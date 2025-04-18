import io
import discord
from discord.ext import commands
from typing import Literal
from utils.graphic_utils import GraphicUtils

graphic_utils = GraphicUtils()

def parse_decimal(value: str) -> float:
    """
    Wandelt String in Float um (Komma oder Punkt).

    :param value: Dezimalzahl als String.
    :return: Float-Wert.
    :raises: commands.BadArgument bei ungültigem Format.
    """
    try:
        return float(value)
    except ValueError:
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            raise commands.BadArgument(f'Ungültiges Dezimalformat: {value}')

class WatermarkCog(commands.Cog):
    """
    Cog für Graustufen- und Wasserzeichenbefehle.
    """
    def __init__(self, bot: commands.Bot):
        """
        Konstruktor für WatermarkCog.

        :param bot: Bot-Instanz.
        :return: None
        """
        self.bot = bot

    @commands.hybrid_command(name='sw', description='Konvertiert Medien in Schwarz-Weiß')
    async def sw(self, ctx: commands.Context, input_file: discord.Attachment):
        """
        Konvertiert Bild oder Video in Graustufen.

        :param ctx: Command-Kontext.
        :param input_file: Eingabedatei als Attachment.
        :return: None
        """
        await ctx.defer()
        # Datei herunterladen
        try:
            data = await input_file.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Herunterladen: {e}')
        name = input_file.filename.lower()
        # Format erkennen
        if name.endswith(('.png','.jpg','.bmp')):
            result = graphic_utils.convert_to_grayscale_image(data)
            out_name = 'sw_result.png'
        elif name.endswith(('.mp4','.avi')):
            result = graphic_utils.convert_to_grayscale_video(data)
            out_name = 'sw_result.mp4'
        else:
            return await ctx.send('Ungültiges Dateiformat.')
        # Datei senden
        buf = io.BytesIO(result)
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename=out_name))

    @commands.hybrid_command(name='watermark', description='Wasserzeichen auf Bild oder Video anwenden')
    async def watermark(self,
                        ctx: commands.Context,
                        input_file: discord.Attachment,
                        watermark_file: discord.Attachment,
                        position: Literal['top-left','top-right','bottom-left','bottom-right','center']='center',
                        scale: str='1.0',
                        transparency: str='1.0'):
        """
        Fügt Wasserzeichen zu Bild/Video hinzu.

        :param ctx: Command-Kontext.
        :param input_file: Originaldatei.
        :param watermark_file: Wasserzeichen-Datei.
        :param position: Position des Wasserzeichens.
        :param scale: Skalierung als String.
        :param transparency: Transparenz als String.
        :return: None
        """
        await ctx.defer()
        # Dateien herunterladen
        try:
            data_in = await input_file.read()
            data_wm = await watermark_file.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Herunterladen: {e}')
        # Parameter parsen
        try:
            sc = parse_decimal(scale)
            tr = parse_decimal(transparency)
        except commands.BadArgument as e:
            return await ctx.send(f'Fehler: {e}')
        name = input_file.filename.lower()
        # Bild oder Video verarbeiten
        if name.endswith(('.png','.jpg')):
            out = graphic_utils.watermark_image_file(data_in, data_wm, position, sc, tr)
            out_name = 'watermark_result.png'
        elif name.endswith(('.mp4','.mov')):
            out = graphic_utils.watermark_video_file(data_in, data_wm, position, sc, tr)
            out_name = 'watermark_result.mp4'
        else:
            return await ctx.send('Ungültiges Dateiformat.')
        # Ergebnis senden
        buf2 = io.BytesIO(out)
        buf2.seek(0)
        await ctx.send(file=discord.File(buf2, filename=out_name))

async def setup(bot: commands.Bot):
    """
    Registriert WatermarkCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(WatermarkCog(bot))
