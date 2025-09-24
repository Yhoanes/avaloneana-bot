# main.py — Slash command /scan (attachment .txt), lógica idéntica a tu web + estilo embellecido

import re
import discord
from discord import app_commands
from typing import Optional
import my_secrets

# ------- Intents mínimos (no hace falta message_content para slash) -------
intents = discord.Intents.none()
intents.guilds = True

# ===================== LÓGICA (idéntica a tu S) ======================

# Mapeo visible
RENAME = {
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Construct_01': 'Constructor',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_High-Priest_01': 'Suicida',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Basilisk-Rider_01': 'Basilisco',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Arch-Mage_01': 'Dancing',
    'AVA_TEMPLE_HIGHLIGHT_LEGENDARY_BOSS_Grail_Sanctum_01': 'FinalBoss',
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Knight-Captain_01': 'Capitán Caballero'
}

# Aceptar variantes TEMPLATE
TECH_BASE = list(RENAME.keys())
TECH_ALL = list({*TECH_BASE, *[s.replace('AVA_TEMPLE_', 'AVA_TEMPLATE_') for s in TECH_BASE]})

# Normaliza TEMPLATE -> TEMPLE
def to_temple(s: str) -> str:
    return s.replace('AVA_TEMPLATE_', 'AVA_TEMPLE_')

# Overrides por boss
CHEST_BY_BOSS = {
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Knight-Captain_01': {
        '10': 'verde','11': 'azul','09': 'morado','08': 'dorado'
    },
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_High-Priest_01': {
        '10': 'verde','11': 'azul','09': 'morado','08': 'dorado'
    },
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Basilisk-Rider_01': {
        '10': 'verde','11': 'azul','09': 'morado','08': 'dorado'
    },
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Arch-Mage_01': {
        '10': 'verde','11': 'azul','09': 'morado','08': 'dorado'
    },
    'AVA_TEMPLE_HIGHLIGHT_UNCOMMON_STRAIGHT_Construct_01': {
        '08': 'verde','09': 'azul','07': 'morado','06': 'dorado'
    },
    'AVA_TEMPLE_HIGHLIGHT_LEGENDARY_BOSS_Grail_Sanctum_01': {
        '05': 'azul','04': 'morado','02': 'dorado'
    }
}

BASE_LAYER_COLOR = {}  # sin fallback global

# Conversión HEX -> ASCII (tolerante con comas, 0x, saltos, etc.)
def hex_to_ascii(hex_str: str) -> str:
    if not hex_str:
        return ''
    clean = (
        hex_str.replace('0x', '').replace('0X', '')
        .replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')
    )
    clean = re.sub(r'[^0-9A-Fa-f]', ' ', clean).strip()
    if not clean:
        return ''
    parts = re.split(r'\s+', clean)
    out_chars = []
    for p in parts:
        if len(p) != 2:
            continue
        try:
            v = int(p, 16)
            out_chars.append(chr(v))
        except ValueError:
            continue
    return ''.join(out_chars)

# Encuentra el PRIMER Layer_(XX) ENTRE el boss actual y el siguiente
def first_layer_between(ascii_txt: str, from_idx: int, to_idx: Optional[int]) -> Optional[str]:
    re_layer = re.compile(r'Layer_(\d{2})')
    for m in re_layer.finditer(ascii_txt, pos=from_idx):
        if to_idx is not None and m.start() >= to_idx:
            return None
        return m.group(1)
    return None

def reward_for(boss_temple: str, layer_num: Optional[str]) -> str:
    if not layer_num:
        return 'desconocido'
    mp = CHEST_BY_BOSS.get(boss_temple)
    if mp and layer_num in mp:
        return mp[layer_num]
    return BASE_LAYER_COLOR.get(layer_num, 'desconocido')

def detect_bosses_with_chests(ascii_txt: str) -> list[dict]:
    # 1) localizar TODAS las apariciones de bosses conocidos (y sus variantes TEMPLATE)
    hits = []
    for tech in TECH_ALL:
        idx = -1
        while True:
            idx = ascii_txt.find(tech, idx + 1)
            if idx == -1:
                break
            hits.append({'tech': tech, 'idx': idx})
    # 2) ordenar por posición
    hits.sort(key=lambda x: x['idx'])

    # 3) para cada boss, tomar el primer Layer dentro del rango hasta el siguiente boss
    out = []
    for i, cur in enumerate(hits):
        next_idx = hits[i + 1]['idx'] if i < len(hits) - 1 else None
        tech_temple = to_temple(cur['tech'])
        if tech_temple not in RENAME:
            continue  # solo de nuestra lista
        layer = first_layer_between(ascii_txt, cur['idx'], next_idx)
        cofre = reward_for(tech_temple, layer) if layer else 'desconocido'
        out.append({
            'name': RENAME[tech_temple],
            'layer': layer,
            'cofre': cofre,
            'bossTech': tech_temple
        })
    return out

# ===================== Estética del mensaje ======================
PRIMARY_COLOR = 0x6C5CE7  # morado elegante
ARROW = "→"
CHEST_EMOJI = {
    "morado": "🟣",
    "verde": "🟢",
    "azul": "🔵",
    "dorado": "🟡",
    "desconocido": "🎁"
}
TITLE_TEXT = "🪬 Escáner de Dungeon Avaloneana 🪬"
FOOTER_TEXT = "🔯 ScannerAva – Shadrick 🔯"

# ======================= Cliente + Slash Command ===========================
class AvaloneanaClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync rápido por guild si está configurado
        guild_id = getattr(my_secrets, "GUILD_ID", None)
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Slash commands sincronizados en guild {guild_id}: {[c.name for c in synced]}")
        else:
            synced = await self.tree.sync()
            print(f"Slash commands sincronizados globalmente: {[c.name for c in synced]}")

client = AvaloneanaClient()

@client.event
async def on_ready():
    print(f"✅ Bot listo como {client.user} (ID: {client.user.id})")

# ----------- /scan: requiere adjuntar .txt, interpreta como tu web -----------
@client.tree.command(name="scan", description="Sube un .txt con el bloque HEX para escanear y devolver el resultado.")
@app_commands.describe(archivo="Adjunta un archivo .txt con el bloque HEX (como copias en la web)")
async def scan(interaction: discord.Interaction, archivo: discord.Attachment):
    await interaction.response.defer()  # por si tarda leyendo

    # Validación de adjunto
    if not archivo.filename.lower().endswith(".txt"):
        await interaction.followup.send("Adjunta un archivo **.txt** con el bloque HEX (como en la web).")
        return
    if archivo.size > 2_000_000:
        await interaction.followup.send("Archivo demasiado grande (máx ~2 MB).")
        return

    # Leer texto del adjunto
    data = await archivo.read()
    try:
        raw = data.decode("utf-8", errors="replace")
    except Exception:
        raw = data.decode("latin1", errors="replace")

    raw = raw.strip()
    if not raw:
        await interaction.followup.send("El archivo está vacío. Verifica el contenido.")
        return

    # La página siempre intenta HEX -> ASCII y si no hay nada, muestra error.
    ascii_txt = hex_to_ascii(raw)
    if not ascii_txt:
        await interaction.followup.send("No pude convertir el HEX. Revisa el formato (igual que en la página).")
        return

    # Detectar y formatear salida
    items = detect_bosses_with_chests(ascii_txt)
    if not items:
        await interaction.followup.send("No se detectaron bosses conocidos.")
        return

    # ----- Embellecer salida con Embed -----
    # Formato: **Nombre** → Cofre Color + emoji
    pretty_lines = []
    for it in items:
        color_name = (it['cofre'] or 'desconocido').lower()
        emoji = CHEST_EMOJI.get(color_name, CHEST_EMOJI['desconocido'])
        pretty_lines.append(f"**{it['name']}** {ARROW} Cofre {color_name.capitalize()}{emoji}")

    description = "\n".join(pretty_lines) if pretty_lines else "No hay resultados."
    embed = discord.Embed(title=TITLE_TEXT, description=description, color=PRIMARY_COLOR)
    embed.set_footer(text=FOOTER_TEXT)

    await interaction.followup.send(embed=embed)

# ------------------- Arrancar bot -------------------
if __name__ == "__main__":
    token = my_secrets.TOKEN
    if not token:
        raise RuntimeError("Falta TOKEN en my_secrets.py")
    client.run(token)
