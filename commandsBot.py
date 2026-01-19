import discord
from discord.ext import commands
from data import DISCORD_BOT_KEY_NO_BOT
from lolCalculator import lolCalculator
from playerDataHandler import init_database

intents = discord.Intents.default()
intents.message_content = True # Required to read message content for prefix commands
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    
@bot.command()
async def hello(ctx):
    await ctx.send('Hello there!')
    
@bot.command()
async def rankedWinRate(ctx, name : str, tagline : str):
    # make attempt to get summonerID
    
    # grab all games
    winrate = lolCalculator.findRankedWinRate(name, tagline)
    await ctx.send(f'Hello {name}#{tagline}! You have winrate {winrate}')
    
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist. Valid commands include:\n `/rankedWinRate <username> <tagline>`")
    else:
        # For unhandled errors, print the traceback for debugging
        print(f"Unhandled error: {error}")
        await ctx.send("An unexpected error occurred. Please try again later.")
    
init_database()
bot.run(DISCORD_BOT_KEY_NO_BOT)