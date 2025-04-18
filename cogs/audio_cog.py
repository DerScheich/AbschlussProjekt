import discord
import io
import numpy as np
from discord.ext import commands
from scipy.io import wavfile
from utils.audio_utils import AudioEffects

audio_fx = AudioEffects()

class AudioCog(commands.Cog):
    """
    Cog mit Audio-Bearbeitungsbefehlen: slowed, slowed_reverb, reverb, stereo, mono.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialisiert AudioCog.

        :param bot: Bot-Instanz.
        :return: None
        """
        self.bot = bot

    @commands.hybrid_command(name='slowed', description='Verlangsamt Audio auf slow_factor.')
    async def slowed(self, ctx: commands.Context, input_audio: discord.Attachment, slow_factor: float = 0.85):
        """
        Verlangsamt das Audio um slow_factor.

        :param ctx: Command-Kontext.
        :param input_audio: Audio-Attachment.
        :param slow_factor: Verlangsamungsfaktor.
        :return: None
        """
        await ctx.defer()
        try:
            rate, data = await audio_fx.load_audio_from_attachment(input_audio)
        except Exception as e:
            return await ctx.send(f'Fehler: {e}')
        out = audio_fx.slow_audio(data, slow_factor)
        arr = np.int16(out * 32767)
        buf = io.BytesIO()
        try:
            wavfile.write(buf, rate, arr)
        except Exception as e:
            return await ctx.send(f'Fehler Erzeugen Ausgabedatei: {e}')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='slowed_result.wav'))

    @commands.hybrid_command(name='slowed_reverb', description='Slowed+Reverb: Verlangsame und fügen Halleffekt hinzu.')
    async def slowed_reverb(self, ctx: commands.Context, input_audio: discord.Attachment, impulse_audio: discord.Attachment, slow_factor: float = 0.85):
        """
        Kombiniert Verlangsamung und Reverb per Impulsantwort.

        :param ctx: Command-Kontext.
        :param input_audio: Original-Audio.
        :param impulse_audio: Impulsantwort.
        :param slow_factor: Verlangsamungsfaktor.
        :return: None
        """
        await ctx.defer()
        try:
            rate_x, x = await audio_fx.load_audio_from_attachment(input_audio)
            rate_h, h = await audio_fx.load_audio_from_attachment(impulse_audio)
        except Exception as e:
            return await ctx.send(f'Fehler Einlesen: {e}')
        if rate_x != rate_h:
            try:
                h = audio_fx.refined_resample_audio(h, rate_h, rate_x)
                rate_h = rate_x
            except Exception as e:
                return await ctx.send(f'Fehler Resampling: {e}')
        try:
            y = audio_fx.refined_convolve_audio(x, h)
        except Exception as e:
            return await ctx.send(f'Fehler Faltung: {e}')
        out = audio_fx.slow_audio(y, slow_factor)
        arr = np.int16(out * 32767)
        buf = io.BytesIO()
        try:
            wavfile.write(buf, rate_x, arr)
        except Exception as e:
            return await ctx.send(f'Fehler Ausgabedatei: {e}')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='slowed_reverb_result.wav'))

    @commands.hybrid_command(name='reverb', description='Faltet Audio mit einer Impulsantwort.')
    async def reverb(self, ctx: commands.Context, input_audio: discord.Attachment, impulse_audio: discord.Attachment):
        """
        Fügt Halleffekt durch Faltung hinzu.

        :param ctx: Command-Kontext.
        :param input_audio: Original-Audio.
        :param impulse_audio: Impulsantwort.
        :return: None
        """
        await ctx.defer()
        try:
            rate_x, x = await audio_fx.load_audio_from_attachment(input_audio)
            rate_h, h = await audio_fx.load_audio_from_attachment(impulse_audio)
        except Exception as e:
            return await ctx.send(f'Fehler Einlesen: {e}')
        if rate_x != rate_h:
            try:
                h = audio_fx.refined_resample_audio(h, rate_h, rate_x)
                rate_h = rate_x
            except Exception as e:
                return await ctx.send(f'Fehler Resampling: {e}')
        try:
            y = audio_fx.refined_convolve_audio(x, h)
        except Exception as e:
            return await ctx.send(f'Fehler Faltung: {e}')
        arr = np.int16(y * 32767)
        buf = io.BytesIO()
        try:
            wavfile.write(buf, rate_x, arr)
        except Exception as e:
            return await ctx.send(f'Fehler Ausgabedatei: {e}')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='reverb_result.wav'))

    @commands.hybrid_command(name='stereo', description='Wandelt Mono zu Stereo um.')
    async def stereo(self, ctx: commands.Context, input_audio: discord.Attachment):
        """
        Erzeugt Stereo aus Mono mittels Haas-Effekt.

        :param ctx: Command-Kontext.
        :param input_audio: Mono-Audio.
        :return: None
        """
        await ctx.defer()
        try:
            rate, data = await audio_fx.load_audio_from_attachment(input_audio)
        except Exception as e:
            return await ctx.send(f'Fehler Laden: {e}')
        if data.ndim != 1:
            return await ctx.send('Fehler: Kein Mono-Signal')
        try:
            out = audio_fx.mono_to_stereo(data, rate)
        except Exception as e:
            return await ctx.send(f'Fehler Umwandlung: {e}')
        arr = np.int16(out * 32767)
        buf = io.BytesIO()
        try:
            wavfile.write(buf, rate, arr)
        except Exception as e:
            return await ctx.send(f'Fehler Ausgabedatei: {e}')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='stereo_result.wav'))

    @commands.hybrid_command(name='mono', description='Wandelt Stereo zu Mono um.')
    async def mono(self, ctx: commands.Context, input_audio: discord.Attachment):
        """
        Wandelt Stereo zu Mono durch Mittelung beider Kanäle.

        :param ctx: Command-Kontext.
        :param input_audio: Stereo-Audio.
        :return: None
        """
        await ctx.defer()
        try:
            rate, data = await audio_fx.load_audio_from_attachment(input_audio)
        except Exception as e:
            return await ctx.send(f'Fehler Laden: {e}')
        if data.ndim != 2 or data.shape[1] != 2:
            return await ctx.send('Fehler: Kein Stereo-Signal')
        try:
            out = audio_fx.stereo_to_mono(data)
        except Exception as e:
            return await ctx.send(f'Fehler Umwandlung: {e}')
        arr = np.int16(out * 32767)
        buf = io.BytesIO()
        try:
            wavfile.write(buf, rate, arr)
        except Exception as e:
            return await ctx.send(f'Fehler Ausgabedatei: {e}')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='mono_result.wav'))

async def setup(bot: commands.Bot):
    """
    Registriert AudioCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(AudioCog(bot))