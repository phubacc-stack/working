import re
import os
import asyncio
import random
from discord.ext import commands, tasks
import discord

# ---------------- Keep-Alive Server ----------------
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ---------------- Bot Setup ----------------
version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
client = commands.Bot(command_prefix="!")

# Updated spam intervals
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

# ---------------- Functions ----------------
def solve(message, file_name):
    hint = [c for c in message[15:-1] if c != '\\']
    hint_string = ''.join(hint).replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_string}$', solutions, re.MULTILINE)
    return solution if solution else None

async def move_to_category(channel, solution, base_category_name, guild, max_channels=48, max_categories=5):
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

# ---------------- Spam Loop ----------------
@tasks.loop(seconds=random.choice(intervals))
async def spam():
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
    await client.wait_until_ready()

# ---------------- Events ----------------
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    spam.start()

@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category:
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                try:
                    def check(m):
                        return (m.author.id == poketwo and 
                                m.channel == message.channel and 
                                m.content.startswith("Congratulations"))
                    await client.wait_for('message', timeout=55.0, check=check)
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

# ---------------- Commands ----------------
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if spam.is_running():
        spam.cancel()
        await ctx.send("Spam loop has been stopped.")
    spam.start()
    await ctx.send("Spam loop has been restarted.")

@client.command()
async def pause(ctx):
    spam.cancel()

# ---------------- Keep Alive ----------------
keep_alive()

# ---------------- Run Bot ----------------
client.run(user_token)
