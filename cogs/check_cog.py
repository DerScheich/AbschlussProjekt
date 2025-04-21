import discord
import io
from discord.ext import commands
from utils.check_utils import check_image_async

class CheckCog(commands.Cog):
    """
    Cog für Bildprüfung-Befehle (/check).

    :param bot: Bot-Instanz.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialisiert CheckCog.

        :param bot: Bot-Instanz.
        :return: None
        """
        self.bot = bot
        self.memory = {}

    @commands.hybrid_command(name='check', description='Prüft Bild anhand Prompt')
    async def check(self, ctx: commands.Context, file: discord.Attachment, *, prompt: str):
        """
        Prüft Bild mit GPT und zeigt Ergebnis in Embed.

        :param ctx: Command-Kontext.
        :param file: Bild-Attachment.
        :param prompt: Prüf-Prompt.
        :return: None
        """
        # Format prüfen
        allowed = ('.png', '.jpg', '.jpeg', '.bmp')
        if not file.filename.lower().endswith(allowed):
            return await ctx.send('Ungültiger Dateityp.', ephemeral=False)
        await ctx.defer()
        # Datei lesen
        try:
            img_bytes = await file.read()
        except Exception as e:
            return await ctx.send(f'Fehler beim Lesen: {e}')
        # GPT-Aufruf
        try:
            result = await check_image_async(img_bytes, prompt)
        except Exception as e:
            return await ctx.send(f'Prüfungsfehler: {e}')
            # Speichern der Antwort im Gedächtnis
        self.memory[ctx.channel.id] = {
                'image': img_bytes,
                'result': result,
                'prompt': prompt
            }
        # Embed bauen
        embed = discord.Embed(title='Prüfungsergebnis', description=result, color=discord.Color.blue())
        embed.set_footer(text='Ursprüngliches Bild unten.')
        discord_file = discord.File(io.BytesIO(img_bytes), filename=file.filename)
        embed.set_image(url=f'attachment://{file.filename}')
        # senden
        await ctx.send(embed=embed, file=discord_file)

async def setup(bot: commands.Bot):
    """
    Registriert CheckCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(CheckCog(bot))
