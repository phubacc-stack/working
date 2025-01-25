import re
import os
import asyncio
import random
from discord.ext import commands, tasks

# Version
version = 'v2.8'

# Environment Variables
user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

# Constants
poketwo_id = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

# File Handling
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()
with open('collection', 'r', encoding='utf8') as file:
    collection_list = file.read()

# Solve Hint Function
def solve(message, file_name):
    hint = message.replace("_", ".")  # Replace underscores with regex dots
    print(f"Processing hint: {hint}")

    # Match the hint with Pokémon names in the file
    try:
        with open(file_name, 'r', encoding='utf8') as f:
            solutions = f.read().splitlines()
    except FileNotFoundError:
        print(f"File '{file_name}' not found!")
        return None

    matches = [name for name in solutions if re.fullmatch(hint, name)]
    print(f"Matches found: {matches}")
    return matches if matches else None

# Handle Pokétwo Embeds in Catch Category
@client.event
async def on_message(message):
    if message.author.id == poketwo_id:
        channel = message.channel
        category = channel.category

        # Check for messages in the "catch" category
        if category and category.name.lower() == "catch" and message.embeds:
            embed_title = message.embeds[0].title
            if "wild pokémon has appeared!" in embed_title.lower():
                await asyncio.sleep(1)
                await channel.send(f"<@{poketwo_id}> h")
                return

        # Handle Pokémon hint solutions
        if "The pokémon is " in message.content:
            hint = message.content.split("The pokémon is ")[1].strip()
            solution = solve(hint, "collection") or solve(hint, "mythical")

            if solution:
                if solution[0] in collection_list:
                    await handle_collection(channel, solution[0], "🎉Friends Col", "collection")
                elif solution[0] in mythical_list:
                    await handle_collection(channel, solution[0], "😈Collection", "mythical")
                else:
                    print("No valid solution found in collection or mythical files.")

# Collection Handler
async def handle_collection(channel, solution, category_name, file_name):
    guild = channel.guild

    # Move the channel to the right category
    new_category = [c for c in guild.categories if c.name == category_name][0]
    num_channels = len(new_category.channels)
    print(f"There are {num_channels} channels in the {category_name} category.")

    if len(new_category.channels) <= 48:
        await channel.edit(name=solution.lower().replace(" ", "-"), category=new_category, sync_permissions=True)
    else:
        # Handle full categories by creating new categories if necessary
        new_category_name = f"{category_name} {len(guild.categories) + 1}"
        new_category = await guild.create_category(new_category_name)
        await channel.edit(name=solution.lower().replace(" ", "-"), category=new_category, sync_permissions=True)
        print(f"Created new category: {new_category_name}")

# Spam Task
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    try:
        channel = client.get_channel(int(spam_id))
        if channel:
            spam_message = ''.join(random.choices('1234567890', k=35))
            await channel.send(spam_message)
    except Exception as e:
        print(f"Error in spam task: {e}")

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# On Ready Event
@client.event
async def on_ready():
    print(f"Logged into account: {client.user.name}")
    if not spam.is_running():
        spam.start()

# Commands
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if not spam.is_running():
        spam.start()
    await ctx.send("Spam task restarted.")

@client.command()
async def pause(ctx):
    if spam.is_running():
        spam.cancel()
    await ctx.send("Spam task paused.")

# Main Function
async def main():
    async with client:
        spam.start()
        await client.start(user_token)

if __name__ == "__main__":
    asyncio.run(main())
    
