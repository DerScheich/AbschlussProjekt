import io
import discord
import os
import aiohttp
from discord.ext import commands
from typing import Literal
from utils.graphic_utils import GraphicUtils
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

graphic_utils = GraphicUtils()

class GraphicCog(commands.Cog):
    """
    Cog für Bildbearbeitung und Bild-Generierung.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialisiert GraphicCog.

        :param bot: Bot-Instanz.
        :return: None
        """
        self.bot = bot

    @commands.hybrid_command(
        name='image',
        description='Generiert ein Bild mit DALL·E 3 (Standard, 1024×1024).'
    )
    async def image(self, ctx: commands.Context, prompt: str):
        """
        Generiert ein Bild via DALL·E 3, sendet es als Embed mit Dateianhang
        """
        # Ack für Slash-Command bzw. Typing-Indikator
        await ctx.defer()

        # Bild generieren
        try:
            resp = client.images.generate(
                model='dall-e-3',
                prompt=prompt,
                quality='standard',
                n=1,
                size='1024x1024'
            )
            image_url = resp.data[0].url
        except Exception as e:
            return await ctx.send(f'Fehler beim Abrufen des Bildes: {e}')

        # Bild herunterladen
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as r:
                    if r.status != 200:
                        return await ctx.send(f'Fehler beim Herunterladen des Bildes: HTTP {r.status}')
                    img_data = await r.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Herunterladen des Bildes: {e}')

        # Datei und Embed vorbereiten
        filename = 'generated_image.png'
        file = discord.File(io.BytesIO(img_data), filename=filename)
        embed = discord.Embed()
        embed.set_image(url=f'attachment://{filename}')
        embed.set_footer(text=f'Generiertes Bild mit folgendem Prompt: {prompt}')

        await ctx.send(file=file, embed=embed)

    @commands.hybrid_command(name='sw', description='Konvertiert Medien in Schwarz-Weiß')
    async def sw(self, ctx: commands.Context, input_file: discord.Attachment):
        """
        Konvertiert Bild oder Video in Graustufen.

        :param ctx: Command-Kontext.
        :param input_file: Eingabedatei als Attachment.
        :return: None
        """
        await ctx.defer()
        try:
            data = await input_file.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Herunterladen: {e}')
        name = input_file.filename.lower()
        if name.endswith(('.png', '.jpg', '.bmp')):
            result = graphic_utils.convert_to_grayscale_image(data)
            out_name = 'sw_result.png'
        elif name.endswith(('.mp4', '.avi')):
            result = graphic_utils.convert_to_grayscale_video(data)
            out_name = 'sw_result.mp4'
        else:
            return await ctx.send('Ungültiges Dateiformat.')
        buf = io.BytesIO(result)
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename=out_name))

    @commands.hybrid_command(name='watermark', description='Wasserzeichen auf Bild oder Video anwenden')
    async def watermark(self, ctx: commands.Context, input_file: discord.Attachment, watermark_file: discord.Attachment,
                        position: Literal['top-left','top-right','bottom-left','bottom-right','center']='center',
                        scale: str='1.0', transparency: str='1.0'):
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
        try:
            data_in = await input_file.read()
            data_wm = await watermark_file.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Herunterladen: {e}')
        # Parameter parsen
        def parse_decimal(val: str) -> float:
            try:
                return float(val)
            except ValueError:
                return float(val.replace(',', '.'))
        try:
            sc = parse_decimal(scale)
            tr = parse_decimal(transparency)
        except Exception:
            return await ctx.send('Ungültige Zahlenformate')
        name = input_file.filename.lower()
        if name.endswith(('.png', '.jpg')):
            out = graphic_utils.watermark_image_file(data_in, data_wm, position, sc, tr)
            out_name = 'watermark_result.png'
        elif name.endswith(('.mp4', '.mov')):
            out = graphic_utils.watermark_video_file(data_in, data_wm, position, sc, tr)
            out_name = 'watermark_result.mp4'
        else:
            return await ctx.send('Ungültiges Dateiformat.')
        buf2 = io.BytesIO(out)
        buf2.seek(0)
        await ctx.send(file=discord.File(buf2, filename=out_name))

async def setup(bot: commands.Bot):
    """
    Registriert GraphicCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(GraphicCog(bot))


