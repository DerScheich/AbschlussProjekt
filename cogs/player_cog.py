from discord.ext import commands
from utils.player_utils import PlayUtils

class PlayerCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.play_utils = PlayUtils()

    @commands.hybrid_command(name="play", description="Spielt einen Song ab und fügt ihn der Queue hinzu.")
    async def play(self, ctx: commands.Context, *, link: str):
        if not ctx.author.voice:
            return await ctx.send("Du musst in einem Sprachkanal sein!", ephemeral=True)
        # Song oder Playlist wird der Queue hinzugefügt
        await self.play_utils.add_to_queue(ctx, link)
        # Falls aktuell nichts abgespielt wird, starte den nächsten Song
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await self.play_utils.play_next(ctx)

    @commands.hybrid_command(name="queue", description="Zeigt die aktuelle Queue an.")
    async def queue(self, ctx: commands.Context):
        # Signalisieren, dass die Antwort etwas Zeit benötigt
        await ctx.defer()
        queue = self.play_utils.get_queue(ctx.guild.id)
        if not queue:
            await ctx.send("Die Queue ist leer!")
        else:
            # Erstelle pro Zeile: Titel (Link) – klickbar via Markdown
            queue_list = "\n".join(
                f"{idx + 1}. {title} ([Link]({link}))" for idx, (title, link) in enumerate(queue)
            )
            await ctx.send(f"**Aktuelle Queue:**\n{queue_list}")

    @commands.hybrid_command(name="skip", description="Überspringt den aktuellen Song und spielt den nächsten Titel ab.")
    async def skip(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()  # Löst den after-Callback aus, der play_next() aufruft
            await ctx.send("Song übersprungen. Nächster Titel wird gestartet...")
        else:
            await ctx.send("Momentan wird nichts abgespielt.", ephemeral=True)

    @commands.hybrid_command(name="clear_queue", description="Leert die aktuelle Warteschlange.")
    async def clear_queue(self, ctx: commands.Context):
        await self.play_utils.clear_queue(ctx)

    @commands.hybrid_command(name="pause", description="Pausiert die Wiedergabe.")
    async def pause(self, ctx: commands.Context):
        await self.play_utils.pause(ctx)
        await ctx.send("Pausiert.")

    @commands.hybrid_command(name="resume", description="Setzt die Wiedergabe fort.")
    async def resume(self, ctx: commands.Context):
        await self.play_utils.resume(ctx)
        await ctx.send("Wiedergabe fortgesetzt.")

    @commands.hybrid_command(name="stop", description="Stoppt die Wiedergabe und verlässt den Sprachkanal.")
    async def stop(self, ctx: commands.Context):
        await self.play_utils.stop(ctx)
        await ctx.send("Wiedergabe gestoppt und Kanal verlassen.")

async def setup(client: commands.Bot):
    await client.add_cog(PlayerCog(client))
