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
import praw

version = 'v3.0'

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
spam_id = os.getenv("spam_id")
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

if not spam_id:
    print("[ERROR] Missing environment variable: spam_id")
    sys.exit(1)

if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"

# --- Reddit API setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/3.0"
)

# --- Files ---
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
client = commands.Bot(command_prefix="!")

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
            break
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
    if channel:
        msg = ''.join(random.sample('1234567890', 7) * 5)
        await send_message_safe(channel, msg)

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    spam.start()
    asyncio.create_task(self_ping_loop())

# --- Self-ping loop ---
async def self_ping_loop():
    await client.wait_until_ready()
    while True:
        try:
            r = requests.get(service_url)
            print(f"Pinged {service_url} - status: {r.status_code}")
        except Exception as e:
            print(f"Error pinging self: {e}")
        await asyncio.sleep(600)

# --- Discord on_message ---
@client.event
async def on_message(message):
    await client.process_commands(message)

# --- Commands ---
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if spam.is_running():
        spam.cancel()
        await ctx.send("Spam loop stopped.")
    spam.start()
    await ctx.send("Spam loop restarted.")

@client.command()
async def pause(ctx):
    spam.cancel()
    await ctx.send("Spam loop paused.")

# --- Subreddit pool (giant) ---
nsfw_subs = [
    # Real content
    "nsfw", "gonewild", "rule34", "porn", "RealGirls", "trainerfucks",
    "NSFW_GIF", "nsfw_videos", "holdthemoan", "amateur", "nsfw_gifs",
    "grool", "thick", "PetiteGoneWild", "Blowjobs", "AnalGW",
    "cumsluts", "GoneWildPlus", "AsiansGoneWild", "altgonewild",
    "BustyPetite", "nsfwoutfits", "gifsgonewild", "dirtysmall",
    "bigasses", "CollegeAmateurs", "LegalTeensXXX", "OnOff",
    "legalteens", "gwcumsluts", "thickload", "BlowjobGifs", "homemadexxx",

    # Hentai/animated
    "hentai", "hentaipics", "rule34cartoons", "AnimeBooty", "thick_hentai",
    "ecchi", "oppai", "yuri", "pantsu", "hentai_gif", "hentai_irl",
    "Doujinshi", "Tentai", "hentai_bl", "monster_girls", "cumhentai",
    "WaifuPorn", "CartoonRule34", "lewdanimegirls", "biganimetiddies",
    "AnimeMILFs", "EcchiHentai", "3D_Hentai", "FutanariHentai", "nsfwanimegifs"
]

# --- NSFW Reddit Commands ---
def pick_post(subreddit_name, filter_type=None):
    subreddit = reddit.subreddit(subreddit_name)
    posts = [p for p in subreddit.hot(limit=80) if not p.stickied]

    if filter_type == "img":
        posts = [p for p in posts if not p.is_video and p.url.lower().endswith((".jpg", ".png", ".jpeg"))]
    elif filter_type == "vid":
        posts = [p for p in posts if p.is_video or p.url.lower().endswith((".gif", ".gifv", ".mp4")) or any(s in p.url for s in ["redgifs", "gfycat"])]

    return random.choice(posts) if posts else None

@client.command()
async def r(ctx, subreddit_name: str = "nsfw", filter_type: str = None):
    """Fetch a post from a specific subreddit (optional img/vid filter)."""
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only.")
        return

    try:
        post = pick_post(subreddit_name, filter_type)
        if post:
            await ctx.send(post.url)
        else:
            await ctx.send(f"❌ No posts found in r/{subreddit_name}.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@client.command()
async def rr(ctx, filter_type: str = None):
    """Fetch a random post from the giant NSFW pool (optional img/vid filter)."""
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only.")
        return

    try:
        subreddit_name = random.choice(nsfw_subs)
        post = pick_post(subreddit_name, filter_type)
        if post:
            await ctx.send(post.url)
        else:
            await ctx.send("❌ No posts found.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# --- Flask server ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server).start()

# --- Run bot ---
while True:
    try:
        client.run(user_token)
    except Exception as e:
        print(f"Bot crashed: {e}. Restarting in 10s...")
        time.sleep(10)
        
