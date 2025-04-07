import discord
import asyncio
import yt_dlp
import urllib.parse, urllib.request, re
from discord.ext import commands

class PlayUtils:
    def __init__(self):
        # Verwaltung von Queues und Voice-Clients pro Guild
        self.queues = {}
        self.voice_clients = {}
        self.youtube_base_url = 'https://www.youtube.com/'
        self.youtube_results_url = self.youtube_base_url + 'results?'
        self.youtube_watch_url = self.youtube_base_url + 'watch?v='
        # Standardoptionen für yt-dlp bei vollständiger Extraktion
        yt_dl_options = {"format": "bestaudio/best", "noplaylist": False}
        self.ytdl = yt_dlp.YoutubeDL(yt_dl_options)
        # FFmpeg-Optionen mit -re für Echtzeit-Streaming
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re',
            'options': '-vn -filter:a "volume=0.25"'
        }

    def get_queue(self, guild_id: int):
        return self.queues.get(guild_id, [])

    async def add_to_queue(self, ctx: commands.Context, link: str):
        """Fügt einen Song oder eine Playlist zur Queue hinzu.
           Bei Playlist-Links wird mittels flacher Extraktion (extract_flat)
           eine Liste von (Titel, Video-URL) erstellt.
        """
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        # Prüfe, ob es sich um eine Playlist handelt (Playlist-Links enthalten meist "list=")
        if "list=" in link:
            flat_opts = {
                "format": "bestaudio/best",
                "extract_flat": True,
                "skip_download": True,
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(flat_opts) as ytdl:
                info = ytdl.extract_info(link, download=False)
            entries = info.get("entries", [])
            if not entries:
                await ctx.send("Keine Videos in der Playlist gefunden. Versuche, als einzelnes Video zu behandeln.")
                # Füge den Link als einzelnes Video hinzu
                await self.add_to_queue(ctx, link)
                return
            count = 0
            for entry in entries:
                video_id = entry.get("id")
                if video_id:
                    video_url = self.youtube_watch_url + video_id
                    # Hole den Titel, falls vorhanden; andernfalls Default
                    title = entry.get("title", "Unbekannter Titel")
                    self.queues[ctx.guild.id].append((title, video_url))
                    count += 1
            await ctx.send(f"{count} Videos zur Queue hinzugefügt.")
        else:
            # Für ein einzelnes Video: führe eine Extraktion durch, um den Titel zu erhalten
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
            except Exception as e:
                await ctx.send(f"Fehler beim Laden des Songs: {e}")
                return
            title = data.get("title", "Unbekannter Titel")
            # Speichere als Tupel (Titel, Link)
            self.queues[ctx.guild.id].append((title, link))
            await ctx.send("Song zur Queue hinzugefügt!")

    async def play_next(self, ctx: commands.Context):
        """Spielt den nächsten Song in der Queue ab, falls vorhanden."""
        if self.queues.get(ctx.guild.id, []):
            next_item = self.queues[ctx.guild.id].pop(0)
            # next_item ist ein Tupel (Titel, URL)
            link = next_item[1] if isinstance(next_item, tuple) else next_item
            await self.play(ctx, link=link)

    async def play(self, ctx: commands.Context, *, link: str):
        """Verbindet sich mit dem Sprachkanal und spielt den angegebenen Song ab.
           Für den aktuell abzuspielenden Song wird die vollständige Extraktion durchgeführt.
        """
        try:
            # Sprachverbindung aufbauen oder verschieben
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
            # Falls kein direkter YouTube-Link angegeben wurde, als Suchbegriff behandeln
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

            # Vollständige Extraktion für den aktuellen Song (alle Metadaten)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
            song_url = data['url']
            player = discord.FFmpegOpusAudio(song_url, **self.ffmpeg_options)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), ctx.bot.loop))
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")

    async def clear_queue(self, ctx: commands.Context):
        """Leert die Queue der aktuellen Guild."""
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    async def pause(self, ctx: commands.Context):
        """Pausiert die Wiedergabe."""
        try:
            self.voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(f"Pause-Fehler: {e}")

    async def resume(self, ctx: commands.Context):
        """Setzt die Wiedergabe fort."""
        try:
            self.voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(f"Resume-Fehler: {e}")

    async def stop(self, ctx: commands.Context):
        """Stoppt die Wiedergabe und trennt die Sprachverbindung."""
        try:
            vc = self.voice_clients[ctx.guild.id]
            vc.stop()
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
        except Exception as e:
            print(f"Stop-Fehler: {e}")
