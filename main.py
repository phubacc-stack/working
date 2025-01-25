import discord
import re
import os
import asyncio
import random
from discord.ext import commands, tasks

version = 'v2.7'

# Load environment variables
user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

# Load Pokémon and mythical lists
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

# Initialize counters
num_pokemon = 0
shiny = 0
legendary = 0
mythical = 0

poketwo = 716390085896962058

# Set up intents for the bot
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)
intervals = [2.2, 2.4, 2.6, 2.8]


def solve(message, file_name):
    """Solve the Pokémon name based on the hint provided."""
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''.join(hint).replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall('^' + hint_string + '$', solutions, re.MULTILINE)
    return solution if solution else None


@tasks.loop(seconds=random.choice(intervals))
async def spam():
    """Spam a random string of numbers in the designated channel."""
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'], 7) * 5))


@spam.before_loop
async def before_spam():
    """Wait until the bot is ready before starting the spam task."""
    await client.wait_until_ready()


@client.event
async def on_ready():
    """Event triggered when the bot is ready."""
    print(f'Logged into account: {client.user.name}')


@client.event
async def on_message(message):
    """Handle incoming messages."""
    if message.author.id == poketwo and message.channel.category and message.channel.category.name == 'catch':
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                await asyncio.sleep(1)
                await message.channel.send('<@716390085896962058> h')
        else:
            content = message.content
            solution = None

            if 'The pokémon is ' in content:
                solution = solve(content, 'collection')

            if solution:
                await handle_solution(message, solution, '🎉Friends Col')
            else:
                solution = solve(content, 'mythical')
                if solution:
                    await handle_solution(message, solution, '😈Collection')


async def handle_solution(message, solution, base_category_name):
    """Handle moving a channel based on the solution."""
    guild = message.guild
    channel = message.channel

    # Move channel to appropriate category
    for i in range(1, 6):  # Up to 5 categories
        category_name = f"{base_category_name} {i}" if i > 1 else base_category_name
        category = discord.utils.get(guild.categories, name=category_name)
        if category and len(category.channels) < 48:
            await channel.edit(
                name=solution[0].lower().replace(' ', '-'),
                category=category,
                sync_permissions=True
            )
            await channel.send('<@716390085896962058> redirect 1 2 3 4 5 6')
            break


@client.command()
async def report(ctx, *, args):
    """Respond to the report command."""
    await ctx.send(args)


@client.command()
async def reboot(ctx):
    """Restart the spam loop."""
    spam.start()


@client.command()
async def pause(ctx):
    """Pause the spam loop."""
    spam.cancel()


# Start the spam task and run the bot
spam.start()
client.run(user_token)
            
