import os
import discord
from openai import OpenAI
from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
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


# Aktivieren der benötigten Intents (für Nachrichteninhalt und Member-Daten)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Erstelle den Bot (Prefix wird hier nur für klassische Befehle genutzt)
bot = commands.Bot(command_prefix="/", intents=intents)

# Speichere für den Imitationsmodus, welche User (über ihre ID) transformiert werden sollen.
bot.mimic_users = {}  # Format: {user_id: tts_flag}


# Registriere den Slash-Befehl /ape
@bot.tree.command(name="ape",
                  description="Aktiviert den Imitationsmodus für einen Benutzer (abwechselnd Groß-/Kleinschreibung).")
async def ape(interaction: discord.Interaction, member: discord.Member, laut: bool = False):
    bot.mimic_users[member.id] = laut
    await interaction.response.send_message(
        f"Imitationsmodus für **{member.display_name}** aktiviert (TTS: {laut}).",
        ephemeral=True
    )

# Registriere den Slash-Befehl /noape, der den Imitationsmodus für einen Benutzer deaktiviert.
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

# Registriere den Slash-Befehl /gpt für den GPT-Chatbot
@bot.tree.command(name="gpt", description="Frage den GPT-Chatbot. Gib einen Prompt ein und erhalte eine Antwort.")
async def gpt(interaction: discord.Interaction, prompt: str):
    # Deferte die Antwort, falls die Anfrage etwas länger dauert (Antwort nur für den Befehlsnutzer sichtbar)
    await interaction.response.defer()
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            instructions="Du bist ein allwissender Assistent. Schreibe maximal 200 Wörter (300Tokens).",
            max_output_tokens = 300,
            input=prompt,
        )
        answer = response.output_text.strip()
    except Exception as e:
        answer = f"Fehler beim Abrufen der Antwort: {e}"
    await interaction.followup.send(answer)
    print(response)

# Registriere den Slash-Befehl /image für DALL·E 3
@bot.tree.command(name="image", description="Generiert ein Bild mit DALL·E 3 (Standard, 1024x1024) basierend auf einem Prompt.")
async def image(interaction: discord.Interaction, prompt: str):
    # Deferte die Antwort, um längere Wartezeiten zu kaschieren
    await interaction.response.defer()
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            quality= "standard",
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
    except Exception as e:
        image_url = f"Fehler beim Abrufen des Bildes: {e}"
    # Sende das Bild (bzw. den Link) öffentlich in den Channel, wie Midjourney
    await interaction.followup.send(image_url)

# Bei jeder Nachricht wird geprüft, ob der Autor im Imitationsmodus ist.
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id in bot.mimic_users:
        transformed = ape_transform(message.content)
        tts_flag = bot.mimic_users[message.author.id]
        await message.channel.send(transformed, tts=tts_flag)

    # Damit auch klassische Befehle verarbeitet werden
    await bot.process_commands(message)


# Sync-Befehl (nur für den Bot-Owner, nur in einem Guild-Kontext)

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
    # Synchronisiere global (alternativ: spezifisch für eine Guild)
    await bot.tree.sync()
    print(f"Logged in as: {bot.user} (ID: {bot.user.id})")
    print("Slash-Commands sollten jetzt verfügbar sein.")


bot.run(os.getenv("BOT_TOKEN"))
