import discord
import os
from dotenv import load_dotenv

load_dotenv()

def ape_transform(text: str) -> str:
    new_text = ""
    use_upper = False  # Beginne mit Kleinbuchstaben
    for char in text:
        if char.isalpha():
            new_text += char.upper() if use_upper else char.lower()
            use_upper = not use_upper
        else:
            new_text += char
    return new_text

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dictionaries für Imitations- und Kombi-Modus, die auch einen TTS-Flag speichern: {username: tts_flag}
        self.mimic_users = {}    # /ape, Imitationsmodus
        self.insult_users = set()  # /insult, immer "du hurensohn"
        self.mock_users = {}  # /mock, kombinierter Modus

    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        # Eigene Nachrichten ignorieren
        if message.author == self.user:
            return

        content = message.content
        tokens = content.split()
        if tokens:
            # /ape [laut] <username>
            if tokens[0] == '/ape':
                if len(tokens) >= 3 and tokens[1].lower() == 'laut':
                    username = tokens[2]
                    self.mimic_users[username] = True
                elif len(tokens) >= 2:
                    username = tokens[1]
                    self.mimic_users[username] = False
                return

            # /noape <username>
            if tokens[0] == '/noape' and len(tokens) >= 2:
                username = tokens[1]
                self.mimic_users.pop(username, None)
                return

            # /insult <username> – immer "du hurensohn"
            if tokens[0] == '/insult' and len(tokens) >= 2:
                username = tokens[1]
                self.insult_users.add(username)
                return

            # /noinsult <username>
            if tokens[0] == '/noinsult' and len(tokens) >= 2:
                username = tokens[1]
                self.insult_users.discard(username)
                return

            # /mock [laut] <username> – kombiniert lowercase-Nachricht mit "selber ... du hurensohn"
            if tokens[0] == '/mock':
                if len(tokens) >= 3 and tokens[1].lower() == 'laut':
                    username = tokens[2]
                    self.mock_users[username] = True
                elif len(tokens) >= 2:
                    username = tokens[1]
                    self.mock_users[username] = False
                return

            # /nomock <username>
            if tokens[0] == '/nomock' and len(tokens) >= 2:
                username = tokens[1]
                self.mock_users.pop(username, None)
                return

        # Antwortlogik: Prioritäten
        # 1. Insult-Modus: Antwortet immer mit "du hurensohn"
        if message.author.name in self.insult_users:
            await message.channel.send("du hurensohn")
        # 2. Kombinierter Modus (/mock): "selber <text in lowercase> du hurensohn"
        elif message.author.name in self.mock_users:
            response = f"selber {message.content.lower()} du hurensohn"
            tts_flag = self.mock_users[message.author.name]
            await message.channel.send(response, tts=tts_flag)
        # 3. Imitationsmodus (/ape): Abwechselnd upper-/lowercase
        elif message.author.name in self.mimic_users:
            transformed = ape_transform(message.content)
            tts_flag = self.mimic_users[message.author.name]
            await message.channel.send(transformed, tts=tts_flag)

        # Testbefehl
        if content == 'ping':
            await message.channel.send('pong')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(os.getenv("BOT_TOKEN"))
