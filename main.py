import os
import discord
import random
import asyncio
from openai import OpenAI
from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional

load_dotenv()

client_api = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

def ape_transform(text: str) -> str:
    """Transformiert einen Text in abwechselnde Groß-/Kleinschreibung."""
    new_text = ""
    use_upper = False
    for char in text:
        if char.isalpha():
            new_text += char.upper() if use_upper else char.lower()
            use_upper = not use_upper
        else:
            new_text += char
    return new_text

def generate_chat_response(history: list) -> str:
    """
    Erzeugt eine ChatGPT-Antwort basierend auf dem übergebenen Gesprächsverlauf.
    Systemprompt: Der Bot soll locker, umgangssprachlich und wie ein junges GenZ Discord-Mitglied antworten.
    """
    try:
        response = client_api.responses.create(
            model="gpt-4o-mini",
            instructions=(
                "Du bist ein junger, lockerer Discord-Nutzer. Du antwortest umgangssprachlich, ohne übertriebene Satzzeichen, "
                "und beteiligst dich am Chat wie ein echtes Mitglied – authentisch und nicht übermäßig formell."
            ),
            max_output_tokens=300,
            input="\n".join(f"{msg['role']}: {msg['content']}" for msg in history),
        )
        return response.output_text.strip()
    except Exception as e:
        return f"Fehler beim Abrufen der Antwort: {e}"

# Liste von Markus-Rühl inspirierten Sprüchen (fiktiv und humorvoll)
maggus_phrases = [
    "Ey, Alter, reiß dich zusammen und pump mal richtig – jetzt wird's fett!",
    "Bruder, keine halben Sachen – du musst die Hanteln knallen lassen!",
    "Komm schon, zeig deine Muckis! Hier geht’s nicht um Warm-up, sondern um richtiges Pitchen!",
    "Das ist kein Training für Anfänger – hier wird richtig abgeräumt, mein Freund!",
    "Ey, wenn du nicht mehr Power raushauen kannst, dann bist du hier fehl am Platz!"
]

# Aktivieren der benötigten Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Erstelle den Bot (Prefix nur für klassische Befehle)
bot = commands.Bot(command_prefix="/", intents=intents)

# Speichere pro User die Modi:
bot.mimic_users = {}   # {user_id: tts_flag} für /ape
bot.mock_users = {}    # {user_id: tts_flag} für /mock
bot.chat_mode = False  # Globaler Chat-Modus
bot.maggus_mode = False  # Wenn aktiviert, antwortet der Bot im Markus-Rühl-Stil
bot.chat_history = {}  # {channel_id: [ {"role": "user"|"assistant", "content": str}, ... ] }

MAX_HISTORY = 10  # Maximale Anzahl an Nachrichten im Verlauf pro Channel

# /ape Slash-Befehl
@bot.tree.command(name="ape", description="Aktiviert den Imitationsmodus für einen Benutzer.")
async def ape(interaction: discord.Interaction, member: discord.Member, laut: bool = False):
    bot.mimic_users[member.id] = laut
    await interaction.response.send_message(
        f"Imitationsmodus für **{member.display_name}** aktiviert (TTS: {laut}).",
        ephemeral=True
    )

# /noape Slash-Befehl
@bot.tree.command(name="noape", description="Deaktiviert den Imitationsmodus für einen Benutzer.")
async def noape(interaction: discord.Interaction, member: discord.Member):
    if member.id in bot.mimic_users:
        bot.mimic_users.pop(member.id)
        await interaction.response.send_message(
            f"Imitationsmodus für **{member.display_name}** wurde deaktiviert.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"**{member.display_name}** war nicht im Imitationsmodus.",
            ephemeral=True
        )

# /mock Slash-Befehl (kombinierter Modus)
@bot.tree.command(name="mock", description="Aktiviert den kombinierten Modus (lowercase, 'selber <text> du hurensohn').")
async def mock(interaction: discord.Interaction, member: discord.Member, laut: bool = False):
    bot.mock_users[member.id] = laut
    await interaction.response.send_message(
        f"Kombinierter Modus für **{member.display_name}** aktiviert (TTS: {laut}).",
        ephemeral=True
    )

# /nomock Slash-Befehl
@bot.tree.command(name="nomock", description="Deaktiviert den kombinierten Modus für einen Benutzer.")
async def nomock(interaction: discord.Interaction, member: discord.Member):
    if member.id in bot.mock_users:
        bot.mock_users.pop(member.id)
        await interaction.response.send_message(
            f"Kombinierter Modus für **{member.display_name}** wurde deaktiviert.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"**{member.display_name}** war nicht im kombinierten Modus.",
            ephemeral=True
        )

# /gpt Slash-Befehl
@bot.tree.command(name="gpt", description="Frage den GPT-Chatbot.")
async def gpt(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        response = client_api.responses.create(
            model="gpt-4o-mini",
            instructions="Du bist ein allwissender Assistent. Schreibe maximal 200 Wörter.",
            max_output_tokens=300,
            input=prompt,
        )
        answer = response.output_text.strip()
    except Exception as e:
        answer = f"Fehler beim Abrufen der Antwort: {e}"
    await interaction.followup.send(answer)
    print(response)

# /image Slash-Befehl
@bot.tree.command(name="image", description="Generiert ein Bild mit DALL·E 3 basierend auf einem Prompt.")
async def image(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        response = client_api.images.generate(
            model="dall-e-3",
            prompt=prompt,
            quality="standard",
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
    except Exception as e:
        image_url = f"Fehler beim Abrufen des Bildes: {e}"
    await interaction.followup.send(image_url)

# /chat Slash-Befehl (globaler Chat-Modus aktivieren)
@bot.tree.command(name="chat", description="Aktiviert den globalen Chat-Modus.")
async def chat(interaction: discord.Interaction):
    bot.chat_mode = True
    await interaction.response.send_message("Chat-Modus aktiviert.", ephemeral=True)

# /nochat Slash-Befehl (globalen Chat-Modus deaktivieren)
@bot.tree.command(name="nochat", description="Deaktiviert den globalen Chat-Modus.")
async def nochat(interaction: discord.Interaction):
    bot.chat_mode = False
    await interaction.response.send_message("Chat-Modus deaktiviert.", ephemeral=True)

# /maggus Slash-Befehl (Markus-Rühl-Stil aktivieren)
@bot.tree.command(name="maggus", description="Aktiviert den Markus-Rühl-Stil für Antworten.")
async def maggus(interaction: discord.Interaction):
    bot.maggus_mode = True
    await interaction.response.send_message("Markus-Rühl-Stil aktiviert.", ephemeral=True)

# /nomaggus Slash-Befehl (Markus-Rühl-Stil deaktivieren)
@bot.tree.command(name="nomaggus", description="Deaktiviert den Markus-Rühl-Stil für Antworten.")
async def nomaggus(interaction: discord.Interaction):
    bot.maggus_mode = False
    await interaction.response.send_message("Markus-Rühl-Stil deaktiviert.", ephemeral=True)

# Ereignis: Verarbeitung eingehender Nachrichten
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Prüfe zuerst die speziellen Modi:
    if message.author.id in bot.mimic_users:
        transformed = ape_transform(message.content)
        tts_flag = bot.mimic_users[message.author.id]
        await message.channel.send(transformed, tts=tts_flag)
    elif message.author.id in bot.mock_users:
        response = f"selber {message.content.lower()} du hurensohn"
        tts_flag = bot.mock_users[message.author.id]
        await message.channel.send(response, tts=tts_flag)
    else:
        # Globaler Chat-Modus: Überlege, ob der Bot antworten soll.
        # Der Bot antwortet, wenn "dr. mehmer" vorkommt oder wenn die Nachricht mit einem Fragezeichen endet.
        if bot.chat_mode:
            trigger = False
            content_lower = message.content.lower()
            if "dr. mehmer" in content_lower or message.content.strip().endswith("?"):
                trigger = True
            if trigger:
                channel_id = message.channel.id
                # Initialisiere den Chat-Verlauf für den Channel, falls nicht vorhanden
                if channel_id not in bot.chat_history:
                    bot.chat_history[channel_id] = []
                # Füge die User-Nachricht zum Verlauf hinzu
                bot.chat_history[channel_id].append({"role": "user", "content": message.content})
                if len(bot.chat_history[channel_id]) > MAX_HISTORY:
                    bot.chat_history[channel_id] = bot.chat_history[channel_id][-MAX_HISTORY:]
                # Falls der Markus-Rühl-Stil aktiviert ist, wähle einen zufälligen Spruch aus.
                if bot.maggus_mode:
                    answer = random.choice(maggus_phrases)
                else:
                    # Generiere eine Antwort basierend auf dem Verlauf
                    answer = generate_chat_response(bot.chat_history[channel_id])
                await message.channel.send(answer)
                # Füge die Bot-Antwort zum Verlauf hinzu
                bot.chat_history[channel_id].append({"role": "assistant", "content": answer})

    # Damit auch klassische Befehle verarbeitet werden
    await bot.process_commands(message)

# Sync-Befehl (nur für den Bot-Owner)
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as: {bot.user} (ID: {bot.user.id})")
    print("Slash-Commands sollten jetzt verfügbar sein.")

bot.run(os.getenv("BOT_TOKEN"))
