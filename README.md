# Abschlussprojekt

## Beschreibung
Unser Discord‑Bot ist ein Python‑Tool, welches es Benutzern ermöglicht, mit Slash‑Commands Audio‑Effekte wie Verlangsamung, Reverb und Stereo/Mono‑Konvertierung anzuwenden, Bilder und Videos in Graustufen oder mit Wasserzeichen zu bearbeiten sowie KI‑generierte Bilder zu erstellen und GPT‑basierte Bildprüfungen durchzuführen. Zusätzlich bietet der Bot Musiksteuerung (Play, Queue, Skip, Pause, Resume, Stop), automatische Geburtstagsverwaltung mit Geburtstagsgrüßen und GPT‑Chat‑Modi inklusive Imitations‑ und Markus‑Rühl‑Stil. 
## Installation
Dieses Projekt verwendet [poetry](https://python-poetry.org/) für das Paketmanagement.

1. Dependencies installieren:
   ```bash
   poetry install --no-root
   ```
2. Anwendung starten:
   ```bash
   poetry run python main.py
   ```
3. Neue Dependencies hinzufügen:
   ```bash
   poetry add <library>
   ```
4. Bot zum eigenen Server hinzufügen:
   [Link](https://discord.com/oauth2/authorize?client_id=1357422287451590716&permissions=8&integration_type=0&scope=applications.commands+bot)

   Oder alternativ: Dem [Test-Discord](https://discord.gg/4WHc38DAbs) beitreten
   

## Discord-Bot Befehle
Mit dem Befehl `/help` erhältst du eine Übersicht aller verfügbaren Befehle:

### ⬜ [Umbra's Sync Command](https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html)
- **/sync** `<guilds>` ["~"|"*"|"^"] – Synchronisiert die Slash-Befehle global oder für spezifische Server

### 🟦 Chat-Modus
- **/ape** `<username>` [laut] – Imitationsmodus aktivieren
- **/noape** `<username>` – Imitationsmodus deaktivieren
- **/maggus** – Markus‑Rühl‑Stil aktivieren
- **/nomaggus** – Markus‑Rühl‑Stil deaktivieren
- **@mention** `<Nachricht>` – GPT-Chat und Geburtstags‑Intents

### 🟨 Audio-Effekte
- **/slowed** `<input_audio>` [slow_factor] – Audio verlangsamen
- **/slowed_reverb** `<input_audio>` `<impulse_audio>` [slow_factor] – Reverb + Slowed
- **/reverb** `<input_audio>` `<impulse_audio>` – Nur Reverb
- **/stereo** `<input_audio>` – Mono → Stereo (Haas-Effekt)
- **/mono** `<input_audio>` – Stereo → Mono

### 🟧 Grafik
- **/watermark** `<input_file>` `<watermark_file>` [position] [scale] [transparency] – Wasserzeichen hinzufügen
- **/sw** `<input_file>` – Bild/Video in Schwarz‑Weiß konvertieren
- **/image** `<prompt>` – Generiert ein Bild mit DALL·E 3

### 🟥 Bildprüfung
- **/check** `<Bilddatei>` `<prompt>` – Bild mit GPT prüfen

### 🟩 Geburtstag
- **/setbirthday** `<username>` `<TT.MM.JJJJ>` [Name] – Geburtstag setzen
- **/viewbirthdays** – Alle Geburtstage anzeigen
- **/viewbirthday** `<username>` – Geburtstag eines Users anzeigen
- **/editbirthday** `<username>` `<TT.MM.JJJJ>` [Neuer_Name] – Geburtstag bearbeiten
- **/deletebirthday** `<username>` – Geburtstag löschen

### 🟪 Musiksteuerung
- **/play** `<Link>` – Song abspielen
- **/queue** – Warteschlange anzeigen
- **/skip** [Anzahl] – Song(s) überspringen
- **/clear_queue** – Warteschlange leeren
- **/pause** – Wiedergabe pausieren
- **/resume** – Wiedergabe fortsetzen
- **/stop** – Wiedergabe stoppen



## Ordnerstruktur

```
cogs/            # Cogs: Discord-Bot-Befehle
utils/           # Hilfsfunktionen der Befehle
main.py          # Hauptprogramm
birthdays.json   # Geburtstagsdatenbank
README.md        # Dokumentation
pyproject.toml   # Poetry-Projektkonfiguration
poetry.lock      # Sperrdatei für Poetry
.env             # Umgebungsvariablen
.gitignore       # Ausschlussliste für Git
```

## Team: Gruppe 7
- Jonas Kriehn
- Max Falk Pitulle
- Jakob Simon Haut
- Heinrich Teich
- Lea Katharina von Leesen

## Issues

- Derzeit kann keine Musik vom Server abgespielt werden, da dieser von yt-dlp als Bot erkannt und daher blockiert wird. Wir sind bemüht an einem zeitnahmen Fix.
