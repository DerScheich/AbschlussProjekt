import io
import discord
from discord.ext import commands
from typing import Literal
from utils.graphic_utils import GraphicUtils

graphic_utils = GraphicUtils()

def parse_decimal(value: str) -> float:
    """
    Versucht zuerst, mit Punkt zu parsen; bei ValueError wird Komma durch Punkt ersetzt.
    Wirft commands.BadArgument bei komplett ungültigem Format.
    """
    try:
        return float(value)
    except ValueError:
        try:
            return float(value.replace(",", "."))
        except ValueError:
            raise commands.BadArgument(f"Ungültiges Dezimalformat: {value}")

class WatermarkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="watermark",
        description="Wasserzeichen auf Bild oder Video anwenden."
    )
    async def watermark(
        self,
        ctx: commands.Context,
        input_file: discord.Attachment,
        watermark_file: discord.Attachment,
        position: Literal["top-left", "top-right", "bottom-left", "bottom-right", "center"] = "center",
        scale: str = "1.0",
        transparency: str = "1.0"
    ):
        await ctx.defer()

        # Dateien herunterladen
        try:
            input_bytes = await input_file.read()
            wm_bytes = await watermark_file.read()
        except Exception as e:
            return await ctx.send(f"Fehler beim Herunterladen der Dateien: {e}")

        # Dezimalwerte parsen
        try:
            scale_val = parse_decimal(scale)
            transparency_val = parse_decimal(transparency)
        except commands.BadArgument as e:
            return await ctx.send(f"Fehler: {e}")

        in_name = input_file.filename.lower()
        out_filename = None

        try:
            if in_name.endswith((".png", ".jpg", ".jpeg", ".bmp")):
                result_bytes = graphic_utils.watermark_image_file(
                    image_bytes=input_bytes,
                    watermark_bytes=wm_bytes,
                    position=position,
                    scale=scale_val,
                    transparency=transparency_val
                )
                out_filename = "watermark_result.png"

            elif in_name.endswith((".mp4", ".avi", ".mov", ".mkv")):
                result_bytes = graphic_utils.watermark_video_file(
                    video_bytes=input_bytes,
                    watermark_bytes=wm_bytes,
                    position=position,
                    scale=scale_val,
                    transparency=transparency_val
                )
                out_filename = "watermark_result.mp4"

            else:
                return await ctx.send("Ungültiges Dateiformat.")
        except Exception as e:
            return await ctx.send(f"Fehler bei der Wasserzeichen-Verarbeitung: {e}")

        # Ergebnis zurücksenden
        out_buffer = io.BytesIO(result_bytes)
        out_buffer.seek(0)
        await ctx.send(file=discord.File(out_buffer, filename=out_filename))


async def setup(bot):
    await bot.add_cog(WatermarkCog(bot))