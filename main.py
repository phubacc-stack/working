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
client = commands.Bot(command_prefix="!")

# Updated spam intervals
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

def solve(message, file_name):
    """
    Extracts a hint from the message and finds matching solutions in the given file.
    """
    hint = [c for c in message[15:-1] if c != '\\']
    hint_string = ''.join(hint).replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_string}$', solutions, re.MULTILINE)
    return solution if solution else None

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    """
    Sends a spam message to the designated channel at a random interval.
    Handles rate limits and Discord server errors with retries.
    """
    channel = client.get_channel(int(spam_id))
    if not channel:
        print("Channel not found.")
        return

    message_content = ''.join(random.sample('1234567890', 7) * 5)

    try:
        await channel.send(message_content)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = getattr(e, 'retry_after', 5)
            print(f"Rate limit exceeded. Retrying in {retry_after} seconds...")
            await asyncio.sleep(retry_after)
            await spam()
        else:
            print(f"HTTP error: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)
            await spam()
    except discord.errors.DiscordServerError as e:
        print(f"Discord server error: {e}. Retrying in 60 seconds...")
        await asyncio.sleep(60)
        await spam()

@spam.before_loop
async def before_spam():
    """
    Waits until the client is ready before starting the spam loop.
    """
    await client.wait_until_ready()

@client.event
async def on_ready():
    """
    Called when the bot is ready.
    Prints the bot's name and starts the spam loop.
    """
    print(f'Logged into account: {client.user.name}')
    spam.start()

@client.event
async def on_message(message):
    """
    Processes incoming messages.
    
    - For messages from Pokétwo:
      * If the message is an embed with a wild spawn, wait 7 seconds for a congratulatory message.
        If none is received, send '<@716390085896962058> h'.
      * If the message is not an embed, check for a solution hint and clone/move the channel accordingly.
    - Also ensures other commands are processed.
    """
    if message.author.id == poketwo and message.channel.category:
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                try:
                    def check(m):
                        return (m.author.id == poketwo and 
                                m.channel == message.channel and 
                                m.content.startswith("Congratulations"))
                    await client.wait_for('message', timeout=7.0, check=check)
                except asyncio.TimeoutError:
                    await message.channel.send('<@716390085896962058> h')
        else:
            content = message.content
            solution = None
            if 'The pokémon is ' in content:
                solution = solve(content, 'collection')
                if solution:
                    cloned_channel = await message.channel.clone(reason="Cloning for backup")
                    await cloned_channel.send("Pokémon spawn has been backed up here.")
                    await move_to_category(
                        channel=message.channel,
                        solution=solution[0],
                        base_category_name="🎉Friends Col",
                        guild=message.guild
                    )
                    await cloned_channel.send('<@716390085896962058> redirect 1 2 3 4 5 6 ')
                else:
                    solution = solve(content, 'mythical')
                    if solution:
                        cloned_channel = await message.channel.clone(reason="Cloning for backup")
                        await cloned_channel.send("Pokémon spawn has been backed up here.")
                        await move_to_category(
                            channel=message.channel,
                            solution=solution[0],
                            base_category_name="😈Collection",
                            guild=message.guild
                        )
                        await cloned_channel.send('<@716390085896962058> redirect 1 2 3 4 5 6 ')
    await client.process_commands(message)

async def move_to_category(channel, solution, base_category_name, guild, max_channels=48, max_categories=5):
    """
    Moves the channel to the appropriate category based on the solution.
    If the category doesn't exist, it creates one. Checks for max channel limits.
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

@client.command()
async def report(ctx, *, args):
    """
    A command to send a report message.
    Usage: !report <message>
    """
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    """
    A command to reboot the spam loop.
    Usage: !reboot
    """
    if spam.is_running():
        spam.cancel()
        await ctx.send("Spam loop has been stopped.")
    spam.start()
    await ctx.send("Spam loop has been restarted.")

@client.command()
async def pause(ctx):
    """
    A command to pause the spam loop.
    Usage: !pause
    """
    spam.cancel()

client.run(user_token)
