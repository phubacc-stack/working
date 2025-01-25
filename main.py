import os
import asyncio
import random
from discord.ext import commands, tasks

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read().splitlines()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read().splitlines()

poketwo = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')

# Helper function for channel management
async def manage_channel(channel, category_name, solution):
    guild = channel.guild
    category = next((c for c in guild.categories if c.name == category_name), None)
    if not category:
        print(f"Category '{category_name}' not found.")
        return False
    if len(category.channels) < 48:
        await channel.edit(name=solution.lower().replace(' ', '-'), category=category, sync_permissions=True)
        return True
    return False

@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category and message.channel.category.name == 'catch':
        if message.embeds and 'wild pokémon has appeared!' in message.embeds[0].title:
            await asyncio.sleep(1)
            await message.channel.send('<@716390085896962058> h')
        elif 'The pokémon is ' in message.content:
            solution = message.content.split('The pokémon is ')[1].strip()
            if solution:
                await message.channel.clone()
                for i in range(1, 6):  # Check up to 5 categories
                    category_name = f'🎉Friends Col {i}' if i > 1 else '🎉Friends Col'
                    if await manage_channel(message.channel, category_name, solution):
                        break
                else:
                    print("No available category for 'Friends Col'.")

# Spam task
@tasks.loop(seconds=5)
async def spam():
    channel = client.get_channel(int(spam_id))
    if channel:
        interval = random.choice([2.2, 2.4, 2.6, 2.8])
        await asyncio.sleep(interval)
        await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# Bot ready event
@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

# Commands
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if not spam.is_running():
        spam.start()
    await ctx.send("Spam task restarted!")

@client.command()
async def pause(ctx):
    if spam.is_running():
        spam.stop()
    await ctx.send("Spam task paused!")

# Main function
async def main():
    async with client:
        spam.start()
        await client.start(user_token)

if __name__ == "__main__":
    asyncio.run(main())
    
