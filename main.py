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
intervals = [3.8, 4.0, 4.2, 4.4]

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
    Move the original channel to the appropriate category or create a new category dynamically.

    Args:
        channel: The original channel to move.
        solution: The solution name to use for renaming the cloned channel.
        base_category_name: The base name for the categories.
        guild: The Discord guild (server) instance.
        max_channels: Maximum number of channels allowed per category.
        max_categories: Maximum number of additional categories to create.
    """
    for i in range(1, max_categories + 1):
        category_name = f"{base_category_name} {i}" if i > 1 else base_category_name
        category = discord.utils.get(guild.categories, name=category_name)

        if category is None:
            print(f"Creating new category: {category_name}")
            category = await guild.create_category(category_name)

        if len(category.channels) < max_channels:
            print(f"Moving channel to category: {category_name}")
            await channel.edit(
                name=solution.lower().replace(' ', '-'),
                category=category,
                sync_permissions=True,
            )
            return

    print(f"All {base_category_name} categories are full.")

@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category:
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
                    # Clone the channel without the embed
                    cloned_channel = await message.channel.clone(reason="Cloning for backup")
                    # Keep the cloned channel in the 'catch' category without an embed
                    await cloned_channel.send("Pokémon spawn has been backed up here.")  # Optional message

                    # Move and rename the original channel
                    await move_to_category(
                        channel=message.channel,  # Move the original channel
                        solution=solution[0],
                        base_category_name="🎉Friends Col",
                        guild=message.guild
                    )
                    await cloned_channel.send('<@716390085896962058> redirect 1 2 3 4 5 6 ')
                else:
                    solution = solve(content, 'mythical')
                    if solution:
                        # Clone the channel without the embed
                        cloned_channel = await message.channel.clone(reason="Cloning for backup")
                        # Keep the cloned channel in the 'catch' category without an embed
                        await cloned_channel.send("Pokémon spawn has been backed up here.")  # Optional message

                        # Move and rename the original channel
                        await move_to_category(
                            channel=message.channel,  # Move the original channel
                            solution=solution[0],
                            base_category_name="😈Collection",
                            guild=message.guild
                        )
                        await cloned_channel.send('<@716390085896962058> redirect 1 2 3 4 5 6 ')

@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    spam.start()

@client.command()
async def pause(ctx):
    spam.cancel()

client.run(user_token)
