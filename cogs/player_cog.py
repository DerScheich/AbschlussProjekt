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

    # In player_cog.py
    @commands.hybrid_command(name="queue", description="Zeigt die aktuelle Queue an.")
    async def queue(self, ctx: commands.Context):
        await ctx.defer()
        try:
            queue = self.play_utils.get_queue(ctx.guild.id)
            current_song = self.play_utils.current_song.get(ctx.guild.id)

            response = []

            # Aktueller Song mit ▶️ und ohne Embed
            if current_song:
                title, link = current_song
                response.append("**Currently Playing:**")
                response.append(f"▶️ {title} ([Link](<{link}>))")  # Link in < > für kein Embed
                response.append("")  # Leerzeile

            # Nächste 10 Songs
            if queue:
                max_songs = min(len(queue), 10)
                response.append(f"**Next {max_songs} Songs:**")

                for idx in range(max_songs):
                    title, link = queue[idx]
                    response.append(f"{idx + 1}. {title} ([Link](<{link}>))")  # Keine Embeds

            # Fallback für leere Queue
            if not response:
                await ctx.send("The queue is empty!")
                return

            # Kombiniere alles und sende
            final_response = "\n".join(response)
            await ctx.send(final_response[:2000])  # Zeichenlimit erzwingen

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @commands.hybrid_command(name="skip",
                             description="Überspringt den aktuellen Song und spielt den nächsten Titel ab.")
    async def skip(self, ctx: commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            # Hole den nächsten Songtitel aus der Queue
            queue = self.play_utils.get_queue(ctx.guild.id)
            next_title = None
            if queue:
                next_title = queue[0][0] if isinstance(queue[0], tuple) else "Unbekannter Titel"
            ctx.voice_client.stop()
            if next_title:
                await ctx.send(f"Song übersprungen. **{next_title}** wird gestartet...")
            else:
                await ctx.send("Song übersprungen. Keine weiteren Songs in der Queue.")
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
