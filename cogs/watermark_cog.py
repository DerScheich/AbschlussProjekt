# cogs/watermark_cog.py
import io
import discord
from discord.ext import commands
from typing import Literal
from utils.watermark_handler import WatermarkHandler

watermark_handler = WatermarkHandler()

class WatermarkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="watermark", description="Wasserzeichen auf Bild oder Video anwenden.")
    async def watermark(
            self,
            ctx: commands.Context,
            input_file: discord.Attachment,
            watermark_file: discord.Attachment,
            position: Literal["top-left", "top-right", "bottom-left", "bottom-right", "center"] = "center",
            scale: float = 1.0,
            transparency: float = 1.0
    ):
        await ctx.defer()
        try:
            input_bytes = await input_file.read()
            wm_bytes = await watermark_file.read()
        except Exception as e:
            return await ctx.send(f"Fehler beim Herunterladen der Dateien: {e}")

        in_name = input_file.filename.lower()
        out_filename = None
        try:
            if in_name.endswith((".png", ".jpg", ".jpeg", ".bmp")):
                result_bytes = watermark_handler.watermark_image_file(
                    image_bytes=input_bytes,
                    watermark_bytes=wm_bytes,
                    position=position,
                    scale=scale,
                    transparency=transparency
                )
                out_filename = "watermark_result.png"
            elif in_name.endswith((".mp4", ".avi", ".mov", ".mkv")):
                result_bytes = watermark_handler.watermark_video_file(
                    video_bytes=input_bytes,
                    watermark_bytes=wm_bytes,
                    position=position,
                    scale=scale,
                    transparency=transparency
                )
                out_filename = "watermark_result.mp4"
            else:
                return await ctx.send("Ungültiges Dateiformat.")
        except Exception as e:
            return await ctx.send(f"Fehler bei der Wasserzeichen-Verarbeitung: {e}")

        out_buffer = io.BytesIO(result_bytes)
        out_buffer.seek(0)
        await ctx.send(file=discord.File(out_buffer, filename=out_filename))

async def setup(bot):
    await bot.add_cog(WatermarkCog(bot))
