import io
import os
import sqlite3
import datetime
import traceback
import discord
from discord import app_commands
from discord.ext import commands

# =====================================================================================
# 1) DESIGN: Farben, Texte und Namen kannst du hier später selbst ändern
#    Farben sind Hex-Codes: 0x + 6 Zeichen (z. B. 0xFF0000 = Rot)
# =====================================================================================
DESIGN = {
    "FOOTER": "Made by Timo",
    "FOOTER_TEAM": "Notruf Hamburg Teamverwaltung",
    "FOOTER_TICKET": "Notruf Hamburg Ticketsystem",
    "PRIMARY": 0x8E44AD,   # Lila: Standard
    "SUCCESS": 0x38A169,   # Grün
    "ERROR": 0xE53E3E,     # Rot
    "WARN": 0xDD6B20,      # Orange
    "NEUTRAL": 0x718096,   # Grau: Logs
    "STATUS": "📍Offizieller Bot von SLRP 
               🔒 Alle Rechte Vorbehalten sowie Copyright Geschützt
               📱 Entwickelt von Timo [Developer]",
    "WELCOME_TEXT": "Willkommen auf dem Server, {user}! Schön, dass du da bist. Du bist Mitglied Nr. {count}.",
    "LEAVE_TEXT": "{name} hat den Server verlassen.",
    "VERIFY_TEXT": "Klicke auf den Button, um dich zu verifizieren und den Server freizuschalten.",
    "SEP": "────────────────────────",   # Trennlinie in den Team-Embeds
    "MAX_WARNS": 3,                      # Anzeige "Warnungen: 1/3"
}

# Ticket-Kategorien: (Schlüssel, Name, Emoji, Beschreibung, Rolle die das Ticket sieht)
# Die Rolle ist ein Name aus CFG unten. Ist die ID dort 0, sieht die TEAM_ROLE das Ticket.
TICKET_KATEGORIEN = [
    ("support", "Normaler Support", "🎫", "Allgemeine Support-Anfragen", "TEAM_ROLE"),
    ("haeuser", "Häuser & Waffenschein", "🏠", "Häuser-Kauf, Waffenschein etc.", "TEAM_ROLE"),
    ("entbannung", "Entbannung", "🔓", "Antrag auf Entbannung", "TEAM_ROLE"),
    ("beschwerde", "Team Beschwerde", "📢", "Beschwerden über Teammitglieder", "HIGHTEAM_ROLE"),
    ("creator", "Content Creator", "🎨", "Bewerbung als Content Creator", "TEAM_ROLE"),
    ("highteam", "High Team", "👑", "Nur für High Team", "HIGHTEAM_ROLE"),
    ("partner", "Partnerschaften", "🤝", "Partneranfragen", "HIGHTEAM_ROLE"),
    ("fraktion", "Fraktion", "🏛️", "Fraktion eintragen", "TEAM_ROLE"),
    ("owner", "Owner", "👔", "Ticket an das Owner-Team", "OWNER_ROLE"),
]

# Zeigt in der Teamliste Online-Status (🟢🟠🔴⚫). Dafür musst du im Developer Portal
# unter Bot zusätzlich den "Presence Intent" einschalten. Sonst auf False lassen.
SHOW_STATUS = False

# =====================================================================================
# 2) EINSTELLUNGEN: IDs (0 = noch nicht eingerichtet)
# =====================================================================================
TOKEN = os.getenv("DISCORD_TOKEN")  # kommt von Railway (Variables), nie in den Code schreiben

CFG = {
    "LOG_CHANNEL": 1558571057999511643,
    "WELCOME_CHANNEL": 1557814941527056396,
    "LEAVE_CHANNEL": 1557814950137692277,
    "ALERT_CHANNEL": 1558572041550958683,
    "RP_CHANNEL": 1557814995683909662,
    "TICKET_CATEGORY": 1557814916101050469,
    "VERIFY_ROLE": 1557814738988310678,
    "TEAM_ROLE": 1557814706457018438,
    "SUPPORT_ROLE": 1557814706457018438,
    "SUPPORT_VC": 1557814994614227134, "SUPPORT_PING": 1557815189456556082,
    "HIGHTEAM_VC": 1557815075492864032, "HIGHTEAM_PING": 1557815191901569078,
    "BUERO_VC": 1557815118899716226, "BUERO_PING": 1558570781892550779,
    # Neu: bitte nach und nach eintragen
    "TEAMLOG_CHANNEL": 1557815289033531523,    # Channel für Beitritt/Uprank/Kick/Warn (0 = dort, wo der Befehl genutzt wird)
    "FEEDBACK_CHANNEL": 1557815164940845106,   # Channel für Feedbacks (0 = Log-Channel)
    "RP_PING_ROLE": 1557814802670297240,       # Rolle, die bei /rp_start gepingt wird
    "HIGHTEAM_ROLE": 1557814659778879587,      # Rolle für High-Team-Tickets
    "OWNER_ROLE": 1557814639113281607,         # Rolle für Owner-Tickets
    "NEWS_PING_ROLE": 1557814816704565279, "EVENT_PING_ROLE": 1557814799637680223, "GIVEAWAY_PING_ROLE": 1557814818726084689,
    "PARTNER_PING_ROLE": 1557814801168601172, "FRAKTION_PING_ROLE": 1558577674534920192,
}

# Self-Roles-Buttons: (Name, Emoji, Rollen-Schlüssel aus CFG)
PING_ROLLEN = [
    ("News Ping", "📣", "NEWS_PING_ROLE"),
    ("RP Ping", "🟩", "RP_PING_ROLE"),
    ("Fraktion Ping", "🏛️", "FRAKTION_PING_ROLE"),
    ("Partnerschafts Ping", "🤝", "PARTNER_PING_ROLE"),
    ("Giveaway Ping", "🎀", "GIVEAWAY_PING_ROLE"),
    ("Event Ping", "🪩", "EVENT_PING_ROLE"),
]
# =====================================================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.presences = SHOW_STATUS
bot = commands.Bot(command_prefix="!", intents=intents)

SEP = DESIGN["SEP"]


# ------------------------------ Datenbank ------------------------------
def db(q, args=(), fetch=False):
    with sqlite3.connect(os.getenv("DB_PATH", "bot.db")) as c:
        cur = c.execute(q, args)
        return cur.fetchall() if fetch else None


for t in [
    "CREATE TABLE IF NOT EXISTS roblox(uid INTEGER PRIMARY KEY, name TEXT)",
    "CREATE TABLE IF NOT EXISTS teamrang(uid INTEGER PRIMARY KEY, rolle INTEGER)",
    "CREATE TABLE IF NOT EXISTS warns(uid INTEGER, grund TEXT, von INTEGER)",
    "CREATE TABLE IF NOT EXISTS mwarns(uid INTEGER, grund TEXT, von INTEGER, zeit TEXT)",
    "CREATE TABLE IF NOT EXISTS icsperre(uid INTEGER PRIMARY KEY, grund TEXT)",
    "CREATE TABLE IF NOT EXISTS houses(name TEXT PRIMARY KEY, besitzer INTEGER)",
    "CREATE TABLE IF NOT EXISTS abmeldungen(uid INTEGER PRIMARY KEY, bis TEXT, grund TEXT)",
]:
    db(t)


# ------------------------------ Hilfsfunktionen ------------------------------
def emb(title, desc="", color=None, thumb=None, footer=None):
    e = discord.Embed(
        title=title,
        description=desc,
        color=color if color is not None else DESIGN["PRIMARY"],
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text=footer or DESIGN["FOOTER"])
    if thumb:
        e.set_thumbnail(url=thumb)
    return e


def team_embed(title, color, rows):
    """Team-Embed im Stil: Trennlinie, Feld, Trennlinie ... und am Ende 'Wann'.
    rows = Liste aus (Emoji, Name, Wert)"""
    desc = ""
    for emoji, label, value in rows:
        desc += f"{SEP}\n\n{emoji} **{label}:** {value}\n\n"
    desc += f"{SEP}\n\n🕐 **Wann:** {discord.utils.format_dt(discord.utils.utcnow(), 'f')}\n\n{SEP}"
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text=DESIGN["FOOTER_TEAM"])
    return e


def list_embed(title, lines, empty, color=None):
    text = ""
    for n, line in enumerate(lines):
        if len(text) + len(line) + 1 > 3900:
            text += f"\n… und {len(lines) - n} weitere"
            break
        text += line + "\n"
    return emb(title, text or empty, color)


def is_team(member: discord.Member):
    return member.guild_permissions.administrator or any(
        r.id == CFG["TEAM_ROLE"] for r in member.roles
    )


async def log(guild, text, file=None):
    ch = guild.get_channel(CFG["LOG_CHANNEL"])
    if ch:
        await ch.send(embed=emb("Bot-Log", text, DESIGN["NEUTRAL"]), file=file)


def team_only():
    return app_commands.check(lambda i: is_team(i.user))


async def post_team(i: discord.Interaction, embed: discord.Embed, logtext: str):
    ch = i.guild.get_channel(CFG["TEAMLOG_CHANNEL"])
    if ch and ch.id != i.channel.id:
        await ch.send(embed=embed)
        await i.response.send_message(f"Eingetragen in {ch.mention}.", ephemeral=True)
    else:
        await i.response.send_message(embed=embed)
    await log(i.guild, logtext)


def get_rank(uid):
    r = db("SELECT rolle FROM teamrang WHERE uid=?", (uid,), fetch=True)
    return r[0][0] if r else None


async def apply_rank(guild, member, old_id, new_role):
    """Entfernt die alte Rang-Rolle, vergibt die neue und die Team-Rolle."""
    try:
        old = guild.get_role(old_id) if old_id else None
        if old and old != new_role:
            await member.remove_roles(old)
        if new_role:
            await member.add_roles(new_role)
        team = guild.get_role(CFG["TEAM_ROLE"])
        if team:
            await member.add_roles(team)
        return True
    except discord.Forbidden:
        return False


@bot.tree.error
async def on_tree_error(i: discord.Interaction, err):
    if isinstance(err, app_commands.CheckFailure):
        msg = "Dafür hast du keine Berechtigung."
    else:
        traceback.print_exception(type(err), err, err.__traceback__)
        msg = "Da ist ein Fehler passiert. Bitte versuche es nochmal."
    if i.response.is_done():
        await i.followup.send(msg, ephemeral=True)
    else:
        await i.response.send_message(msg, ephemeral=True)


# ------------------------------ Verify ------------------------------
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", emoji="✅", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify(self, i: discord.Interaction, b: discord.ui.Button):
        role = i.guild.get_role(CFG["VERIFY_ROLE"])
        if role in i.user.roles:
            return await i.response.send_message("Du bist schon verifiziert.", ephemeral=True)
        if role:
            await i.user.add_roles(role)
        await i.response.send_message("Du bist verifiziert!", ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat sich verifiziert.")


# ------------------------------ Tickets ------------------------------
def ticket_role(guild, cfg_key):
    return guild.get_role(CFG.get(cfg_key, 0)) or guild.get_role(CFG["TEAM_ROLE"])


async def create_ticket(i: discord.Interaction, key: str):
    g = i.guild
    kat = next(k for k in TICKET_KATEGORIEN if k[0] == key)
    _, label, emoji, _, rolle_key = kat
    for ch in g.text_channels:
        if ch.topic == f"ticket:{i.user.id}":
            return await i.response.edit_message(content=f"Du hast schon ein Ticket: {ch.mention}", embed=None, view=None)
    role = ticket_role(g, rolle_key)
    ow = {
        g.default_role: discord.PermissionOverwrite(view_channel=False),
        i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
    }
    if role:
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    ch = await g.create_text_channel(
        f"{key}-{i.user.name}",
        category=g.get_channel(CFG["TICKET_CATEGORY"]),
        overwrites=ow,
        topic=f"ticket:{i.user.id}",
    )
    e = emb(f"{emoji} {label}", "Beschreibe bitte dein Anliegen so detailliert wie möglich.\nDas Team meldet sich so schnell wie möglich bei dir.",
            footer=DESIGN["FOOTER_TICKET"])
    await ch.send(f"{i.user.mention} {role.mention if role else ''}", embed=e, view=TicketControls())
    await i.response.edit_message(content=f"Ticket erstellt: {ch.mention}", embed=None, view=None)
    await log(g, f"Ticket ({label}) von {i.user.mention} erstellt: {ch.mention}")


class CategorySelect(discord.ui.Select):
    def __init__(self):
        opts = [discord.SelectOption(label=l, value=k, emoji=e, description=d) for k, l, e, d, _ in TICKET_KATEGORIEN]
        super().__init__(placeholder="Wähle eine Kategorie aus...", options=opts)

    async def callback(self, i: discord.Interaction):
        await create_ticket(i, self.values[0])


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(CategorySelect())

    @discord.ui.button(label="Abbrechen", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.edit_message(content="Abgebrochen.", embed=None, view=None)


class TicketOpen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket erstellen", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ticket_open")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        e = emb("🎫 Ticket Kategorie auswählen", "Wähle eine Kategorie für dein Ticket aus:", footer=DESIGN["FOOTER_TICKET"])
        await i.response.send_message(embed=e, view=CategoryView(), ephemeral=True)


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Übernehmen", emoji="🙋", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_team(i.user):
            return await i.response.send_message("Nur das Team kann Tickets übernehmen.", ephemeral=True)
        await i.response.send_message(embed=emb("🙋 Ticket übernommen", f"{i.user.mention} kümmert sich um dieses Ticket.", DESIGN["SUCCESS"], footer=DESIGN["FOOTER_TICKET"]))
        await log(i.guild, f"{i.user.mention} hat {i.channel.mention} übernommen.")

    @discord.ui.button(label="Schließen", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        try:
            owner_id = int((i.channel.topic or "").split(":")[1])
        except Exception:
            owner_id = 0
        if not (is_team(i.user) or i.user.id == owner_id):
            return await i.response.send_message("Das darf nur das Team oder der Ersteller.", ephemeral=True)
        await i.response.send_message("Ticket wird geschlossen und gespeichert …")
        lines = []
        async for m in i.channel.history(limit=None, oldest_first=True):
            if m.content:
                lines.append(f"[{m.created_at:%d.%m.%Y %H:%M}] {m.author}: {m.content}")
        data = io.BytesIO("\n".join(lines).encode("utf-8"))
        name = i.channel.name
        await log(i.guild, f"{name} wurde von {i.user.mention} geschlossen. Verlauf siehe Datei.",
                  file=discord.File(data, filename=f"{name}.txt"))
        await i.channel.delete()


def ticket_panel_embed():
    kats = "\n".join(f"• {e} {l}" for _, l, e, _, _ in TICKET_KATEGORIEN)
    desc = (
        f"{SEP}\n📋 **TICKET ERSTELLEN**\n{SEP}\n\n"
        f"Klicke auf den Button unten, um ein Ticket zu erstellen.\n\n"
        f"📌 **Kategorien:**\n{kats}\n\n{SEP}\n"
        f"💡 **Hinweis:**\n• Für jedes Ticket wird ein eigener Channel erstellt\n"
        f"• Bitte beschreibe dein Anliegen so detailliert wie möglich\n{SEP}"
    )
    e = discord.Embed(title="🎫 TICKETSYSTEM", description=desc, color=DESIGN["PRIMARY"])
    e.set_footer(text=DESIGN["FOOTER_TICKET"])
    return e


# ------------------------------ "." Discord-Kontrolle ------------------------------
class DotRequest(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    def _ok(self, i):
        return i.user.guild_permissions.administrator or any(r.id == CFG["SUPPORT_ROLE"] for r in i.user.roles)

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.success)
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        if not self._ok(i):
            return await i.response.send_message("Nur Supporter.", ephemeral=True)
        role = i.guild.get_role(CFG["VERIFY_ROLE"])
        if role:
            await self.member.add_roles(role)
        await i.response.edit_message(
            embed=emb("✅ Angenommen", f"{self.member.mention} wurde von {i.user.mention} angenommen.", DESIGN["SUCCESS"]), view=None)
        await log(i.guild, f"{i.user.mention} hat {self.member.mention} angenommen.")

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.danger)
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        if not self._ok(i):
            return await i.response.send_message("Nur Supporter.", ephemeral=True)
        await i.response.edit_message(
            embed=emb("❌ Abgelehnt", f"{self.member.mention} wurde von {i.user.mention} abgelehnt.", DESIGN["ERROR"]), view=None)
        await log(i.guild, f"{i.user.mention} hat {self.member.mention} abgelehnt.")


# ------------------------------ Ping-Rollen (Self-Roles) ------------------------------
class PingRoles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for n, (label, emoji, key) in enumerate(PING_ROLLEN):
            b = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=f"pingrole_{n}")
            b.callback = self._make(key)
            self.add_item(b)

    def _make(self, key):
        async def cb(i: discord.Interaction):
            role = i.guild.get_role(CFG.get(key, 0))
            if not role:
                return await i.response.send_message("Diese Rolle ist noch nicht eingerichtet.", ephemeral=True)
            if role in i.user.roles:
                await i.user.remove_roles(role)
                msg = f"Rolle {role.mention} entfernt."
            else:
                await i.user.add_roles(role)
                msg = f"Rolle {role.mention} erhalten."
            await i.response.send_message(msg, ephemeral=True)
        return cb


# ------------------------------ Feedback ------------------------------
class FeedbackModal(discord.ui.Modal, title="Teammitglied Feedback"):
    sterne = discord.ui.TextInput(label="Sterne (1-5)", placeholder="1-5", max_length=1)
    grund = discord.ui.TextInput(label="Warum?", placeholder="Deine Begründung...", style=discord.TextStyle.paragraph, max_length=800)

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, i: discord.Interaction):
        if not self.sterne.value.isdigit() or not 1 <= int(self.sterne.value) <= 5:
            return await i.response.send_message("Bitte gib bei den Sternen eine Zahl von 1 bis 5 ein.", ephemeral=True)
        n = int(self.sterne.value)
        desc = (
            f"**Teamler:** {self.member.mention}\n"
            f"**Bewertung:** {'⭐' * n} `({n}/5)`\n"
            f"**Begründung:** {self.grund.value}\n\n"
            f"**Von:** {i.user.mention} • {discord.utils.format_dt(discord.utils.utcnow(), 'R')}"
        )
        ch = i.guild.get_channel(CFG["FEEDBACK_CHANNEL"]) or i.guild.get_channel(CFG["LOG_CHANNEL"])
        if ch:
            await ch.send(embed=emb("💜 Neues Feedback", desc, DESIGN["PRIMARY"]))
        await i.response.send_message("Danke für dein Feedback!", ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat Feedback für {self.member.mention} abgegeben ({n}/5).")


class FeedbackPick(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Wähle ein Teammitglied aus...", min_values=1, max_values=1)
    async def pick(self, i: discord.Interaction, select: discord.ui.UserSelect):
        member = i.guild.get_member(select.values[0].id)
        if member is None or not is_team(member):
            return await i.response.send_message("Das ist kein Teammitglied.", ephemeral=True)
        if member.id == i.user.id:
            return await i.response.send_message("Du kannst dich nicht selbst bewerten.", ephemeral=True)
        await i.response.send_modal(FeedbackModal(member))


class FeedbackOpen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Feedback einreichen", emoji="💜", style=discord.ButtonStyle.secondary, custom_id="feedback_open")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        e = emb("💜 Teammitglied Feedback", "Wähle das Teammitglied aus, das du bewerten möchtest.")
        await i.response.send_message(embed=e, view=FeedbackPick(), ephemeral=True)


# ------------------------------ Events ------------------------------
last_dot, last_vc = {}, {}


def cooldown(store, key, seconds):
    now = datetime.datetime.now().timestamp()
    if now - store.get(key, 0) < seconds:
        return True
    store[key] = now
    return False


@bot.event
async def setup_hook():
    bot.add_view(VerifyView())
    bot.add_view(TicketOpen())
    bot.add_view(TicketControls())
    bot.add_view(PingRoles())
    bot.add_view(FeedbackOpen())
    await bot.tree.sync()


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(DESIGN["STATUS"]))
    print(f"Eingeloggt als {bot.user}")


@bot.event
async def on_member_join(m: discord.Member):
    ch = m.guild.get_channel(CFG["WELCOME_CHANNEL"])
    if ch:
        text = DESIGN["WELCOME_TEXT"].format(user=m.mention, count=m.guild.member_count)
        await ch.send(embed=emb("👋 Willkommen!", text, DESIGN["SUCCESS"], m.display_avatar.url))
    await log(m.guild, f"{m.mention} ist beigetreten.")


@bot.event
async def on_member_remove(m: discord.Member):
    ch = m.guild.get_channel(CFG["LEAVE_CHANNEL"])
    if ch:
        await ch.send(embed=emb("🚪 Auf Wiedersehen", DESIGN["LEAVE_TEXT"].format(name=m.display_name), DESIGN["ERROR"], m.display_avatar.url))
    await log(m.guild, f"{m.display_name} hat den Server verlassen.")


@bot.event
async def on_member_ban(guild, user):
    await log(guild, f"{user} wurde gebannt.")


@bot.event
async def on_message_delete(msg: discord.Message):
    if msg.author.bot or not msg.guild or not msg.content:
        return
    await log(msg.guild, f"Nachricht von {msg.author.mention} in {msg.channel.mention} gelöscht:\n{msg.content[:1500]}")


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    await log(before.guild, f"{before.author.mention} hat in {before.channel.mention} eine Nachricht bearbeitet.\n"
                            f"**Vorher:** {before.content[:700]}\n**Nachher:** {after.content[:700]}")


@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot or not msg.guild:
        return
    if msg.content.strip() == "." and not cooldown(last_dot, msg.author.id, 60):
        await msg.channel.send(
            embed=emb("🛡️ Discord-Kontrolle", f"{msg.author.mention} wartet auf Kontrolle. Ein Supporter kann annehmen oder ablehnen."),
            view=DotRequest(msg.author),
        )
    await bot.process_commands(msg)


@bot.event
async def on_voice_state_update(m: discord.Member, before, after):
    if m.bot:
        return
    rooms = {
        CFG["SUPPORT_VC"]: ("Support", CFG["SUPPORT_PING"]),
        CFG["HIGHTEAM_VC"]: ("Highteam", CFG["HIGHTEAM_PING"]),
        CFG["BUERO_VC"]: ("Büro", CFG["BUERO_PING"]),
    }
    if after.channel and after.channel != before.channel and after.channel.id in rooms:
        name, role_id = rooms[after.channel.id]
        if not cooldown(last_vc, m.id, 30):
            alert = m.guild.get_channel(CFG["ALERT_CHANNEL"])
            if alert:
                await alert.send(
                    f"<@&{role_id}>",
                    embed=emb(f"🔔 {name}-Warteraum", f"{m.mention} wartet im **{name}-Warteraum**.", DESIGN["WARN"]),
                )
            await log(m.guild, f"{m.mention} ist dem {name}-Warteraum beigetreten.")
        try:
            if m.guild.voice_client is None:
                await after.channel.connect()
        except Exception as e:
            print("Voice-Join fehlgeschlagen:", e)
    vc = m.guild.voice_client
    if vc and len(vc.channel.members) == 1:
        await vc.disconnect()


# ------------------------------ Panels ------------------------------
@bot.tree.command(description="Verify-Panel senden")
@team_only()
async def verify_panel(i: discord.Interaction):
    await i.channel.send(embed=emb("✅ Verifizierung", DESIGN["VERIFY_TEXT"], DESIGN["SUCCESS"]), view=VerifyView())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Ticket-Panel senden")
@team_only()
async def ticket_panel(i: discord.Interaction):
    await i.channel.send(embed=ticket_panel_embed(), view=TicketOpen())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Ping-Rollen-Panel senden")
@team_only()
async def pingrollen_panel(i: discord.Interaction):
    desc = "Wähle aus, für welche Themen du benachrichtigt werden möchtest.\nKlicke auf einen Button, um die Rolle zu erhalten oder wieder zu entfernen."
    await i.channel.send(embed=emb("🔔 Ping Rollen", desc), view=PingRoles())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Feedback-Panel senden")
@team_only()
async def feedback_panel(i: discord.Interaction):
    desc = "Hast du Lob, Kritik oder Verbesserungsvorschläge für unser Team?\nKlicke unten auf den Button, um dein Feedback einzureichen."
    await i.channel.send(embed=emb("💜 Feedback geben", desc), view=FeedbackOpen())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Eigenes Embed senden (Farbe optional als Hex, z. B. FF0000)")
@team_only()
async def embed(i: discord.Interaction, titel: str, text: str, farbe: str = ""):
    try:
        color = int(farbe.replace("#", ""), 16) if farbe else None
    except ValueError:
        return await i.response.send_message("Ungültige Farbe. Beispiel: FF0000", ephemeral=True)
    await i.channel.send(embed=emb(titel, text.replace("\\n", "\n"), color))
    await i.response.send_message("Gesendet.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat ein Embed gesendet: {titel}")


# ------------------------------ RP Start / Stop ------------------------------
@bot.tree.command(description="RP starten")
@team_only()
async def rp_start(i: discord.Interaction, servercode: str, ping: bool = True):
    ch = i.guild.get_channel(CFG["RP_CHANNEL"]) or i.channel
    role = i.guild.get_role(CFG["RP_PING_ROLE"])
    desc = (
        f"{role.mention + ' ' if role else ''}Es findet eine **öffentliche** Roleplay Sitzung statt.\n\n"
        f"**Servercode:** `{servercode}`\n"
        f"Wir freuen uns, dich begrüßen zu dürfen! 👋"
    )
    await ch.send(content=role.mention if (role and ping) else None, embed=emb("🟢 Das RP hat begonnen!", desc, DESIGN["SUCCESS"]))
    await i.response.send_message("RP gestartet.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat das RP gestartet (Code {servercode}).")


@bot.tree.command(description="RP beenden")
@team_only()
async def rp_stop(i: discord.Interaction, servercode: str = ""):
    ch = i.guild.get_channel(CFG["RP_CHANNEL"]) or i.channel
    code = f"**Servercode:** `{servercode}`\n" if servercode else ""
    desc = (
        f"Es findet **keine** Roleplay Sitzung statt.\n\n{code}"
        f"Komm gerne bei der nächsten Roleplay Sitzung vorbei! 🎉"
    )
    await ch.send(embed=emb("🔴 Das RP ist beendet!", desc, DESIGN["ERROR"]))
    await i.response.send_message("RP beendet.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat das RP beendet.")


# ------------------------------ Roblox-Namen ------------------------------
@bot.tree.command(description="Deinen Roblox-Namen eintragen")
async def roblox_setzen(i: discord.Interaction, name: str):
    db("INSERT OR REPLACE INTO roblox VALUES(?,?)", (i.user.id, name))
    await i.response.send_message(f"Roblox-Name gespeichert: **{name}**", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat den Roblox-Namen {name} eingetragen.")


@bot.tree.command(description="Roblox-Namen eines Mitglieds entfernen")
@team_only()
async def roblox_entfernen(i: discord.Interaction, user: discord.Member):
    db("DELETE FROM roblox WHERE uid=?", (user.id,))
    await i.response.send_message(f"Eintrag von {user.mention} entfernt.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat den Roblox-Eintrag von {user.mention} entfernt.")


@bot.tree.command(description="Liste Discord-Name und Roblox-Name")
async def roblox_liste(i: discord.Interaction):
    rows = db("SELECT uid,name FROM roblox ORDER BY name COLLATE NOCASE", fetch=True)
    await i.response.send_message(embed=list_embed("🎮 Roblox-Namen", [f"<@{u}> — **{n}**" for u, n in rows], "Noch keine Einträge."))


# ------------------------------ Team ------------------------------
@bot.tree.command(description="Neues Teammitglied eintragen")
@team_only()
async def team_beitritt(i: discord.Interaction, user: discord.Member, position: discord.Role, grund: str):
    old = get_rank(user.id)
    db("INSERT OR REPLACE INTO teamrang VALUES(?,?)", (user.id, position.id))
    ok = await apply_rank(i.guild, user, old, position)
    e = team_embed("👋 Team Beitritt", DESIGN["SUCCESS"], [
        ("👤", "MITGLIED", user.mention), ("🎖️", "POSITION", position.mention), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} ins Team aufgenommen ({position.name}).")
    if not ok:
        await i.followup.send("Rollen konnten nicht vergeben werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


async def rank_change(i, user, rolle, grund, up):
    old = get_rank(user.id)
    if old is None:
        return await i.response.send_message("Diese Person ist nicht im Team. Nutze zuerst /team_beitritt.", ephemeral=True)
    db("INSERT OR REPLACE INTO teamrang VALUES(?,?)", (user.id, rolle.id))
    ok = await apply_rank(i.guild, user, old, rolle)
    old_role = i.guild.get_role(old)
    von = old_role.mention if old_role else "Unbekannt"
    title, color = ("⏫ TEAM UPRANK", DESIGN["SUCCESS"]) if up else ("⏬ TEAM DOWNRANK", DESIGN["WARN"])
    e = team_embed(title, color, [
        ("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention),
        ("📝", "RANGÄNDERUNG", f"\n⬇️ Von: {von}\n⬆️ Auf: {rolle.mention}"), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} auf {rolle.name} {'befördert' if up else 'degradiert'}.")
    if not ok:
        await i.followup.send("Rollen konnten nicht vergeben werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


@bot.tree.command(description="Teammitglied befördern")
@team_only()
async def uprank(i: discord.Interaction, user: discord.Member, rolle: discord.Role, grund: str):
    await rank_change(i, user, rolle, grund, True)


@bot.tree.command(description="Teammitglied degradieren")
@team_only()
async def downrank(i: discord.Interaction, user: discord.Member, rolle: discord.Role, grund: str):
    await rank_change(i, user, rolle, grund, False)


@bot.tree.command(description="Teammitglied aus dem Team entfernen")
@team_only()
async def teamkick(i: discord.Interaction, user: discord.Member, grund: str):
    old = get_rank(user.id)
    db("DELETE FROM teamrang WHERE uid=?", (user.id,))
    ok = True
    try:
        for rid in (old, CFG["TEAM_ROLE"]):
            role = i.guild.get_role(rid) if rid else None
            if role:
                await user.remove_roles(role)
    except discord.Forbidden:
        ok = False
    e = team_embed("❌ TEAM KICK", DESIGN["ERROR"], [
        ("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} aus dem Team gekickt: {grund}")
    if not ok:
        await i.followup.send("Rollen konnten nicht entfernt werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


@bot.tree.command(description="Teamwarn vergeben")
@team_only()
async def teamwarn(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT INTO warns VALUES(?,?,?)", (user.id, grund, i.user.id))
    n = len(db("SELECT 1 FROM warns WHERE uid=?", (user.id,), fetch=True))
    rows = [("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention),
            ("📊", "WARNUNGEN", f"{n}/{DESIGN['MAX_WARNS']}"), ("📝", "GRUND", f"> {grund}")]
    if n >= DESIGN["MAX_WARNS"]:
        rows.insert(3, ("🚨", "HINWEIS", "Maximale Warnungen erreicht"))
    await post_team(i, team_embed("⚠️ TEAM WARN", DESIGN["WARN"], rows), f"{i.user.mention} hat {user.mention} verwarnt (Warn {n}): {grund}")


@bot.tree.command(description="Teamwarn entfernen (Nummer aus /teamwarns)")
@team_only()
async def teamwarn_entfernen(i: discord.Interaction, user: discord.Member, nummer: int, grund: str):
    rows = db("SELECT rowid, grund FROM warns WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    if not 1 <= nummer <= len(rows):
        return await i.response.send_message("Diese Warn-Nummer gibt es nicht. Schau mit /teamwarns nach.", ephemeral=True)
    rid, entfernt = rows[nummer - 1]
    db("DELETE FROM warns WHERE rowid=?", (rid,))
    n = len(rows) - 1
    e = team_embed("🔄 TEAM WARN ENTFERNT", DESIGN["SUCCESS"], [
        ("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention), ("📝", "ENTFERNT", entfernt),
        ("📊", "WARNUNGEN", f"{n}/{DESIGN['MAX_WARNS']}"), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat einen Teamwarn von {user.mention} entfernt: {grund}")


@bot.tree.command(description="Teamwarns eines Mitglieds anzeigen")
@team_only()
async def teamwarns(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT grund,von FROM warns WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    await i.response.send_message(embed=list_embed(f"⚠️ Teamwarns von {user.display_name}", [f"{n}. {g} (von <@{v}>)" for n, (g, v) in enumerate(rows, 1)], "Keine Warns.", DESIGN["WARN"]))


@bot.tree.command(description="Team-Abmeldung")
@team_only()
async def abmeldung(i: discord.Interaction, bis: str, grund: str):
    db("INSERT OR REPLACE INTO abmeldungen VALUES(?,?,?)", (i.user.id, bis, grund))
    e = team_embed("📅 TEAM ABMELDUNG", DESIGN["WARN"], [
        ("👤", "MITGLIED", i.user.mention), ("📆", "BIS", bis), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat sich abgemeldet (bis {bis}): {grund}")


@bot.tree.command(description="Dich aus der Abmeldung zurückmelden")
@team_only()
async def rueckmeldung(i: discord.Interaction):
    db("DELETE FROM abmeldungen WHERE uid=?", (i.user.id,))
    e = team_embed("✅ TEAM RÜCKMELDUNG", DESIGN["SUCCESS"], [("👤", "MITGLIED", i.user.mention)])
    await post_team(i, e, f"{i.user.mention} hat sich zurückgemeldet.")


@bot.tree.command(description="Alle aktuellen Abmeldungen")
@team_only()
async def abmeldungen(i: discord.Interaction):
    rows = db("SELECT uid,bis,grund FROM abmeldungen", fetch=True)
    await i.response.send_message(embed=list_embed("📅 Abmeldungen", [f"<@{u}> bis **{b}**: {g}" for u, b, g in rows], "Niemand abgemeldet.", DESIGN["WARN"]))


def status_dot(m):
    if not SHOW_STATUS or m is None:
        return "•"
    return {"online": "🟢", "idle": "🟠", "dnd": "🔴"}.get(str(m.status), "⚫")


@bot.tree.command(description="Teamliste anzeigen")
async def teamliste(i: discord.Interaction):
    rows = db("SELECT uid, rolle FROM teamrang", fetch=True)
    if not rows:
        return await i.response.send_message(embed=emb("👥 Teamliste", "Keine Teammitglieder eingetragen."))
    groups = {}
    for uid, rid in rows:
        groups.setdefault(rid, []).append(uid)
    sortiert = sorted(groups.items(), key=lambda kv: (i.guild.get_role(kv[0]).position if i.guild.get_role(kv[0]) else -1), reverse=True)
    blocks = []
    for rid, uids in sortiert:
        role = i.guild.get_role(rid)
        head = f"{role.mention if role else 'Unbekannter Rang'} **[{len(uids)}]**"
        lines = "\n".join(f"{status_dot(i.guild.get_member(u))} <@{u}>" for u in uids)
        blocks.append(f"{head}\n{lines}\n\n{SEP}\n")
    embeds, cur = [], ""
    for b in blocks:
        if len(cur) + len(b) > 3800:
            embeds.append(cur)
            cur = ""
        cur += b
    embeds.append(cur)
    out = [emb("👥 Teamliste" if n == 0 else None, text) for n, text in enumerate(embeds[:10])]
    await i.response.send_message(embeds=out)


# ------------------------------ IC-Sperre ------------------------------
@bot.tree.command(description="IC-Rechte sperren")
@team_only()
async def ic_sperre(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT OR REPLACE INTO icsperre VALUES(?,?)", (user.id, grund))
    e = team_embed("🚫 IC-RECHTE SPERRE", DESIGN["ERROR"], [
        ("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention), ("📝", "GRUND", f"> {grund}")])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} IC-gesperrt: {grund}")


@bot.tree.command(description="IC-Sperre aufheben")
@team_only()
async def ic_entsperren(i: discord.Interaction, user: discord.Member):
    db("DELETE FROM icsperre WHERE uid=?", (user.id,))
    e = team_embed("✅ IC-SPERRE AUFGEHOBEN", DESIGN["SUCCESS"], [("👤", "MITGLIED", user.mention), ("👮", "DURCH", i.user.mention)])
    await post_team(i, e, f"{i.user.mention} hat die IC-Sperre von {user.mention} aufgehoben.")


@bot.tree.command(description="Liste aller IC-Sperren")
async def ic_liste(i: discord.Interaction):
    rows = db("SELECT uid,grund FROM icsperre", fetch=True)
    await i.response.send_message(embed=list_embed("🚫 IC-Rechte-Sperren", [f"<@{u}> — {g}" for u, g in rows], "Keine IC-Sperren.", DESIGN["ERROR"]))


# ------------------------------ Häuser ------------------------------
@bot.tree.command(description="Haus hinzufügen oder Besitzer ändern")
@team_only()
async def haus_setzen(i: discord.Interaction, name: str, besitzer: discord.Member):
    db("INSERT OR REPLACE INTO houses VALUES(?,?)", (name, besitzer.id))
    await i.response.send_message(embed=emb("🏠 Haus vergeben", f"**{name}** gehört jetzt {besitzer.mention}.", DESIGN["SUCCESS"]))
    await log(i.guild, f"{i.user.mention} hat Haus {name} an {besitzer.mention} vergeben.")


@bot.tree.command(description="Haus entfernen")
@team_only()
async def haus_loeschen(i: discord.Interaction, name: str):
    db("DELETE FROM houses WHERE name=?", (name,))
    await i.response.send_message(embed=emb("🏠 Haus entfernt", f"**{name}** wurde entfernt.", DESIGN["WARN"]))
    await log(i.guild, f"{i.user.mention} hat Haus {name} entfernt.")


@bot.tree.command(description="Häuserliste")
async def haeuser(i: discord.Interaction):
    rows = db("SELECT name,besitzer FROM houses ORDER BY name COLLATE NOCASE", fetch=True)
    await i.response.send_message(embed=list_embed("🏠 Häuserliste", [f"**{n}** — <@{b}>" for n, b in rows], "Keine Häuser eingetragen."))


# ------------------------------ Moderation ------------------------------
@bot.tree.command(description="Mitglied kicken")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, user: discord.Member, grund: str):
    try:
        await user.kick(reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    await i.response.send_message(embed=emb("👢 Kick", f"{user.mention} wurde gekickt.\n**Grund:** {grund}", DESIGN["ERROR"]))
    await log(i.guild, f"{i.user.mention} hat {user.mention} gekickt: {grund}")


@bot.tree.command(description="Mitglied bannen")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, user: discord.Member, grund: str):
    try:
        await user.ban(reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    await i.response.send_message(embed=emb("🔨 Ban", f"{user.mention} wurde gebannt.\n**Grund:** {grund}", DESIGN["ERROR"]))
    await log(i.guild, f"{i.user.mention} hat {user.mention} gebannt: {grund}")


@bot.tree.command(description="Mitglied stummschalten (Timeout in Minuten)")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(i: discord.Interaction, user: discord.Member, minuten: app_commands.Range[int, 1, 40320], grund: str):
    try:
        await user.timeout(datetime.timedelta(minutes=minuten), reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    await i.response.send_message(embed=emb("🔇 Timeout", f"{user.mention} für **{minuten} Min.** stummgeschaltet.\n**Grund:** {grund}", DESIGN["WARN"]))
    await log(i.guild, f"{i.user.mention} hat {user.mention} für {minuten} Min. stummgeschaltet: {grund}")


@bot.tree.command(description="Mitglied verwarnen")
@team_only()
async def warn(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT INTO mwarns VALUES(?,?,?,?)", (user.id, grund, i.user.id, datetime.datetime.now().strftime("%d.%m.%Y")))
    n = len(db("SELECT 1 FROM mwarns WHERE uid=?", (user.id,), fetch=True))
    await i.response.send_message(embed=emb("⚠️ Verwarnung", f"{user.mention} wurde verwarnt (Warn {n}).\n**Grund:** {grund}", DESIGN["WARN"], user.display_avatar.url))
    await log(i.guild, f"{i.user.mention} hat {user.mention} verwarnt (Warn {n}): {grund}")


@bot.tree.command(description="Verwarnungen eines Mitglieds anzeigen")
@team_only()
async def warns(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT grund,von,zeit FROM mwarns WHERE uid=?", (user.id,), fetch=True)
    await i.response.send_message(embed=list_embed(f"⚠️ Verwarnungen von {user.display_name}", [f"{n}. {g} ({z}, von <@{v}>)" for n, (g, v, z) in enumerate(rows, 1)], "Keine Verwarnungen.", DESIGN["WARN"]))


@bot.tree.command(description="Nachrichten im Channel löschen")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, anzahl: app_commands.Range[int, 1, 100]):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=anzahl)
    await i.followup.send(f"{len(deleted)} Nachrichten gelöscht.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {len(deleted)} Nachrichten in {i.channel.mention} gelöscht.")


# ------------------------------ Info ------------------------------
@bot.tree.command(description="Infos über ein Mitglied")
async def userinfo(i: discord.Interaction, user: discord.Member):
    rb = db("SELECT name FROM roblox WHERE uid=?", (user.id,), fetch=True)
    rid = get_rank(user.id)
    role = i.guild.get_role(rid) if rid else None
    ic = db("SELECT grund FROM icsperre WHERE uid=?", (user.id,), fetch=True)
    w = len(db("SELECT 1 FROM mwarns WHERE uid=?", (user.id,), fetch=True))
    e = emb(f"👤 {user.display_name}", thumb=user.display_avatar.url)
    e.add_field(name="Roblox", value=rb[0][0] if rb else "nicht eingetragen")
    e.add_field(name="Team", value=role.mention if role else "kein Teammitglied")
    e.add_field(name="IC-Sperre", value=ic[0][0] if ic else "keine")
    e.add_field(name="Verwarnungen", value=str(w))
    e.add_field(name="Beigetreten", value=discord.utils.format_dt(user.joined_at, "D") if user.joined_at else "?")
    await i.response.send_message(embed=e)


@bot.tree.command(description="Alle Befehle anzeigen")
async def hilfe(i: discord.Interaction):
    e = emb("📖 Hilfe")
    e.add_field(name="Alle", value="`/roblox_setzen` `/roblox_liste` `/teamliste` `/ic_liste` `/haeuser` `/userinfo` `/hilfe`", inline=False)
    e.add_field(name="Team", value="`/team_beitritt` `/uprank` `/downrank` `/teamkick` `/teamwarn` `/teamwarn_entfernen` `/teamwarns` `/abmeldung` `/rueckmeldung` `/abmeldungen` `/ic_sperre` `/ic_entsperren` `/haus_setzen` `/haus_loeschen` `/warn` `/warns`", inline=False)
    e.add_field(name="RP und Embeds", value="`/rp_start` `/rp_stop` `/embed`", inline=False)
    e.add_field(name="Moderation", value="`/kick` `/ban` `/timeout` `/clear`", inline=False)
    e.add_field(name="Panels", value="`/verify_panel` `/ticket_panel` `/pingrollen_panel` `/feedback_panel`", inline=False)
    await i.response.send_message(embed=e, ephemeral=True)


bot.run(os.getenv("DISCORD_TOKEN"))
