import logging

import discord
from discord.ext import commands

from config import DISCORD_BOT_TOKEN
from lolCalculator import lolCalculator

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for prefix commands
bot = commands.Bot(command_prefix="/", intents=intents)
# Child of the "discord" logger, so it shares the console handler bot.run() sets up
LOG = logging.getLogger("discord.commandsBot")


@bot.event
async def on_ready():
    LOG.info("Bot is ready. Logged in as %s", bot.user)


@bot.command()
async def hello(ctx):
    await ctx.send("Hello there!")


@bot.command()
async def rankedWinRate(ctx, name: str, tagline: str):
    # make attempt to get summonerID

    # grab all games
    winrate = lolCalculator.findRankedWinRate(name, tagline)
    await ctx.send(f"Hello {name}#{tagline}! You have winrate {winrate}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist. Valid commands include:\n `/rankedWinRate <username> <tagline>`")
    else:
        # For unhandled errors, log the traceback for debugging
        LOG.error("Unhandled error: %s", error, exc_info=error)
        await ctx.send("An unexpected error occurred. Please try again later.")


bot.run(DISCORD_BOT_TOKEN)
