import re
import os
import asyncio
import random
from discord.ext import commands, tasks

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

num_pokemon = 0
shiny = 0
legendary = 0
mythical = 0

poketwo = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

# Function to solve the Pokémon name based on the hint from the message
def solve(message, file_name):
    # Ensure the file exists before proceeding
    if not os.path.exists(file_name):
        print(f"Error: The file {file_name} does not exist.")
        return None
    
    # Extract the hint from the message (starting at index 15)
    hint = []
    try:
        for i in range(15, len(message) - 1):
            if message[i] != '\\':
                hint.append(message[i])
    except IndexError:
        print("Error: The message does not contain enough characters.")
        return None
    
    # Build the hint string
    hint_string = ''.join(hint)

    # Remove underscores from the hint (so we just have the known part)
    hint_string = hint_string.replace('_', '')

    # If the hint string is empty after removing underscores, we can't search
    if not hint_string:
        print("Error: No valid hint found to search for.")
        return None

    # Open the appropriate file and read the content
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            solutions = f.read()
    except Exception as e:
        print(f"Error reading the file {file_name}: {e}")
        return None
    
    # Perform case-insensitive regex match for the hint (we are searching for the cleaned hint string)
    try:
        solution = re.findall(f'^{hint_string.lower()}$', solutions, re.MULTILINE | re.IGNORECASE)
    except re.error as e:
        print(f"Error with regex: {e}")
        return None
    
    # If no match found, return None
    if len(solution) == 0:
        print("No match found.")
        return None
    
    return solution  # Return the matched solution(s)

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    guild = message.guild
    category = channel.category
    # Check if message is from Poketwo
    if message.author.id == poketwo:
        if message.channel.category.name == 'catch':
            # Check if message contains Pokémon embed
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await channel.send('<@716390085896962058> h')
            else:
                content = message.content
                solution = None
                
                # Try to solve the Pokémon name from the message content
                if 'The pokémon is ' in content:
                    solution = solve(content, 'collection')
                    if solution:
                        await channel.clone()
                        # If solution found, move to new category and sync.
                        category_name = '🎉Friends Col'
                        guild = message.guild
                        old_category = channel.category
                        new_category = [c for c in guild.categories if c.name == category_name][0]
                        num_channels = len(new_category.channels)
                        print(f"There are {num_channels} channels in the {category_name} category.")
                        if len(new_category.channels) <= 48:
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        if len(new_category.channels) >= 48:
                            category_name = '🎉Friends Col 2'
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            num_channels = len(new_category.channels)
                            print(f"There are {num_channels} channels in the {category_name} category.")
                            if len(new_category.channels) <= 48:
                                await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')
                    if not solution:
                        solution = solve(content, 'mythical')
                        if solution:
                            await channel.clone()
                            # If solution found, move to new category and sync.
                            category_name = '😈Collection'
                            guild = message.guild
                            old_category = channel.category
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            num_channels = len(new_category.channels)
                            print(f"There are {num_channels} channels in the {category_name} category.")
                            if len(new_category.channels) <= 48:
                                await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                            if len(new_category.channels) >= 48:
                                category_name = '😈Collection 2'
                                new_category = [c for c in guild.categories if c.name == category_name][0]
                                num_channels = len(new_category.channels)
                                print(f"There are {num_channels} channels in the {category_name} category.")
                                if len(new_category.channels) <= 48:
                                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                            await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')

# Task that sends a random spam message at intervals
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# On bot ready event
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')

# Handles incoming messages
@client.event
async def on_message(message):
    # Your on_message logic remains unchanged
    pass

# Bot commands
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if not spam.is_running():
        spam.start()
    await ctx.send("Spam task has been restarted!")

@client.command()
async def pause(ctx):
    if spam.is_running():
        spam.cancel()
    await ctx.send("Spam task has been paused!")

# Main function to run the bot
async def main():
    async with client:
        spam.start()  # Start the spam task
        await client.start(user_token)

# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
                    
