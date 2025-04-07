import discord
import io
import numpy as np
from discord.ext import commands
from scipy.io import wavfile
from utils.audio_effects import AudioEffects

audio_fx = AudioEffects()

class AudioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="slowed", description="Verlangsame das Audio auf 85 % (Slowed-Only).")
    async def slowed(
            self,
            ctx: commands.Context,
            input_audio: discord.Attachment
    ):
        await ctx.defer()
        try:
            rate_in, data_in = await audio_fx.load_audio_from_attachment(input_audio)
        except Exception as e:
            return await ctx.send(f"Fehler: {e}")

        slowed_data = audio_fx.slow_audio(data_in, slow_factor=0.85)
        slowed_int16 = np.int16(slowed_data * 32767)
        buffer_out = io.BytesIO()
        try:
            wavfile.write(buffer_out, rate_in, slowed_int16)
        except Exception as e:
            return await ctx.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        buffer_out.seek(0)
        await ctx.send(file=discord.File(buffer_out, filename="slowed_result.wav"))

    @commands.hybrid_command(name="slowed_reverb", description="Slowed+Reverb: Audio ~15% langsamer & Hall-Effekt.")
    async def slowed_reverb(
            self,
            ctx: commands.Context,
            input_audio: discord.Attachment,
            impulse_audio: discord.Attachment
    ):
        await ctx.defer()
        try:
            rate_x, x_data = await audio_fx.load_audio_from_attachment(input_audio)
            rate_h, h_data = await audio_fx.load_audio_from_attachment(impulse_audio)
        except Exception as e:
            return await ctx.send(f"Fehler beim Einlesen der Dateien: {e}")

        if rate_x != rate_h:
            try:
                h_data = audio_fx.refined_resample_audio(h_data, rate_h, rate_x)
                rate_h = rate_x
            except Exception as e:
                return await ctx.send(f"Fehler beim Resampling: {e}")
        try:
            y = audio_fx.refined_convolve_audio(x_data, h_data)
        except Exception as e:
            return await ctx.send(f"Fehler bei der Faltung: {e}")
        slowed = audio_fx.slow_audio(y, slow_factor=0.85)
        slowed_int16 = np.int16(slowed * 32767)
        buffer_out = io.BytesIO()
        try:
            wavfile.write(buffer_out, rate_x, slowed_int16)
        except Exception as e:
            return await ctx.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        buffer_out.seek(0)
        await ctx.send(file=discord.File(buffer_out, filename="slowed_reverb_result.wav"))

    @commands.hybrid_command(name="reverb", description="Falte ein Audiosignal mit einer Impulsantwort.")
    async def reverb(
            self,
            ctx: commands.Context,
            input_audio: discord.Attachment,
            impulse_audio: discord.Attachment
    ):
        await ctx.defer()
        try:
            rate_x, x_data = await audio_fx.load_audio_from_attachment(input_audio)
            rate_h, h_data = await audio_fx.load_audio_from_attachment(impulse_audio)
        except Exception as e:
            return await ctx.send(f"Fehler beim Einlesen der Dateien: {e}")

        if rate_x != rate_h:
            try:
                h_data = audio_fx.refined_resample_audio(h_data, rate_h, rate_x)
                rate_h = rate_x
            except Exception as e:
                return await ctx.send(f"Fehler beim Resampling: {e}")
        try:
            y = audio_fx.refined_convolve_audio(x_data, h_data)
        except Exception as e:
            return await ctx.send(f"Fehler bei der Faltung: {e}")
        y_int16 = np.int16(y * 32767)
        buffer_out = io.BytesIO()
        try:
            wavfile.write(buffer_out, rate_x, y_int16)
        except Exception as e:
            return await ctx.send(f"Fehler beim Erzeugen der Ausgabedatei: {e}")
        buffer_out.seek(0)
        await ctx.send(file=discord.File(buffer_out, filename="reverb_result.wav"))

async def setup(bot):
    await bot.add_cog(AudioCog(bot))
