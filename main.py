import re, os, asyncio, random, string
from discord.ext import commands, tasks
import discord

version = 'v2.7'

# Environment Variables
user_token = os.getenv('user_token')
spam_id = os.getenv('spam_id')

# Load data from files
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

# Bot Configurations
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

client = commands.Bot(command_prefix='Lickitysplit', intents=intents)

# Task Intervals
intervals = [2.2, 2.4, 2.6, 2.8]


def solve(message, file_name):
    """Solve the Pokémon name based on the hint."""
    hint = ''.join(char for char in message[15:-1] if char != '\\')
    hint_replaced = hint.replace('_', '.')
    with open(file_name, "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_replaced}$', solutions, re.MULTILINE)
    return solution if solution else None


@tasks.loop(seconds=random.choice(intervals))
async def spam():
    """Send random spam messages to the target channel."""
    channel = client.get_channel(int(spam_id))
    if channel:
        await channel.send(''.join(random.sample(string.digits, 7) * 5))
    else:
        print("Spam channel not found.")


@spam.before_loop
async def before_spam():
    """Ensure the bot is ready before starting the spam task."""
    await client.wait_until_ready()


@client.event
async def on_ready():
    """Event triggered when the bot is ready."""
    print(f'Logged into account: {client.user.name}')


@client.event
async def on_message(message):
    """Handle messages from Poketwo."""
    if message.author.id == 716390085896962058:  # Check if the message is from Poketwo
        if message.channel.category and message.channel.category.name.lower() == 'catch':
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await message.channel.send('<@716390085896962058> h')
            else:
                solution = None
                if 'The pokémon is ' in message.content:
                    solution = solve(message.content, 'collection')
                if solution:
                    await handle_channel_edit(message.channel, solution[0].lower().replace(' ', '-'), '🎉Friends Col')
                else:
                    solution = solve(message.content, 'mythical')
                    if solution:
                        await handle_channel_edit(message.channel, solution[0].lower().replace(' ', '-'), '😈Collection')


async def handle_channel_edit(channel, new_name, base_category_name):
    """Edit channel category and name based on availability."""
    guild = channel.guild
    for i in range(1, 6):  # Check up to 5 categories
        category_name = f'{base_category_name} {i}' if i > 1 else base_category_name
        category = discord.utils.get(guild.categories, name=category_name)
        if category and len(category.channels) < 48:
            await channel.edit(name=new_name, category=category, sync_permissions=True)
            await channel.send('<@716390085896962058> redirect 1 2 3 4 5 6')
            return
    print(f"No available slots in {base_category_name} categories.")


@client.command()
async def report(ctx, *, args):
    """Send a report message."""
    await ctx.send(args)


@client.command()
async def reboot(ctx):
    """Restart the spam task."""
    if not spam.is_running():
        spam.start()
        await ctx.send("Spam task restarted.")
    else:
        await ctx.send("Spam task is already running.")


@client.command()
async def pause(ctx):
    """Pause the spam task."""
    if spam.is_running():
        spam.cancel()
        await ctx.send("Spam task paused.")
    else:
        await ctx.send("Spam task is not running.")


# Run the bot
client.run(user_token)
