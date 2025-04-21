import os
import discord
import asyncio
import yt_dlp
import urllib.parse, urllib.request, re
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

class PlayUtils:
    """
    Utility-Klasse für Musikbefehle (Queue, Play, Skip, Spotify & YouTube).
    """
    def __init__(self):
        """
        Initialisiert PlayUtils mit leeren Queues und Clients.

        :return: None
        """
        self.queues = {}
        self.voice_clients = {}
        self.current_song = {}  # Speichert den aktuell spielenden Song pro Guild
        self.youtube_base_url = 'https://www.youtube.com/'
        self.youtube_results_url = self.youtube_base_url + 'results?'
        self.youtube_watch_url = self.youtube_base_url + 'watch?v='

        yt_dl_options = {"format": "bestaudio/best", "noplaylist": False}
        self.ytdl = yt_dlp.YoutubeDL(yt_dl_options)

        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re',
            'options': '-vn -filter:a "volume=0.25"'
        }

        # Spotipy-Client für Spotify
        self.sp_client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
        ))

    async def safe_send(self, ctx, content: str):
        """
        Sendet Antwort unabhängig vom Command-Typ.

        :param ctx: Command-Kontext
        :param content: Nachrichtentext
        :return: None
        """
        try:
            if hasattr(ctx, 'interaction') and ctx.interaction:
                if not ctx.interaction.response.is_done():
                    await ctx.interaction.response.send_message(content)
                else:
                    await ctx.followup.send(content)
            else:
                await ctx.send(content)
        except Exception:
            await ctx.send(content)

    def get_queue(self, guild_id: int):
        """
        Gibt die Queue für eine Guild zurück.

        :param guild_id: ID der Guild als Integer.
        :return: Liste der Queue-Einträge.
        """
        return self.queues.get(guild_id, [])
    async def add_to_queue(self, ctx: commands.Context, link: str):
        """
        Fügt einen Song (YouTube) oder Spotify-Track/Playlist der Queue hinzu.

        :param ctx: Command-Kontext.
        :param link: YouTube- oder Spotify-Link.
        :return: None
        """
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        # Spotify-Link checken
        if "open.spotify.com" in link.lower():
            if "/track/" in link.lower():
                # Einzelner Track
                loop = asyncio.get_event_loop()
                try:
                    track_data = await loop.run_in_executor(None, lambda: self.sp_client.track(link))
                except Exception as e:
                    await self.safe_send(ctx, f"Fehler beim Abrufen des Spotify-Tracks: {e}")
                    return
                track_title = track_data.get("name", "Unbekannter Titel")
                artists = track_data.get("artists", [])
                artist = artists[0].get("name", "") if artists else ""
                query = f"{track_title} {artist}".strip()
                await self._add_spotify_single(ctx, query)

            elif "/playlist/" in link.lower():
                parsed = urllib.parse.urlparse(link)
                path_parts = parsed.path.split('/')
                playlist_id = path_parts[2] if len(path_parts) >= 3 else None
                if not playlist_id:
                    await self.safe_send(ctx, "Ungültiger Spotify-Playlist-Link.")
                    return

                loop = asyncio.get_event_loop()
                try:
                    # alle Playlist-Tracks laden
                    all_tracks = []
                    offset = 0
                    while True:
                        batch = await loop.run_in_executor(
                            None,
                            lambda: self.sp_client.playlist_tracks(
                                playlist_id,
                                fields="items(track(name,artists(name))",
                                offset=offset,
                                limit=10  # Maximal 100 Tracks pro Anfrage
                            )
                        )
                        if not batch.get("items"):
                            break
                        all_tracks.extend(batch["items"])
                        offset += len(batch["items"])

                    # Extrahiere Titel und Künstler
                    tracks = []
                    for item in all_tracks:
                        track = item.get("track")
                        if track:
                            title = track.get("name", "Unbekannter Titel")
                            artist = track.get("artists", [{}])[0].get("name", "")
                            tracks.append((title, artist))

                    # Speichere die Tracks mit YouTube-Links
                    entry = {
                        "type": "spotify_playlist",
                        "playlist_id": playlist_id,
                        "playlist_name": "Unbekannte Playlist",
                        "tracks": tracks,
                        "current_index": 0
                    }
                    self.queues[ctx.guild.id].append(entry)
                    await self.safe_send(
                        ctx,
                        f"Spotify-Playlist mit {len(tracks)} Songs zur Queue hinzugefügt."
                    )
                except Exception as e:
                    await self.safe_send(ctx, f"Fehler: {e}")
            else:
                await self.safe_send(ctx, "Bitte einen gültigen Spotify-Track- oder -Playlist-Link angeben.")
            return

        # YouTube-Playlist checken
        if "list=" in link:
            link = self._ensure_playlist_link(link)
            flat_opts = {
                "format": "bestaudio/best",
                "extract_flat": True,
                "skip_download": True,
                "quiet": True
            }
            with yt_dlp.YoutubeDL(flat_opts) as ytdl:
                info = ytdl.extract_info(link, download=False)
            if not info or "entries" not in info or not info["entries"]:
                await self._add_single(ctx, link)
            else:

                count = 0
                for entry in info["entries"]:
                    if entry.get("_type") in ["url", "video"]:
                        video_id = entry.get("id")
                        title = entry.get("title", "Unbekannter Titel")
                        if not video_id:
                            continue
                        if "private" in title.lower():
                            continue
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        self.queues[ctx.guild.id].append((title, video_url))
                        count += 1
                if count == 0:
                    await self.safe_send(ctx, "Keine verfügbaren Videos in der Playlist (alle privat?).")
                else:
                    await self.safe_send(ctx, f"{count} YouTube-Videos zur Queue hinzugefügt.")
        else:
            # Einzelvideo zur Queue
            await self._add_single(ctx, link)

    def _ensure_playlist_link(self, link: str) -> str:
        """
        Formatiert YouTube-Playlist-Link korrekt.

        :param link: Original-Link.
        :return: Playlist-Link.
        """
        import urllib.parse




        parsed = urllib.parse.urlparse(link)
        query = urllib.parse.parse_qs(parsed.query)
        playlist_id = query.get("list", [None])[0]
        if playlist_id:
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        return link

    async def _add_single(self, ctx: commands.Context, link: str):
        """
        Fügt ein einzelnes YouTube-Video zur Queue hinzu.

        :param ctx: Command-Kontext.
        :param link: Video-Link.
        :return: None
        """
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
        except Exception as e:
            error_text = str(e)
            if "Private video" in error_text:
                await self.safe_send(ctx, "Das Video ist privat und wurde übersprungen.")

            else:
                await self.safe_send(ctx, f"Fehler beim Laden des Songs: {e}")
            return
        title = data.get("title", "Unbekannter Titel")
        self.queues[ctx.guild.id].append((title, link))
        await self.safe_send(ctx, f"Song '{title}' zur Queue hinzugefügt!")

    async def _add_spotify_single(self, ctx: commands.Context, query: str):
        """
        Sucht YouTube-Video zu Spotify-Track und fügt es ein.

        :param ctx: Command-Kontext.
        :param query: Such-Query.
        :return: None
        """
        import urllib.parse, urllib.request, re
        query_string = urllib.parse.urlencode({'search_query': query})
        url = self.youtube_results_url + query_string
        with urllib.request.urlopen(url) as response:
            content = response.read().decode()
        search_results = re.findall(r'/watch\?v=(.{11})', content)
        if not search_results:
            await self.safe_send(ctx, f"Kein passendes YouTube-Ergebnis für '{query}' gefunden.")
            return
        youtube_link = self.youtube_watch_url + search_results[0]
        await self._add_single(ctx, youtube_link)

    async def _peek_next_spotify_track(self, entry: dict, ctx) -> tuple | None:
        """
        Vorschau: Nächsten Spotify-Track ohne Index-Erhöhung anzeigen.

        :param entry: Playlist-Eintrag.
        :param ctx: Command-Kontext.
        :return: (Titel, Query) oder None
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.sp_client.playlist_tracks(entry["playlist_id"], offset=entry["current_index"], limit=1)


            )
        except Exception as e:
            await self.safe_send(ctx, f"Fehler beim Abrufen des Spotify-Tracks: {e}")
            return None
        items = result.get("items", [])
        if not items:
            return None
        track = items[0].get("track")
        if not track:
            return None
        track_title = track.get("name", "Unbekannter Titel")
        artists = track.get("artists", [])
        artist = artists[0].get("name", "") if artists else ""
        return (track_title, f"{track_title} {artist}".strip())

    async def _get_next_spotify_track(self, entry: dict, ctx) -> tuple | None:
        """
        Holt nächsten Spotify-Track und erhöht Index.

        :param entry: Playlist-Eintrag.
        :param ctx: Command-Kontext.
        :return: (Titel, Query) oder None
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.sp_client.playlist_tracks(entry["playlist_id"], offset=entry["current_index"], limit=1)
            )
        except Exception as e:
            await self.safe_send(ctx, f"Fehler beim Abrufen des Spotify-Tracks: {e}")
            return None
        items = result.get("items", [])
        if not items:
            return None
        track = items[0].get("track")
        if not track:
            return None
        track_title = track.get("name", "Unbekannter Titel")
        artists = track.get("artists", [])
        artist = artists[0].get("name", "") if artists else ""
        entry["current_index"] += 1
        return (track_title, f"{track_title} {artist}".strip())

    async def skip_tracks(self, ctx: commands.Context, amount: int) -> list:
        """
        Überspringt (amount-1) Songs in der Queue.

        :param ctx: Command-Kontext.
        :param amount: Anzahl zu überspringender Tracks.
        :return: Liste übersprungener Titel.
        """
        skipped = []
        extra = amount - 1  # Der erste Skip kommt über voice_client.stop()
        q = self.queues.get(ctx.guild.id, [])

        while extra > 0 and q:
            item = q[0]
            if isinstance(item, dict) and item.get("type") == "spotify_playlist":
                res = await self._get_next_spotify_track(item, ctx)
                if res is None:
                    q.pop(0)
                    continue
                title, _ = res
                skipped.append(title)
                extra -= 1
            elif isinstance(item, tuple):
                title, _ = q.pop(0)
                skipped.append(title)
                extra -= 1
            else:
                q.pop(0)
                extra -= 1
        return skipped

    async def play_next(self, ctx: commands.Context):
        """
        Spielt den nächsten Song in der Queue.

        :param ctx: Command-Kontext.
        :return: None
        """
        # aktuelles Lied entfernen
        self.current_song.pop(ctx.guild.id, None)
        queue = self.queues.get(ctx.guild.id, [])
        if not queue:
            return
        # Bestimme den nächsten Song
        if isinstance(queue[0], dict) and queue[0].get("type") == "spotify_playlist":
            # Spotify-Playlist: Ermittele den nächsten Track on demand
            item = queue[0]
            res = await self._get_next_spotify_track(item, ctx)
            if res is None:
                # Playlist zu Ende
                queue.pop(0)
                await self.play_next(ctx)
                return
            title, query = res
            link = self._bridge_to_youtube(query)
            if link is None:
                await self.safe_send(ctx, f"Kein passendes YouTube-Ergebnis zu '{query}' gefunden.")
                await self.play_next(ctx)
                return
            self.current_song[ctx.guild.id] = (title, link)
            await self.play(ctx, link=link)
        else:
            # Normales YouTube-Item
            item = queue.pop(0)
            if isinstance(item, tuple):
                _, link = item
            else:
                link = item
            await self.play(ctx, link=link)

    def _bridge_to_youtube(self, query: str) -> str | None:
        """Sucht zu 'query' das erste YouTube-Ergebnis und gibt die watch-URL zurück."""





        try:
            q = urllib.parse.urlencode({'search_query': query})
            url = self.youtube_results_url + q
            with urllib.request.urlopen(url) as response:
                content = response.read().decode()
            search_results = re.findall(r'/watch\?v=(.{11})', content)
            if not search_results:
                return None
            return self.youtube_watch_url + search_results[0]
        except Exception:
            return None

    async def play(self, ctx: commands.Context, *, link: str):
        """Startet das Abspielen eines Links (YouTube)."""






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

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
            title = data.get("title", "Unbekannter Titel")
            self.current_song[ctx.guild.id] = (title, link)
            source = discord.FFmpegOpusAudio(data['url'], **self.ffmpeg_options)
            voice_client.play(source, after=lambda e:
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), ctx.bot.loop))
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")

    async def clear_queue(self, ctx: commands.Context):






        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await self.safe_send(ctx, "Queue cleared!")
        else:
            await self.safe_send(ctx, "There is no queue to clear")

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