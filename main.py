import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from typing import Literal, Optional

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

initial_extensions = [
    "cogs.audio_cog",
    "cogs.chat_cog",
    "cogs.graphic_cog",
    "cogs.play_cog",
    "cogs.check_cog",
    "cogs.birthday_cog"
]

async def load_extensions():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)  # Asynchrones Laden der Cogs
            print(f"✅ Cog {ext} geladen.")
        except Exception as e:
            print(f"❌ Fehler beim Laden von {ext}: {str(e)}")

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    """Umbra's Sync - https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html"""
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

@bot.event
async def on_ready():
    await bot.tree.sync()  # Synchronisiere Slash-Commands
    print(f"🟢 Bot ist online als {bot.user}!")

async def main():
    await load_extensions()
    await bot.start(os.getenv("BOT_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())