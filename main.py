import os
import sys
import re
import asyncio
import random
import discord
from discord.ext import commands, tasks
import threading
from flask import Flask
import requests
import time

version = 'v2.8'

# --- Environment Variables ---
user_token = os.getenv("user_token")
spam_id = os.getenv("spam_id")
service_url = os.getenv("SERVICE_URL")  # Optional: Render URL for self-ping

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

if not spam_id:
    print("[ERROR] Missing environment variable: spam_id")
    sys.exit(1)

if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"  # fallback

# --- Read Files ---
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Spam intervals
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

# --- Solve hints ---
def solve(message, file_name):
    hint = [c for c in message[15:-1] if c != '\\']
    hint_string = ''.join(hint).replace('_', '.')
    with open(file_name, "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_string}$', solutions, re.MULTILINE)
    return solution if solution else None

# --- Safe message sender ---
async def send_message_safe(channel, content):
    while True:
        try:
            await channel.send(content)
            break  # message sent successfully
        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', 5)
                print(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
            else:
                print(f"HTTPException: {e}. Retrying in 60 seconds...")
                await asyncio.sleep(60)
        except discord.errors.DiscordServerError as e:
            print(f"Discord server error: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)

# --- Spam loop ---
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    if not channel:
        print("Channel not found.")
        return

    message_content = ''.join(random.sample('1234567890', 7) * 5)
    await send_message_safe(channel, message_content)

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# --- On ready ---
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    spam.start()
    asyncio.create_task(self_ping_loop())

# --- Self-ping loop to keep Render alive ---
async def self_ping_loop():
    await client.wait_until_ready()
    while True:
        try:
            r = requests.get(service_url)
            print(f"Pinged {service_url} - status: {r.status_code}")
        except Exception as e:
            print(f"Error pinging self: {e}")
        await asyncio.sleep(600)  # ping every 10 minutes

# --- Discord on_message ---
@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category:
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                try:
                    def check(m):
                        return (
                            m.author.id == poketwo and
                            m.channel == message.channel and
                            m.content.startswith("Congratulations")
                        )
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
    # Make sure commands are processed
    await client.process_commands(message)

# --- Move to category ---
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

# --- Commands ---
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

# --- NEW: Reddit NSFW commands ---
@client.command()
async def redditnsfw(ctx, subreddit: str = "trainerfucks"):
    """Fetch a random NSFW post from a subreddit"""
    try:
        headers = {"User-Agent": "DiscordBot/1.0"}
        url = f"https://www.reddit.com/r/{subreddit}/random/.json?limit=1"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            await ctx.send(f"Failed to fetch from r/{subreddit}.")
            return

        data = response.json()
        post = data[0]["data"]["children"][0]["data"]

        title = post["title"]
        image_url = post.get("url")

        await ctx.send(f"**{title}**\n{image_url}")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@client.command()
async def randomnsfw(ctx):
    """Fetch a random NSFW post from r/trainerfucks"""
    await redditnsfw(ctx, "trainerfucks")

# --- Flask server for uptime ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server).start()

# --- Run bot with auto-restart ---
while True:
    try:
        client.run(user_token)
    except Exception as e:
        print(f"Bot crashed: {e}. Restarting in 10 seconds...")
        time.sleep(10)
        
