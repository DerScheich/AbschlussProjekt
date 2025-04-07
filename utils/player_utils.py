import discord
import asyncio
import yt_dlp
import urllib.parse, urllib.request, re
from discord.ext import commands

class PlayUtils:
    def __init__(self):
        self.queues = {}
        self.voice_clients = {}
        self.current_song = {}  # Speichert den aktuellen Song pro Guild
        self.youtube_base_url = 'https://www.youtube.com/'
        self.youtube_results_url = self.youtube_base_url + 'results?'
        self.youtube_watch_url = self.youtube_base_url + 'watch?v='

        yt_dl_options = {"format": "bestaudio/best", "noplaylist": False}
        self.ytdl = yt_dlp.YoutubeDL(yt_dl_options)

        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re',
            'options': '-vn -filter:a "volume=0.25"'
        }

    def get_queue(self, guild_id: int):
        return self.queues.get(guild_id, [])

    async def add_to_queue(self, ctx, link: str):
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        # Falls "list=" im Link steht, behandeln wir das als Playlist
        if "list=" in link:
            # 1) Link anpassen, um watch?v=... zu entfernen, damit wir eine reine Playlist-URL erhalten
            link = self._ensure_playlist_link(link)

            # 2) Mit extract_flat alle Einträge holen
            flat_opts = {
                "format": "bestaudio/best",
                "extract_flat": True,
                "skip_download": True,
                "quiet": True
            }
            with yt_dlp.YoutubeDL(flat_opts) as ytdl:
                info = ytdl.extract_info(link, download=False)

            # 3) Prüfen, ob es tatsächlich eine Playlist ist und Einträge vorhanden sind
            if not info or "entries" not in info or not info["entries"]:
                # Dann als einzelnes Video behandeln
                await self._add_single(ctx, link)
            else:
                count = 0
                for entry in info["entries"]:
                    if entry.get("_type") in ["url", "video"]:
                        video_id = entry.get("id")
                        title = entry.get("title", "Unbekannter Titel")
                        if not video_id:
                            continue
                        # Überspringe private Videos
                        if "private" in title.lower():
                            continue
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        self.queues[ctx.guild.id].append((title, video_url))
                        count += 1
                if count == 0:
                    await ctx.send("Keine verfügbare Videos in der Playlist gefunden (alle Videos sind privat).")
                else:
                    await ctx.send(f"{count} Videos zur Queue hinzugefügt.")
        else:
            # Einzelnes Video
            await self._add_single(ctx, link)

    def _ensure_playlist_link(self, link: str) -> str:
        """
        Entfernt das 'watch?v=...' und formt die URL zu einer reinen Playlist-URL um.
        Aus 'youtube.com/watch?v=ABC&list=XYZ' wird 'youtube.com/playlist?list=XYZ'
        """
        import urllib.parse

        parsed = urllib.parse.urlparse(link)
        query = urllib.parse.parse_qs(parsed.query)
        playlist_id = query.get("list", [None])[0]
        if playlist_id:
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        return link

    async def _add_single(self, ctx, link: str):
        """Führt eine vollständige Extraktion für einen einzelnen Link durch und hängt (Titel, Link) an.
           Bei privaten Videos wird ein Fehler aufgefangen und das Video nicht der Queue hinzugefügt.
        """
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
        except Exception as e:
            error_text = str(e)
            if "Private video" in error_text:
                await ctx.send("Das Video ist privat und wurde übersprungen.")
            else:
                await ctx.send(f"Fehler beim Laden des Songs: {e}")
            return
        title = data.get("title", "Unbekannter Titel")
        self.queues[ctx.guild.id].append((title, link))
        await ctx.send("Song zur Queue hinzugefügt!")

    async def play_next(self, ctx: commands.Context):
        if self.queues.get(ctx.guild.id, []):
            # Alten aktuellen Song entfernen
            self.current_song.pop(ctx.guild.id, None)
            next_item = self.queues[ctx.guild.id].pop(0)
            link = next_item[1] if isinstance(next_item, tuple) else next_item
            await self.play(ctx, link=link)

    async def play(self, ctx: commands.Context, *, link: str):
        try:
            if ctx.guild.id not in self.voice_clients or not self.voice_clients[ctx.guild.id].is_connected():
                voice_client = await ctx.author.voice.channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
            else:
                voice_client = self.voice_clients[ctx.guild.id]
                await voice_client.move_to(ctx.author.voice.channel)
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            return

        try:
            if self.youtube_base_url not in link:
                query_string = urllib.parse.urlencode({'search_query': link})
                url = self.youtube_results_url + query_string
                with urllib.request.urlopen(url) as response:
                    content = response.read().decode()
                search_results = re.findall(r'/watch\?v=(.{11})', content)
                if not search_results:
                    await ctx.send("Kein passendes Ergebnis gefunden.")
                    return
                link = self.youtube_watch_url + search_results[0]

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))

            # Aktuellen Song speichern
            self.current_song[ctx.guild.id] = (
                data.get("title", "Unbekannter Titel"),
                link
            )

            song_url = data['url']
            player = discord.FFmpegOpusAudio(song_url, **self.ffmpeg_options)
            voice_client.play(player,
                              after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), ctx.bot.loop))
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")

    async def clear_queue(self, ctx: commands.Context):
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    async def pause(self, ctx: commands.Context):
        try:
            self.voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(f"Pause-Fehler: {e}")

    async def resume(self, ctx: commands.Context):
        try:
            self.voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(f"Resume-Fehler: {e}")

    async def stop(self, ctx: commands.Context):
        """Stoppt die Wiedergabe, trennt die Sprachverbindung und leert die Queue."""
        try:
            vc = self.voice_clients[ctx.guild.id]
            vc.stop()
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            self.current_song.pop(ctx.guild.id, None)
            if ctx.guild.id in self.queues:
                self.queues[ctx.guild.id].clear()
        except Exception as e:
            print(f"Stop-Fehler: {e}")
