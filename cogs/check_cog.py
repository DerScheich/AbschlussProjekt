import discord
from discord.ext import commands
import io
from utils.check_utils import check_image_async


class CheckCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="check", description="Prüft das angehängte Bild anhand des Prompts")
    async def check(self, ctx: commands.Context, file: discord.Attachment, *, prompt: str):
        """
        /check <Bilddatei> <prompt>

        Lese die übergebene Bilddatei und leite sie zusammen mit dem Prompt an das GPT-Modell weiter.
        Das Ergebnis wird in einem hübsch formatierten Embed zurückgegeben. Zudem wird das ursprüngliche
        Bild als Attachment erneut angezeigt, um das Feedback besser nachvollziehen zu können.
        """
        # Überprüfe, ob die hochgeladene Datei ein unterstütztes Bildformat hat.
        allowed_extensions = (".png", ".jpg", ".jpeg", ".bmp")
        if not file.filename.lower().endswith(allowed_extensions):
            return await ctx.send(
                "Ungültiger Dateityp. Bitte lade ein Bild im Format .png, .jpg, .jpeg oder .bmp hoch."
            )

        await ctx.defer()
        try:
            image_bytes = await file.read()
        except Exception as e:
            return await ctx.send(f"Fehler beim Lesen der Bilddatei: {e}")

        # Hole die GPT-Antwort; dabei wird der Bildinhalt per OCR extrahiert und geprüft.
        try:
            result = await check_image_async(image_bytes, prompt)
        except Exception as e:
            return await ctx.send(f"Fehler während der Bildprüfung: {e}")

        # Erstelle ein Embed für eine übersichtliche Darstellung
        embed = discord.Embed(
            title="Überprüfungsergebnis",
            description=result,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Das oben angezeigte Bild wurde geprüft.")

        # Erstelle ein Discord-File aus dem ursprünglichen Bild, damit es im Embed angezeigt wird
        image_file = discord.File(io.BytesIO(image_bytes), filename=file.filename)
        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(embed=embed, file=image_file)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckCog(bot))
