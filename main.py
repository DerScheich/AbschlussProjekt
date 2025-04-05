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

import cv2
import tempfile
import subprocess
##########################################################
# Bot-Setup
##########################################################

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Deine bisherigen Variablen und Modi
bot.mimic_users = {}
bot.mock_users = {}
bot.maggus_mode = False
bot.chat_history = {}

MAX_HISTORY = 10

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

audio_fx = AudioEffects()

##################################################################
#Klasse für Wasserzeichen
##################################################################
class WatermarkHandler:
    """
    Diese Klasse enthält Funktionen zum Hinzufügen von Wasserzeichen zu Bildern und Videos.
    """

    def add_watermark_image(
            self,
            image: np.ndarray,
            watermark: np.ndarray,
            position: str = "center",
            scale: float = 1.0,
            transparency: float = 1.0
    ) -> np.ndarray:
        # Skalierung
        wH, wW = watermark.shape[:2]
        scaled_width = int(wW * scale)
        scaled_height = int(wH * scale)
        watermark_resized = cv2.resize(watermark, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
        wH2, wW2 = watermark_resized.shape[:2]
        positions = {
            "top-left": (0, 0),
            "top-right": (w - wW2, 0),
            "bottom-left": (0, h - wH2),
            "bottom-right": (w - wW2, h - wH2),
            "center": ((w - wW2) // 2, (h - wH2) // 2)
        }
        if position not in positions:
            position = "center"
        x, y = positions[position]
        if x < 0 or y < 0 or (x + wW2 > w) or (y + wH2 > h):
            return image
        roi = image[y:y + wH2, x:x + wW2]
        if watermark_resized.shape[2] == 4:
            alpha_channel = watermark_resized[:, :, 3] / 255.0 * transparency
            color_channels = watermark_resized[:, :, :3]
        else:
            alpha_channel = np.ones((wH2, wW2), dtype=np.float32) * transparency
            color_channels = watermark_resized
        for c in range(3):
            roi[:, :, c] = alpha_channel * color_channels[:, :, c] + (1 - alpha_channel) * roi[:, :, c]
        image[y:y + wH2, x:x + wW2] = roi
        return image

    def watermark_video_file(
        self,
        video_bytes: bytes,
        watermark_bytes: bytes,
        position: str,
        scale: float,
        transparency: float
    ) -> bytes:
        temp_dir = tempfile.gettempdir()
        temp_input = os.path.join(temp_dir, "watermark_inputvideo.mp4")
        temp_video = os.path.join(temp_dir, "watermark_tempvideo.mp4")
        final_output = os.path.join(temp_dir, "watermark_final_output.mp4")
        with open(temp_input, "wb") as f:
            f.write(video_bytes)
        wm_array = np.frombuffer(watermark_bytes, np.uint8)
        wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)
        if wm_img is None:
            raise ValueError("Wasserzeichen-Datei konnte nicht als Bild decodiert werden.")
        cap = cv2.VideoCapture(temp_input)
        if not cap.isOpened():
            raise ValueError("Eingabevideo konnte nicht geöffnet werden.")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_vid = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_result = self.add_watermark_image(frame, wm_img, position, scale, transparency)
            out_vid.write(frame_result)
        cap.release()
        out_vid.release()
        # Füge Audio hinzu und re-kodiere mit ffmpeg (H.264/AAC)
        command = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", temp_input,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            final_output
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception("FFmpeg Error: " + result.stderr.decode("utf-8"))
        with open(final_output, "rb") as f:
            result_bytes = f.read()
        return result_bytes

    def watermark_frame(
        self,
        frame: np.ndarray,
        wm_img: np.ndarray,
        position: str,
        scale: float,
        transparency: float
    ) -> np.ndarray:
        """Wendet ein Wasserzeichen auf einen einzelnen Frame an."""
        return self.add_watermark_image(
            image=frame,
            watermark=wm_img,
            position=position,
            scale=scale,
            transparency=transparency
        )

    def watermark_image_file(
        self,
        image_bytes: bytes,
        watermark_bytes: bytes,
        position: str,
        scale: float,
        transparency: float
    ) -> bytes:
        """Öffnet ein Bild + Wasserzeichen aus Bytes, setzt WM drauf und gibt PNG-Bytes zurück."""
        # decode input image
        in_array = np.frombuffer(image_bytes, np.uint8)
        in_img = cv2.imdecode(in_array, cv2.IMREAD_COLOR)
        # decode watermark
        wm_array = np.frombuffer(watermark_bytes, np.uint8)
        wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)

        if in_img is None or wm_img is None:
            raise ValueError("Eingabedatei oder Wasserzeichen nicht decodierbar als Bild.")

        # WM anwenden
        result = self.add_watermark_image(in_img, wm_img, position, scale, transparency)

        # Result als PNG codieren
        success, encoded = cv2.imencode(".png", result)
        if not success:
            raise ValueError("Fehler beim Kodieren des Ergebnis-Bildes.")

        return encoded.tobytes()

watermark_handler = WatermarkHandler()

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
# /slowed
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
# /slowed_reverb
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
# /reverb
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
# /watermark
##########################################################

@bot.tree.command(name="watermark", description="Wasserzeichen (Bild) auf ein Bild oder Video anwenden.")
async def watermark_cmd(
    interaction: discord.Interaction,
    input_file: discord.Attachment,
    watermark_file: discord.Attachment,
    position: Literal["top-left", "top-right", "bottom-left", "bottom-right", "center"] = "center",
    scale: float = 1.0,
    transparency: float = 1.0
):
    """
    /watermark input_file: (Bild|Video) watermark_file: (Bild) position: ...
               scale=1.0 transparency=1.0
    Gibt watermark_result.png/.mp4 zurück
    """
    await interaction.response.defer(thinking=True)

    try:
        # 1) Bytes lesen
        input_bytes = await input_file.read()
        wm_bytes = await watermark_file.read()
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Herunterladen der Dateien: {e}")
        return

    in_name = input_file.filename.lower()
    out_filename = None
    try:
        # 2) Bild oder Video?
        if in_name.endswith((".png", ".jpg", ".jpeg", ".bmp")):
            # -> Bild
            result_bytes = watermark_handler.watermark_image_file(
                image_bytes=input_bytes,
                watermark_bytes=wm_bytes,
                position=position,
                scale=scale,
                transparency=transparency
            )
            out_filename = "watermark_result.png"

        elif in_name.endswith((".mp4", ".avi", ".mov", ".mkv")):
            # -> Video
            result_bytes = watermark_handler.watermark_video_file(
                video_bytes=input_bytes,
                watermark_bytes=wm_bytes,
                position=position,
                scale=scale,
                transparency=transparency
            )
            out_filename = "watermark_result.mp4"
        else:
            await interaction.followup.send("Eingabedatei muss ein Bild (png/jpg/bmp) oder Video (mp4/avi/mov/mkv) sein!")
            return
    except Exception as e:
        await interaction.followup.send(f"Fehler bei der Wasserzeichen-Verarbeitung: {e}")
        return

    # 3) Antwort senden
    out_buffer = io.BytesIO(result_bytes)
    out_buffer.seek(0)
    await interaction.followup.send(
        content="Hier ist dein Wasserzeichen-Ergebnis:",
        file=discord.File(out_buffer, filename=out_filename)
    )


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
        if bot.user in message.mentions:
            channel_id = message.channel.id
            if channel_id not in bot.chat_history:
                bot.chat_history[channel_id] = []
            # Speichere die aktuelle Nachricht im Verlauf
            bot.chat_history[channel_id].append({"role": "user", "content": message.content})
            if len(bot.chat_history[channel_id]) > MAX_HISTORY:
                bot.chat_history[channel_id] = bot.chat_history[channel_id][-MAX_HISTORY:]

            # Baue den Gesprächsverlauf als String auf
            conversation_prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in bot.chat_history[channel_id])

            if client:
                if bot.maggus_mode:
                    instructions = (
                        "Du bist Markus Rühl, ein renommierter deutscher Profi-Bodybuilder, "
                        "bekannt für deine beeindruckende Muskelmasse und deinen unverwechselbaren Humor. "
                        "In deinen Antworten verwendest du häufig Insider-Begriffe und Phrasen wie 'Bob Tschigerillo', 'Abbelschorle', 'Muss net schmegge, muss wirke' und 'Muss wirke'. "
                        "Deine Ausdrucksweise ist direkt, humorvoll und gelegentlich mit hessischem Dialekt durchsetzt. "
                        "Du betonst die Bedeutung von harter Arbeit, Disziplin und einer pragmatischen Herangehensweise an Training und Ernährung. "
                        "Dein Humor ist oft selbstironisch, und du nimmst dich selbst nicht zu ernst. Deine Antworten sollen die Leser unterhalten und gleichzeitig Einblicke in die Welt des professionellen Bodybuildings geben."
                        "Wenn irgendwas mit Bob Chigerillo kommt, bilde einen logischen Satz mit 'ausgebobt' (als Diss gegen Bob, zB. 'als der Bob mich gesehen hat, hat es sich für ihn ausgebobt' (Da markus Rühl wesentlich breiter und definierter war). "
                        "Spreche den Gesprächspartner etwas schroff an. "
                        "Beispiele: "
                        "1) Ey, Alter, reiß dich zusammen und pump mal richtig – jetzt wird's fett! "
                        "2) Bruder, keine halben Sachen – du musst die Hanteln knallen lassen! "
                        "3) Komm schon, zeig deine Muckis!"
                    )
                else:
                    instructions = "Du bist ein lockerer Chat-Helfer. Antworte kurz."
                try:
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        instructions=instructions,
                        max_output_tokens=150,
                        input=conversation_prompt,  # Hier wird der gesamte Verlauf übergeben
                    )
                    answer = response.output_text.strip()
                except Exception as e:
                    answer = f"Fehler beim Abrufen der Chat-Antwort: {e}"
            else:
                answer = "GPT nicht verfügbar."

            await message.channel.send(answer)
            bot.chat_history[channel_id].append({"role": "assistant", "content": answer})

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
