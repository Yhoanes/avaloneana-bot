# web.py — Web + Bot en Render: abre la URL -> despierta -> arranca bot

import os
import re
import asyncio
import threading
from typing import Optional

import discord
from discord import app_commands
from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse

# ---------------- Vars de entorno ----------------
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("1420463425309507738")

# ---------------- Intents mínimos ----------------
intents = discord.Intents.none()
intents.guilds = True

# ===================== Lógica idéntica a tu web =====================
RENAME = {
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Construct_01': 'Constructor',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_High-Priest_01': 'Suicida',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Basilisk-Rider_01': 'Basilisco',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Arch-Mage_01': 'Dancing',
    'AVA_TEMPLE_HIGHLIGHT_LEGENDARY_BOSS_Grail_Sanctum_01': 'FinalBoss',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Knight-Captain_01': 'Capitán Caballero'
}
TECH_BASE = list(RENAME.keys())
TECH_ALL = list({*TECH_BASE, *[s.replace('AVA_TEMPLE_', 'AVA_TEMPLATE_') for s in TECH_BASE]})

def to_temple(s: str) -> str:
    return s.replace('AVA_TEMPLATE_', 'AVA_TEMPLE_')

CHEST_BY_BOSS = {
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Knight-Captain_01': {'10':'verde','11':'azul','09':'morado','08':'dorado'},
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_High-Priest_01'  : {'10':'verde','11':'azul','09':'morado','08':'dorado'},
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Basilisk-Rider_01': {'10':'verde','11':'azul','09':'morado','08':'dorado'},
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Arch-Mage_01'     : {'10':'verde','11':'azul','09':'morado','08':'dorado'},
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Construct_01'     : {'08':'verde','09':'azul','07':'morado','06':'dorado'},
    'AVA_TEMPLE_HIGHLIGHT_LEGENDARY_BOSS_Grail_Sanctum_01'    : {'05':'azul','04':'morado','02':'dorado'}
}
BASE_LAYER_COLOR = {}

def hex_to_ascii(hex_str: str) -> str:
    if not hex_str: return ''
    clean = (hex_str.replace('0x','').replace('0X','')
             .replace('\t',' ').replace('\r',' ').replace('\n',' '))
    clean = re.sub(r'[^0-9A-Fa-f]', ' ', clean).strip()
    if not clean: return ''
    parts = re.split(r'\s+', clean)
    out = []
    for p in parts:
        if len(p) != 2: continue
        try:
            out.append(chr(int(p,16)))
        except ValueError:
            continue
    return ''.join(out)

def first_layer_between(ascii_txt: str, from_idx: int, to_idx: Optional[int]) -> Optional[str]:
    re_layer = re.compile(r'Layer_(\d{2})')
    for m in re_layer.finditer(ascii_txt, pos=from_idx):
        if to_idx is not None and m.start() >= to_idx:
            return None
        return m.group(1)
    return None

def reward_for(boss_temple: str, layer_num: Optional[str]) -> str:
    if not layer_num: return 'desconocido'
    mp = CHEST_BY_BOSS.get(boss_temple)
    if mp and layer_num in mp: return mp[layer_num]
    return BASE_LAYER_COLOR.get(layer_num, 'desconocido')

def detect_bosses_with_chests(ascii_txt: str) -> list[dict]:
    hits=[]
    for tech in TECH_ALL:
        idx=-1
        while True:
            idx = ascii_txt.find(tech, idx+1)
            if idx == -1: break
            hits.append({'tech': tech, 'idx': idx})
    hits.sort(key=lambda x: x['idx'])

    out=[]
    for i, cur in enumerate(hits):
        next_idx = hits[i+1]['idx'] if i < len(hits)-1 else None
        tech_temple = to_temple(cur['tech'])
        if tech_temple not in RENAME: continue
        layer = first_layer_between(ascii_txt, cur['idx'], next_idx)
        cofre = reward_for(tech_temple, layer) if layer else 'desconocido'
        out.append({'name': RENAME[tech_temple], 'layer': layer, 'cofre': cofre, 'bossTech': tech_temple})
    return out

# ===================== Estética =====================
PRIMARY_COLOR = 0x6C5CE7
ARROW = "→"
CHEST_EMOJI = {"morado":"🟣","verde":"🟢","azul":"🔵","dorado":"🟡","desconocido":"🎁"}
TITLE_TEXT = "🪬 Escáner de Avaloneana 🪬"
FOOTER_TEXT = "🔯 ScannerAva – Shadrick 🔯"

# ===================== Cliente Discord =====================
class AvaloneanaClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Slash commands sincronizados en guild", GUILD_ID)
        else:
            await self.tree.sync()
            print("Slash commands sincronizados globalmente")

client = AvaloneanaClient()

@client.event
async def on_ready():
    print(f"✅ Bot listo como {client.user} (ID: {client.user.id})")

@client.tree.command(name="scan", description="Sube un .txt con el bloque HEX para escanear y devolver el resultado.")
@app_commands.describe(archivo="Adjunta un archivo .txt con el bloque HEX")
async def scan(interaction: discord.Interaction, archivo: discord.Attachment):
    await interaction.response.defer()
    if not archivo.filename.lower().endswith(".txt"):
        await interaction.followup.send("Adjunta un archivo **.txt**.")
        return
    if archivo.size > 2_000_000:
        await interaction.followup.send("Archivo demasiado grande (máx ~2 MB).")
        return
    data = await archivo.read()
    try: raw = data.decode("utf-8", errors="replace").strip()
    except: raw = data.decode("latin1", errors="replace").strip()

    ascii_txt = hex_to_ascii(raw)
    if not ascii_txt:
        await interaction.followup.send("No pude convertir el HEX. Revisa el formato.")
        return

    items = detect_bosses_with_chests(ascii_txt)
    if not items:
        await interaction.followup.send("No se detectaron bosses conocidos.")
        return

    # Embed bonito
    pretty = []
    for it in items:
        c = (it['cofre'] or 'desconocido').lower()
        emoji = CHEST_EMOJI.get(c, '🎁')
        pretty.append(f"**{it['name']}** {ARROW} Cofre {c.capitalize()}{emoji}")
    desc = "\n".join(pretty) if pretty else "No hay resultados."

    embed = discord.Embed(title=TITLE_TEXT, description=desc, color=PRIMARY_COLOR)
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.followup.send(embed=embed)

# ===================== FastAPI (para Render) =====================
app = FastAPI()
_bot_started = False

def _start_bot():
    asyncio.run(client.start(TOKEN))

@app.on_event("startup")
async def startup_event():
    global _bot_started
    if not TOKEN:
        raise RuntimeError("Falta TOKEN en variables de entorno")
    if not _bot_started:
        threading.Thread(target=_start_bot, daemon=True).start()
        _bot_started = True
        print("Bot lanzado en background")

@app.get("/", response_class=PlainTextResponse)
def root():
    return "✅ Bot encendido. Ya puedes usar /scan en Discord."

@app.get("/healthz")
def health():
    return Response("ok", media_type="text/plain")
