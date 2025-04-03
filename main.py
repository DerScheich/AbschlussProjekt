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
        # Mengen für die verschiedenen Modi
        self.mimic_users = set()
        self.mock_users = set()
        self.mockape_users = set()

    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        # Eigene Nachrichten ignorieren
        if message.author == self.user:
            return

        # Aktivierung/Deaktivierung Mimic-Modus
        if message.content.startswith('/ape '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mimic_users.add(target_username)
            return

        if message.content.startswith('/noape '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mimic_users.discard(target_username)
            return

        # Aktivierung/Deaktivierung Mock-Modus
        if message.content.startswith('/mock '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mock_users.add(target_username)
            return

        if message.content.startswith('/nomock '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mock_users.discard(target_username)
            return

        # Aktivierung/Deaktivierung Mockape-Modus
        if message.content.startswith('/mockape '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mockape_users.add(target_username)
            return

        if message.content.startswith('/nomockape '):
            parts = message.content.split(maxsplit=1)
            if len(parts) >= 2:
                target_username = parts[1].strip()
                self.mockape_users.discard(target_username)
            return

        # Antwortlogik:
        # 1. Mock-Modus: "du hurensohn"
        if message.author.name in self.mock_users:
            await message.channel.send("du hurensohn")
        # 2. Mockape-Modus: "selber <text in lowercase> du hurensohn"
        elif message.author.name in self.mockape_users:
            response = f"selber {message.content.lower()} du hurensohn"
            await message.channel.send(response)
        # 3. Mimic-Modus: abwechselnd upper-/lowercase
        elif message.author.name in self.mimic_users:
            transformed_text = ape_transform(message.content)
            await message.channel.send(transformed_text)

        # Testbefehl
        if message.content == 'ping':
            await message.channel.send('pong')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(os.getenv("BOT_TOKEN"))
