import os
import discord
import random
import asyncio
import numpy as np
import io

from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional

from openai import OpenAI
from scipy.io import wavfile
from scipy import signal
from pydub import AudioSegment

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

##########################################################
# Klasse für Audioeffekte & Laden der Dateien
##########################################################
class AudioEffects:
    """
    Alle Audiofunktionen liegen hier:
    - load_audio_from_attachment
    - refined_resample_audio
    - refined_convolve_audio
    - slow_audio
    """

    @staticmethod
    async def load_audio_from_attachment(attachment: discord.Attachment) -> tuple[int, np.ndarray]:
        """
        Lädt das übergebene Attachment (WAV oder MP3) in den RAM,
        decodiert es und gibt (sample_rate, samples) zurück.
        """
        file_bytes = await attachment.read()
        name_lower = attachment.filename.lower()

        if name_lower.endswith(".wav"):
            with io.BytesIO(file_bytes) as f:
                rate, data = wavfile.read(f)
            return rate, data

        elif name_lower.endswith(".mp3"):
            audio_seg = AudioSegment.from_file(io.BytesIO(file_bytes), format="mp3")
            samples = np.array(audio_seg.get_array_of_samples())
            rate = audio_seg.frame_rate

            # Mehrkanal?
            if audio_seg.channels == 2:
                samples = samples.reshape((-1, 2))
            return rate, samples

        else:
            raise ValueError("Es sind nur .wav oder .mp3 erlaubt.")

    @staticmethod
    def refined_resample_audio(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """Resampling von Audiodaten, falls die Abtastraten unterschiedlich sind."""
        if orig_rate == target_rate:
            return audio
        target_length = int(len(audio) * target_rate / orig_rate)
        return signal.resample(audio, target_length)

    @staticmethod
    def refined_convolve_audio(x: np.ndarray, h: np.ndarray) -> np.ndarray:
        """
        Führt die Faltung durch und gibt ein normalisiertes Stereo-Signal zurück.
        """
        if x.ndim == 1:
            x = np.expand_dims(x, axis=1)
        if h.ndim == 1:
            h = np.expand_dims(h, axis=1)

        if x.shape[1] == 1 and h.shape[1] == 1:
            y = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            y = np.column_stack((y, y))  # Stereo
        elif x.shape[1] == 1 and h.shape[1] == 2:
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 0], h[:, 1], mode="full")
            y = np.column_stack((left, right))
        elif x.shape[1] == 2 and h.shape[1] == 1:
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 1], h[:, 0], mode="full")
            y = np.column_stack((left, right))
        else:
            # x Stereo, h Stereo
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 1], h[:, 1], mode="full")
            y = np.column_stack((left, right))

        max_val = np.max(np.abs(y))
        if max_val > 0:
            y /= max_val
        return y

    @staticmethod
    def slow_audio(data: np.ndarray, slow_factor: float = 0.85) -> np.ndarray:
        """
        Verlangsamt das Audio per Resampling. standard: 85% speed -> 15% langsamer
        """
        new_len = int(len(data) / slow_factor)

        if data.ndim == 1:
            slowed = signal.resample(data, new_len)
        else:
            left = signal.resample(data[:, 0], new_len)
            right = signal.resample(data[:, 1], new_len)
            slowed = np.column_stack((left, right))

        max_val = np.max(np.abs(slowed))
        if max_val > 0:
            slowed /= max_val

        return slowed


##########################################################
# Bot / Setup
##########################################################

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Deine bisherigen Variablen und Modi
bot.mimic_users = {}
bot.mock_users = {}
bot.chat_mode = False
bot.maggus_mode = False
bot.chat_history = {}

MAX_HISTORY = 10

# Instanz der AudioEffects-Klasse, die wir für alle Kommandos verwenden können
audio_fx = AudioEffects()

##########################################################
# Hilfsfunktion ape_transform für on_message
##########################################################
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

##########################################################
# 1) /slowed
##########################################################
@bot.tree.command(name="slowed", description="Verlangsame das Audio auf 85 % (Slowed-Only).")
async def slowed(
    interaction: discord.Interaction,
    input_audio: discord.Attachment
):
    await interaction.response.defer(thinking=True)

    try:
        rate_in, data_in = await audio_fx.load_audio_from_attachment(input_audio)
    except ValueError as e:
        await interaction.followup.send(f"Dateiformat-Fehler: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Einlesen der Datei: {e}")
        return

    # Audio um 15% verlangsamen
    slowed_data = audio_fx.slow_audio(data_in, slow_factor=0.85)
    slowed_int16 = np.int16(slowed_data * 32767)

    # WAV erstellen + zurücksenden
    buffer_out = io.BytesIO()
    try:
        wavfile.write(buffer_out, rate_in, slowed_int16)
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        return

    buffer_out.seek(0)
    try:
        await interaction.followup.send(
            content="Hier ist dein verlangsames Audio (85 % Speed):",
            file=discord.File(buffer_out, filename="slowed_result.wav")
        )
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Senden der Ergebnisdatei: {e}")


##########################################################
# 2) /slowed_reverb
##########################################################
@bot.tree.command(name="slowed_reverb", description="Slowed+Reverb: Audio ~15% langsamer & Hall-Effekt.")
async def slowed_reverb(
    interaction: discord.Interaction,
    input_audio: discord.Attachment,
    impulse_audio: discord.Attachment
):
    await interaction.response.defer(thinking=True)

    try:
        rate_x, x_data = await audio_fx.load_audio_from_attachment(input_audio)
        rate_h, h_data = await audio_fx.load_audio_from_attachment(impulse_audio)
    except ValueError as e:
        await interaction.followup.send(f"Dateiformat-Fehler: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Einlesen der Dateien: {e}")
        return

    # Resample, falls nötig
    if rate_x != rate_h:
        try:
            h_data = audio_fx.refined_resample_audio(h_data, rate_h, rate_x)
            rate_h = rate_x
        except Exception as e:
            await interaction.followup.send(f"Fehler beim Resampling: {e}")
            return

    # Faltung
    try:
        y = audio_fx.refined_convolve_audio(x_data, h_data)
    except Exception as e:
        await interaction.followup.send(f"Fehler bei der Faltung: {e}")
        return

    # Audio verlangsamen
    slowed = audio_fx.slow_audio(y, slow_factor=0.85)
    slowed_int16 = np.int16(slowed * 32767)

    # WAV zurücksenden
    buffer_out = io.BytesIO()
    try:
        wavfile.write(buffer_out, rate_x, slowed_int16)
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        return

    buffer_out.seek(0)
    try:
        await interaction.followup.send(
            content="Hier ist dein Slowed+Reverb-Audio:",
            file=discord.File(buffer_out, filename="slowed_reverb_result.wav")
        )
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Senden der Ergebnisdatei: {e}")


##########################################################
# 3) /reverb
##########################################################
@bot.tree.command(name="reverb", description="Falte ein Audiosignal (WAV/MP3) mit einer Impulsantwort (WAV/MP3).")
async def reverb(
    interaction: discord.Interaction,
    input_audio: discord.Attachment,
    impulse_audio: discord.Attachment
):
    await interaction.response.defer(thinking=True)

    try:
        rate_x, x_data = await audio_fx.load_audio_from_attachment(input_audio)
        rate_h, h_data = await audio_fx.load_audio_from_attachment(impulse_audio)
    except ValueError as e:
        await interaction.followup.send(f"Dateiformat-Fehler: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Einlesen der Dateien: {e}")
        return

    # Resample, falls nötig
    if rate_x != rate_h:
        try:
            h_data = audio_fx.refined_resample_audio(h_data, rate_h, rate_x)
            rate_h = rate_x
        except Exception as e:
            await interaction.followup.send(f"Fehler beim Resampling: {e}")
            return

    # Faltung
    try:
        y = audio_fx.refined_convolve_audio(x_data, h_data)
    except Exception as e:
        await interaction.followup.send(f"Fehler bei der Faltung: {e}")
        return

    y_int16 = np.int16(y * 32767)
    buffer_out = io.BytesIO()
    try:
        wavfile.write(buffer_out, rate_x, y_int16)
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        return

    buffer_out.seek(0)
    try:
        await interaction.followup.send(
            content="Hier ist dein gefaltetes Audio:",
            file=discord.File(buffer_out, filename="reverb_result.wav")
        )
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Senden der Ergebnisdatei: {e}")


##########################################################
# Weitere Befehle (ape, mock, etc.)
##########################################################
@bot.tree.command(name="ape", description="Aktiviert den Imitationsmodus für einen Benutzer.")
async def ape(interaction: discord.Interaction, member: discord.Member, laut: bool = False):
    bot.mimic_users[member.id] = laut
    await interaction.response.send_message(
        f"Imitationsmodus für **{member.display_name}** aktiviert (TTS: {laut}).",
        ephemeral=True
    )

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

@bot.tree.command(name="mock", description="Aktiviert den kombinierten Modus (lowercase, 'selber <text> du hurensohn').")
async def mock(interaction: discord.Interaction, member: discord.Member, laut: bool = False):
    bot.mock_users[member.id] = laut
    await interaction.response.send_message(
        f"Kombinierter Modus für **{member.display_name}** aktiviert (TTS: {laut}).",
        ephemeral=True
    )

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

@bot.tree.command(name="chat", description="Aktiviert den globalen Chat-Modus.")
async def chat(interaction: discord.Interaction):
    bot.chat_mode = True
    await interaction.response.send_message("Chat-Modus aktiviert.", ephemeral=True)

@bot.tree.command(name="nochat", description="Deaktiviert den globalen Chat-Modus.")
async def nochat(interaction: discord.Interaction):
    bot.chat_mode = False
    await interaction.response.send_message("Chat-Modus deaktiviert.", ephemeral=True)

@bot.tree.command(name="maggus", description="Aktiviert den Markus-Rühl-Stil für Antworten.")
async def maggus(interaction: discord.Interaction):
    bot.maggus_mode = True
    await interaction.response.send_message("Markus-Rühl-Stil aktiviert.", ephemeral=True)

@bot.tree.command(name="nomaggus", description="Deaktiviert den Markus-Rühl-Stil für Antworten.")
async def nomaggus(interaction: discord.Interaction):
    bot.maggus_mode = False
    await interaction.response.send_message("Markus-Rühl-Stil deaktiviert.", ephemeral=True)

##########################################################
# on_message-Event (ape/mock/chat)
##########################################################
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id in bot.mimic_users:
        transformed = ape_transform(message.content)
        tts_flag = bot.mimic_users[message.author.id]
        await message.channel.send(transformed, tts=tts_flag)

    elif message.author.id in bot.mock_users:
        response = f"selber {message.content.lower()} du hurensohn"
        tts_flag = bot.mock_users[message.author.id]
        await message.channel.send(response, tts=tts_flag)

    else:
        if bot.chat_mode:
            trigger = False
            if bot.chat_mode and (bot.user in message.mentions):
                trigger = True
            if trigger:
                channel_id = message.channel.id
                if channel_id not in bot.chat_history:
                    bot.chat_history[channel_id] = []
                bot.chat_history[channel_id].append({"role": "user", "content": message.content})
                if len(bot.chat_history[channel_id]) > MAX_HISTORY:
                    bot.chat_history[channel_id] = bot.chat_history[channel_id][-MAX_HISTORY:]

                if client:
                    # Wenn Maggus aktiv, nutze spezielle Prompt
                    if bot.maggus_mode:
                        instructions = (
                            "Du bist Markus Rühl, ein renommierter deutscher Profi-Bodybuilder, "
                            "bekannt für deine beeindruckende Muskelmasse und deinen unverwechselbaren Humor. "
                            "In deinen Antworten verwendest du häufig Insider-Begriffe und Phrasen wie 'Bob Tschigerillo', 'Abbelschorle', 'Muss net schmegge, muss wirke' und 'Muss wirke'. "
                            "Deine Ausdrucksweise ist direkt, humorvoll und gelegentlich mit hessischem Dialekt durchsetzt. "
                            "Du betonst die Bedeutung von harter Arbeit, Disziplin und einer pragmatischen Herangehensweise an Training und Ernährung. "
                            "Dein Humor ist oft selbstironisch, und du nimmst dich selbst nicht zu ernst. Deine Antworten sollen die Leser unterhalten und gleichzeitig Einblicke in die Welt des professionellen Bodybuildings geben."
                            "Wenn irgendwas mit Bob Chigerillo kommt, bilde einen logischen Satz mit ausgebobt. Das Ausgebobbt-Meme mit Markus Rühl bezieht sich auf humorvolle Interaktionen zwischen dem deutschen Profi-Bodybuilder "
                            "Markus Rühl und Bob Cicherillo, einem bekannten Bodybuilding-Kommentator. In diesen Videos verwendet Rühl den Begriff ausgebobbt in Anspielung auf Cicherillo, welcher bei einem Wettkampf gegen ihn verloren hat. Es hatte sich also ausgebobt für den Bob."
                            "Spreche den Gesprächspartner etwas schroff an. "
                            "Beispiele: "
                            "1) Ey, Alter, reiß dich zusammen und pump mal richtig – jetzt wird's fett! "
                            "2) Bruder, keine halben Sachen – du musst die Hanteln knallen lassen! "
                            "3) Komm schon, zeig deine Muckis!"
                        )
                    else:
                        instructions = "Du bist ein lockerer Discord-Bot. Antworte kurz."

                    # GPT-Aufruf
                    try:
                        response = client.responses.create(
                            model="gpt-4o-mini",
                            instructions=instructions,
                            max_output_tokens=150,
                            input=message.content,
                        )
                        answer = response.output_text.strip()
                    except Exception as e:
                        answer = f"Fehler beim Abrufen der Chat-Antwort: {e}"
                else:
                    answer = "GPT nicht verfügbar."

                    # Sende Antwort im Chat
                await message.channel.send(answer)
                bot.chat_history[channel_id].append({"role": "assistant", "content": answer})

                # Stelle sicher, dass Discord noch alle Befehle verarbeitet
            await bot.process_commands(message)

##########################################################
# sync und Start
##########################################################
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~","*","^"]] = None) -> None:
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
