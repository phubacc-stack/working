import re
import os
import asyncio
import random
from discord.ext import commands, tasks
import discord

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

def solve(message, file_name):
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
    channel = client.get_channel(int(spam_id))
    if channel:
        await channel.send(''.join(random.sample(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'], 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    spam.start()

async def move_to_category(channel, solution, base_category_name, guild, max_channels=48, max_categories=5):
    """
    Move the channel to the appropriate category or create a new category dynamically.

    Args:
        channel: The channel to move.
        solution: The solution name to use for renaming the channel.
        base_category_name: The base name for the categories.
        guild: The Discord guild (server) instance.
        max_channels: Maximum number of channels allowed per category.
        max_categories: Maximum number of additional categories to create.
    """
    for i in range(1, max_categories + 1):  # Loop through categories
        category_name = f"{base_category_name} {i}" if i > 1 else base_category_name
        new_category = discord.utils.get(guild.categories, name=category_name)
        
        if new_category is None:
            # Create a new category if it doesn't exist
            print(f"Category '{category_name}' does not exist. Creating it now...")
            new_category = await guild.create_category(category_name)
            print(f"Created new category: {category_name}")
        
        # Check if the category has space for more channels
        if len(new_category.channels) < max_channels:
            print(f"Moving channel to {category_name}.")
            await channel.edit(
                name=solution.lower().replace(' ', '-'),
                category=new_category,
                sync_permissions=True
            )
            return  # Exit after moving the channel

    # If no category is available
    print(f"All {base_category_name} categories are full. No further categories created.")

@client.event
async def on_message(message):
    if message.author.id == poketwo:
        if message.channel.category and message.channel.category.name == 'catch':
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await message.channel.send('<@716390085896962058> h')
            else:
                content = message.content
                solution = None

                if 'The pokémon is ' in content:
                    # Try solving from the 'collection' file
                    solution = solve(content, 'collection')
                    if solution:
                        await move_to_category(
                            channel=message.channel,
                            solution=solution[0],
                            base_category_name='🎉Friends Col',
                            guild=message.guild
                        )
                    else:
                        # Try solving from the 'mythical' file
                        solution = solve(content, 'mythical')
                        if solution:
                            await move_to_category(
                                channel=message.channel,
                                solution=solution[0],
                                base_category_name='😈Collection',
                                guild=message.guild
                            )

@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    spam.start()

@client.command()
async def pause(ctx):
    spam.cancel()

# This will start the bot and the event loop
client.run(user_token)
