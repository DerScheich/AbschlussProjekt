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
        self.current_song = {}
        self.youtube_base_url = 'https://www.youtube.com/'
        self.youtube_results_url = self.youtube_base_url + 'results?'
        self.youtube_watch_url = self.youtube_base_url + 'watch?v='

        # yt-dlp Optionen inkl. Cookies aus Firefox-Browserprofil
        yt_dl_options = {
            "format": "bestaudio/best",
            "noplaylist": False,
            "cookies_from_browser": "firefox"
        }
        self.ytdl = yt_dlp.YoutubeDL(yt_dl_options)

        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re',
            'options': '-vn -filter:a "volume=0.25"'
        }

        # Spotipy-Client initialisieren
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
                # Spotify-Track abrufen
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

                # alle Playlist-Tracks laden
                loop = asyncio.get_event_loop()
                try:
                    all_tracks = []
                    offset = 0
                    while True:
                        batch = await loop.run_in_executor(
                            None,
                            lambda: self.sp_client.playlist_tracks(
                                playlist_id,
                                fields="items(track(name,artists(name))",
                                offset=offset,
                                limit=10
                            )
                        )
                        if not batch.get("items"):
                            break
                        all_tracks.extend(batch["items"])
                        offset += len(batch["items"])

                    # Titel und Künstler extrahieren
                    tracks = []
                    for item in all_tracks:
                        track = item.get("track")
                        if track:
                            title = track.get("name", "Unbekannter Titel")
                            artist = track.get("artists", [{}])[0].get("name", "")
                            tracks.append((title, artist))

                    # Playlist in Queue speichern
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
                await self.safe_send(ctx, "Bitte gültigen Spotify-Link angeben.")
            return

        # YouTube-Playlist checken
        if "list=" in link:
            link = self._ensure_playlist_link(link)
            flat_opts = {
                "format": "bestaudio/best",
                "extract_flat": True,
                "skip_download": True,
                "quiet": True,
                "cookies_from_browser": "firefox"
            }
            with yt_dlp.YoutubeDL(flat_opts) as ytdl:
                info = ytdl.extract_info(link, download=False)
            if not info or not info.get("entries"):
                await self._add_single(ctx, link)
            else:
                # Videos zur Queue hinzufügen
                count = 0
                for entry in info["entries"]:
                    if entry.get("_type") in ["url", "video"]:
                        video_id = entry.get("id")
                        title = entry.get("title", "Unbekannter Titel")
                        if not video_id or "private" in title.lower():
                            continue
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        self.queues[ctx.guild.id].append((title, video_url))
                        count += 1
                msg = (f"{count} YouTube-Videos zur Queue hinzugefügt."
                       if count else "Keine verfügbaren Videos in der Playlist.")
                await self.safe_send(ctx, msg)
        else:
            # Einzelvideo zur Queue
            await self._add_single(ctx, link)

    def _ensure_playlist_link(self, link: str) -> str:
        """
        Formatiert YouTube-Playlist-Link korrekt.

        :param link: Original-Link.
        :return: Playlist-Link.
        """
        parsed = urllib.parse.urlparse(link)
        query = urllib.parse.parse_qs(parsed.query)
        playlist_id = query.get("list", [None])[0]
        return f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else link

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
            error = str(e)
            # Private Videos überspringen
            if "Private video" in error:
                await self.safe_send(ctx, "Privates Video übersprungen.")
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
        qs = urllib.parse.urlencode({'search_query': query})
        url = self.youtube_results_url + qs
        with urllib.request.urlopen(url) as resp:
            content = resp.read().decode()
        # erstes Ergebnis verwenden
        ids = re.findall(r'/watch\?v=(.{11})', content)
        if not ids:
            await self.safe_send(ctx, f"Kein Ergebnis für '{query}'.")
            return
        link = self.youtube_watch_url + ids[0]
        await self._add_single(ctx, link)

    async def _peek_next_spotify_track(self, entry: dict, ctx) -> tuple | None:
        """
        Vorschau: Nächsten Spotify-Track ohne Index-Erhöhung anzeigen.

        :param entry: Playlist-Eintrag.
        :param ctx: Command-Kontext.
        :return: (Titel, Query) oder None
        """
        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(
                None,
                lambda: self.sp_client.playlist_tracks(
                    entry["playlist_id"], offset=entry["current_index"], limit=1
                )
            )
        except Exception as e:
            await self.safe_send(ctx, f"Fehler beim Abruf: {e}")
            return None
        items = res.get("items", [])
        if not items or not items[0].get("track"):
            return None
        t = items[0]["track"]
        title = t.get("name", "Unbekannter Titel")
        artist = t.get("artists", [{}])[0].get("name", "")
        return (title, f"{title} {artist}".strip())

    async def _get_next_spotify_track(self, entry: dict, ctx) -> tuple | None:
        """
        Holt nächsten Spotify-Track und erhöht Index.

        :param entry: Playlist-Eintrag.
        :param ctx: Command-Kontext.
        :return: (Titel, Query) oder None
        """
        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(
                None,
                lambda: self.sp_client.playlist_tracks(
                    entry["playlist_id"], offset=entry["current_index"], limit=1
                )
            )
        except Exception as e:
            await self.safe_send(ctx, f"Fehler beim Abruf: {e}")
            return None
        items = res.get("items", [])
        if not items or not items[0].get("track"):
            return None
        entry["current_index"] += 1
        t = items[0]["track"]
        title = t.get("name", "Unbekannter Titel")
        artist = t.get("artists", [{}])[0].get("name", "")
        return (title, f"{title} {artist}".strip())

    async def skip_tracks(self, ctx: commands.Context, amount: int) -> list:
        """
        Überspringt (amount-1) Songs in der Queue.

        :param ctx: Command-Kontext.
        :param amount: Anzahl zu überspringender Tracks.
        :return: Liste übersprungener Titel.
        """
        skipped = []
        extra = amount - 1
        q = self.queues.get(ctx.guild.id, [])
        # weitere Tracks entfernen
        while extra > 0 and q:
            item = q[0]
            if isinstance(item, dict) and item.get("type") == "spotify_playlist":
                res = await self._get_next_spotify_track(item, ctx)
                if res is None:
                    q.pop(0)
                    continue
                skipped.append(res[0])
            else:
                skipped.append(q.pop(0)[0] if isinstance(item, tuple) else None)
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
        # Spotify-Playlist oder YouTube-Item
        item = queue.pop(0)
        if isinstance(item, dict) and item.get("type") == "spotify_playlist":
            res = await self._get_next_spotify_track(item, ctx)
            if not res:
                await self.play_next(ctx)
                return
            title, query = res
            link = self._bridge_to_youtube(query)
            if not link:
                await self.safe_send(ctx, f"Kein YouTube-Ergebnis für '{query}'.")
                await self.play_next(ctx)
                return
            self.current_song[ctx.guild.id] = (title, link)
            await self.play(ctx, link=link)
        else:
            # direkt abspielen
            link = item[1] if isinstance(item, tuple) else item
            await self.play(ctx, link=link)

    def _bridge_to_youtube(self, query: str) -> str | None:
        """
        Sucht erstes YouTube-Ergebnis zu Query.

        :param query: Such-String.
        :return: Video-Link oder None.
        """
        try:
            qs = urllib.parse.urlencode({'search_query': query})
            with urllib.request.urlopen(self.youtube_results_url + qs) as resp:
                content = resp.read().decode()
            ids = re.findall(r'/watch\?v=(.{11})', content)
            return self.youtube_watch_url + ids[0] if ids else None
        except Exception:
            return None

    async def play(self, ctx: commands.Context, *, link: str):
        """
        Verbindet und startet Wiedergabe des Links.

        :param ctx: Command-Kontext.
        :param link: Video-Link.
        :return: None
        """
        try:
            # Verbindung zum Voice-Channel
            if ctx.guild.id not in self.voice_clients or not self.voice_clients[ctx.guild.id].is_connected():
                vc = await ctx.author.voice.channel.connect()
                self.voice_clients[ctx.guild.id] = vc
            else:
                vc = self.voice_clients[ctx.guild.id]
                await vc.move_to(ctx.author.voice.channel)
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            return

        try:
            # Stream-Info laden
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
            title = data.get("title", "Unbekannter Titel")
            self.current_song[ctx.guild.id] = (title, link)
            source = discord.FFmpegOpusAudio(data['url'], **self.ffmpeg_options)
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), ctx.bot.loop))
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")

    async def clear_queue(self, ctx: commands.Context):
        """
        Leert die Queue der aktuellen Guild.

        :param ctx: Command-Kontext.
        :return: None
        """
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await self.safe_send(ctx, "Queue geleert!")
        else:
            await self.safe_send(ctx, "Keine Queue zum Leeren.")

    async def pause(self, ctx: commands.Context):
        """
        Pausiert die Wiedergabe.

        :param ctx: Command-Kontext.
        :return: None
        """
        try:
            self.voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(f"Pause-Fehler: {e}")

    async def resume(self, ctx: commands.Context):
        """
        Setzt die Wiedergabe fort.

        :param ctx: Command-Kontext.
        :return: None
        """
        try:
            self.voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(f"Resume-Fehler: {e}")

    async def stop(self, ctx: commands.Context):
        """
        Stoppt Wiedergabe und verlässt den Channel.

        :param ctx: Command-Kontext.
        :return: None
        """
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