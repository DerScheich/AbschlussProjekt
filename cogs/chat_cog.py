import discord
from discord.ext import commands
from openai import OpenAI
import os
from utils.chat_utils import ChatUtils

MAX_HISTORY = 10

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mimic_users = {}
        self.mock_users = {}
        self.maggus_mode = False
        self.chat_history = {}
        self.gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chat_utils = ChatUtils(gpt_client=self.gpt_client, maggus_mode=self.maggus_mode)

    @commands.hybrid_command(name="ape", description="Aktiviert den Imitationsmodus für einen Benutzer.")
    async def ape(self, ctx, member: discord.Member, laut: bool = False):
        self.mimic_users[member.id] = laut
        await ctx.send(f"Imitationsmodus für **{member.display_name}** aktiviert (TTS: {laut}).", ephemeral=True)

    @commands.hybrid_command(name="noape", description="Deaktiviert den Imitationsmodus für einen Benutzer.")
    async def noape(self, ctx, member: discord.Member):
        if member.id in self.mimic_users:
            self.mimic_users.pop(member.id)
            await ctx.send(f"Imitationsmodus für **{member.display_name}** wurde deaktiviert.", ephemeral=True)
        else:
            await ctx.send(f"**{member.display_name}** war nicht im Imitationsmodus.", ephemeral=True)

    @commands.hybrid_command(name="mock", description="Aktiviert den kombinierten Modus.")
    async def mock(self, ctx, member: discord.Member, laut: bool = False):
        self.mock_users[member.id] = laut
        await ctx.send(f"Kombinierter Modus für **{member.display_name}** aktiviert (TTS: {laut}).", ephemeral=True)

    @commands.hybrid_command(name="nomock", description="Deaktiviert den kombinierten Modus für einen Benutzer.")
    async def nomock(self, ctx, member: discord.Member):
        if member.id in self.mock_users:
            self.mock_users.pop(member.id)
            await ctx.send(f"Kombinierter Modus für **{member.display_name}** wurde deaktiviert.", ephemeral=True)
        else:
            await ctx.send(f"**{member.display_name}** war nicht im kombinierten Modus.", ephemeral=True)

    @commands.hybrid_command(name="maggus", description="Aktiviert den Markus-Rühl-Stil für Antworten.")
    async def maggus(self, ctx):
        self.maggus_mode = True
        self.chat_utils.maggus_mode = True  # Aktualisiere den Zustand in ChatUtils
        await ctx.send("Markus-Rühl-Stil aktiviert.", ephemeral=True)

    @commands.hybrid_command(name="nomaggus", description="Deaktiviert den Markus-Rühl-Stil für Antworten.")
    async def nomaggus(self, ctx):
        self.maggus_mode = False
        self.chat_utils.maggus_mode = False
        await ctx.send("Markus-Rühl-Stil deaktiviert.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.id in self.mimic_users:
            # Nutzt die ape_transform-Funktion aus ChatUtils
            transformed = self.chat_utils.ape_transform(message.content)
            tts_flag = self.mimic_users[message.author.id]
            await message.channel.send(transformed, tts=tts_flag)
        elif message.author.id in self.mock_users:
            response = f"selber {message.content.lower()} du hurensohn"
            tts_flag = self.mock_users[message.author.id]
            await message.channel.send(response, tts=tts_flag)
        else:
            if self.bot.user in message.mentions:
                channel_id = message.channel.id
                if channel_id not in self.chat_history:
                    self.chat_history[channel_id] = []
                self.chat_history[channel_id].append({"role": "user", "content": message.content})
                if len(self.chat_history[channel_id]) > MAX_HISTORY:
                    self.chat_history[channel_id] = self.chat_history[channel_id][-MAX_HISTORY:]
                conversation_prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in self.chat_history[channel_id])
                answer = self.chat_utils.gpt_response(conversation_prompt)
                await message.channel.send(answer)
                self.chat_history[channel_id].append({"role": "assistant", "content": answer})

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
