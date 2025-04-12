from discord.ext import commands
from utils.play_utils import PlayUtils

class PlayerCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.play_utils = PlayUtils()

    @commands.hybrid_command(name="play", description="Spielt einen Song ab und fügt ihn der Queue hinzu.")
    async def play(self, ctx: commands.Context, *, link: str):
        if not ctx.author.voice:
            return await ctx.send("Du musst in einem Sprachkanal sein!", ephemeral=True)
        await ctx.defer()
        await self.play_utils.add_to_queue(ctx, link)
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await self.play_utils.play_next(ctx)

    @commands.hybrid_command(name="queue", description="Zeigt die aktuelle Queue an.")
    async def queue(self, ctx: commands.Context):
        await ctx.defer()
        try:
            queue = self.play_utils.get_queue(ctx.guild.id)
            current = self.play_utils.current_song.get(ctx.guild.id)
            response = []

            # Currently Playing
            if current:
                ctitle, clink = current
                response.append("**Currently Playing:**")
                response.append(f"▶️ {ctitle} ([Link](<{clink}>))")
                response.append("")

            # Next Songs (bis zu 10 Einträge)
            if queue:
                response.append("**Next Songs:**")
                for idx, item in enumerate(queue[:10]):
                    if isinstance(item, dict) and item.get("type") == "spotify_playlist":
                        # Hole den nächsten Track aus der Spotify-Playlist als Vorschau
                        res = await self.play_utils._peek_next_spotify_track(item, ctx)
                        if res:
                            title, query = res
                            yt_link = self.play_utils._bridge_to_youtube(query)
                            response.append(f"{idx+1}. {title} ([Link](<{yt_link}>))")
                        else:
                            response.append(f"{idx+1}. Kein weiterer Track in der Playlist")
                    elif isinstance(item, tuple):
                        title, link = item
                        response.append(f"{idx+1}. {title} ([Link](<{link}>))")
                    else:
                        response.append(f"{idx+1}. Unbekannter Eintrag")
            if not response:
                await ctx.send("The queue is empty!")
                return

            final = "\n".join(response)
            await ctx.send(final[:2000])
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @commands.hybrid_command(name="skip", description="Überspringt den aktuellen Song (Standard), oder mehrere Tracks.")
    async def skip(self, ctx: commands.Context, amount: int = 1):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("Momentan wird nichts abgespielt.", ephemeral=True)

        if amount <= 1:
            # Normaler Skip
            queue = self.play_utils.get_queue(ctx.guild.id)
            next_title = None
            if queue:
                item = queue[0]
                if isinstance(item, dict) and item.get("type") == "spotify_playlist":
                    peeked = await self.play_utils._peek_next_spotify_track(item, ctx)
                    if peeked:
                        next_title, _ = peeked
                elif isinstance(item, tuple):
                    next_title = item[0]

            ctx.voice_client.stop()

            if next_title:
                await ctx.send(f"Song übersprungen. **{next_title}** wird gestartet...")
            else:
                await ctx.send("Song übersprungen. Keine weiteren Songs in der Queue.")
        else:
            # Überspringt mehrere Songs
            skipped = await self.play_utils.skip_tracks(ctx, amount)
            ctx.voice_client.stop()

            queue = self.play_utils.get_queue(ctx.guild.id)
            next_title = None
            if queue:
                item = queue[0]
                if isinstance(item, dict) and item.get("type") == "spotify_playlist":
                    peeked = await self.play_utils._peek_next_spotify_track(item, ctx)
                    if peeked:
                        next_title, _ = peeked
                elif isinstance(item, tuple):
                    next_title = item[0]

            if next_title:
                await ctx.send(f"{amount} Songs übersprungen. **{next_title}** wird gestartet...")
            else:
                await ctx.send(f"{amount} Songs übersprungen. Keine weiteren Songs in der Queue.")

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
