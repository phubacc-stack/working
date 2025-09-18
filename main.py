import os
import sys
import asyncio
import random as pyrandom
import discord
from discord.ext import commands
import threading
from flask import Flask
import requests
import time
import praw
from datetime import datetime, timezone
import html
import json

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v6.0-auto-mix'
start_time = datetime.now(timezone.utc)
post_counter = 0

# --- User Token from environment ---
user_token = os.environ.get("user_token")
if not user_token:
    print("[ERROR] user_token not set in environment!")
    sys.exit(1)

service_url = os.environ.get("SERVICE_URL", "https://example.com")  # optional keepalive URL

# --- Reddit API setup (praw) ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

# --- Pools Loader ---
POOLS_URL = "https://raw.githubusercontent.com/phubacc-stack/working/8ce06d533b0ba820fedd0001368215a3d42fff29/pools.json"
nsfw_pool, hentai_pool = [], []

def load_pools():
    global nsfw_pool, hentai_pool
    try:
        r = requests.get(POOLS_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        nsfw_pool = data.get("nsfw_pool", [])
        hentai_pool = data.get("hentai_pool", [])
        print(f"[Pools] Loaded: NSFW={len(nsfw_pool)} Hentai={len(hentai_pool)}")
    except Exception as e:
        print(f"[WARNING] [Pools] Failed to load from GitHub, using placeholders: {e}")
        nsfw_pool = ["nsfw", "gonewild", "RealGirls"]
        hentai_pool = ["hentai", "rule34", "ecchi"]

load_pools()

# --- Bot Setup ---
client = commands.Bot(command_prefix="!", self_bot=False)
auto_tasks = {}

# --- Utils ---
async def send_with_gallery_support(channel, url, delay=30):
    global post_counter
    try:
        if isinstance(url, list):  # gallery
            for u in url:
                await channel.send(u)
                post_counter += 1
                print(f"[Sent] {u}")
                await asyncio.sleep(delay)
        else:
            await channel.send(url)
            post_counter += 1
            print(f"[Sent] {url}")
            await asyncio.sleep(delay)
    except Exception as e:
        print(f"[Error sending] {e}")

def get_filtered_posts(subreddit, content_type="img", search_term=None, section="hot"):
    posts = []
    try:
        sub = reddit.subreddit(subreddit)
        
        # Switch between sections: hot, new, rising, controversial, top
        if section == "hot":
            submission_generator = sub.hot(limit=50)
        elif section == "new":
            submission_generator = sub.new(limit=50)
        elif section == "rising":
            submission_generator = sub.rising(limit=50)
        elif section == "controversial":
            submission_generator = sub.controversial(limit=50)
        elif section == "top":
            submission_generator = sub.top(limit=50)
        else:
            # Default to "hot" if invalid section
            submission_generator = sub.hot(limit=50)
        
        for p in submission_generator:
            if p.over_18 is False:
                continue
            if search_term and search_term.lower() not in p.title.lower():
                continue
            url = p.url
            if content_type == "img" and any(url.endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                posts.append(url)
            elif content_type == "gif" and url.endswith(".gif"):
                posts.append(url)
            elif content_type == "vid" and ("v.redd.it" in url or url.endswith(".mp4")):
                posts.append(url)
            elif content_type == "random":
                posts.append(url)
            elif content_type == "gallery" and getattr(p, "is_gallery", False):
                items = []
                for media_id, m in getattr(p, "media_metadata", {}).items():
                    u = m["s"]["u"]
                    items.append(html.unescape(u))
                if items:
                    posts.append(items)
    except Exception as e:
        print(f"[get_filtered_posts error] {e}")
    return posts

# --- Auto System ---
async def auto_loop(channel, subreddit=None, content_type="img", delay=30, search_term=None, poolmix=False):
    global auto_tasks
    try:
        sections = ["hot", "new", "rising", "controversial", "top"]  # Possible sections to fetch from
        section_idx = 0  # Start from 'hot'
        
        while True:
            info = auto_tasks.get(channel.id)
            if not info or info.get("task").cancelled():
                break
            if info.get("paused"):
                await asyncio.sleep(2)
                continue
            try:
                if poolmix:
                    sub = pyrandom.choice(nsfw_pool + hentai_pool)
                else:
                    sub = subreddit

                ctype = info.get("type", content_type)
                if ctype == "random":
                    ctype = pyrandom.choice(["img", "gif", "vid", "gallery"])

                posts = get_filtered_posts(sub, ctype, search_term=search_term, section=sections[section_idx])

                if not posts:
                    await asyncio.sleep(delay)
                    continue

                if ctype == "gallery":  # Send all images in the gallery
                    await send_with_gallery_support(channel, posts, delay=delay)
                else:
                    choice = pyrandom.choice(posts)
                    await send_with_gallery_support(channel, choice, delay=delay)

                # Cycle to the next section
                section_idx = (section_idx + 1) % len(sections)
            except Exception as e:
                print(f"[auto_loop error] {e}")
            await asyncio.sleep(delay)
    finally:
        auto_tasks.pop(channel.id, None)

def start_auto(channel_id, subreddit=None, content_type="img", delay=30, search_term=None, poolmix=False):
    if channel_id in auto_tasks:
        auto_tasks[channel_id]["task"].cancel()
    channel = client.get_channel(channel_id)
    task = client.loop.create_task(auto_loop(channel, subreddit=subreddit, content_type=content_type, delay=delay, search_term=search_term, poolmix=poolmix))
    auto_tasks[channel_id] = {"task": task, "paused": False, "subreddit": subreddit, "type": content_type, "delay": delay, "search_term": search_term, "poolmix": poolmix}

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    if amount > 50: amount = 50
    collected = []
    while len(collected) < amount:
        sub = pyrandom.choice(nsfw_pool + hentai_pool)
        posts = get_filtered_posts(sub, content_type)
        if posts:
            collected.append(pyrandom.choice(posts))
    for item in collected:
        await send_with_gallery_support(ctx.channel, item)

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    if amount > 50: amount = 50
    collected = []
    posts = get_filtered_posts(subreddit, content_type)
    for p in posts[:amount]:
        collected.append(p)
    for item in collected:
        await send_with_gallery_support(ctx.channel, item)

@client.command()
async def autosub(ctx, subreddit: str, seconds: int = 30, content_type: str = "img"):
    start_auto(ctx.channel.id, subreddit=subreddit, content_type=content_type, delay=seconds)
    msg = await ctx.send(f"▶️ AutoSub started: r/{subreddit} every {seconds}s for {content_type}. Use reactions to control.")
    for r in ["⏸️", "▶️", "⏹️", "🖼️", "🎥", "🎬", "🔀", "ℹ️"]:
        await msg.add_reaction(r)

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
    start_auto(ctx.channel.id, content_type=content_type, delay=seconds, poolmix=True)
    msg = await ctx.send(f"▶️ AutoMix started: Pool mix every {seconds}s for {content_type}. Use reactions to control.")
    for r in ["⏸️", "▶️", "⏹️", "🖼️", "🎥", "🎬", "🔀", "ℹ️"]:
        await msg.add_reaction(r)

@client.command()
async def autostop(ctx):
    if ctx.channel.id in auto_tasks:
        auto_tasks[ctx.channel.id]["task"].cancel()
        auto_tasks.pop(ctx.channel.id, None)
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

@client.command()
async def gallerycollection(ctx, content_type: str = "gallery"):
    """Fetch random gallery posts"""
    collected = []
    while len(collected) < 10:  # Adjust the amount based on how many galleries you want
        sub = pyrandom.choice(nsfw_pool + hentai_pool)
        posts = get_filtered_posts(sub, content_type)
        if posts:
            collected.extend(posts)

    if collected:
        for item in pyrandom.sample(collected, len(collected)):  # Randomize gallery order
            await send_with_gallery_support(ctx.channel, item)
    else:
        await ctx.send("❌ No galleries found.")
    
@client.command()
async def who(ctx):
    await ctx.send(f"I am a Discord NSFW bot v{version}")

@client.command(name="myhelp")  # renamed here
async def help(ctx):  # function name can stay "help" or change
    help_message = (
        "!r [amount] [type] - Random posts\n"
        "!rsub [subreddit] [amount] [type] - Posts from subreddit\n"
        "!auto [seconds] [type] - Auto pool mix\n"
        "!autosub [sub] [seconds] [type] - Auto subreddit\n"
        "!autostop - Stop auto\n"
        "!gallerycollection - Fetch random gallery posts\n"
        "!stats - Bot stats\n"
        "!who - Bot info"
    )
    await ctx.send(help_message)

# --- Reaction Controls ---
@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return
    channel = client.get_channel(payload.channel_id)
    if not channel or channel.id not in auto_tasks:
        return
    info = auto_tasks[channel.id]
    emoji = str(payload.emoji)
    if emoji == "⏸️":
        info["paused"] = True
        await channel.send("⏸️ Auto paused.")
    elif emoji == "▶️":
        info["paused"] = False
        await channel.send("▶️ Auto resumed.")
    elif emoji == "⏹️":
        info["task"].cancel()
        auto_tasks.pop(channel.id, None)
        await channel.send("⏹️ Auto stopped.")
    elif emoji == "🖼️":
        info["type"] = "img"
        await channel.send("🖼️ Type set to IMG.")
    elif emoji == "🎬":
        info["type"] = "vid"
        await channel.send("🎬 Type set to VID.")
    elif emoji == "🎥":
        info["type"] = "gif"
        await channel.send("🎥 Type set to GIF.")
    elif emoji == "🔀":
        info["type"] = "random"
        await channel.send("🔀 Type set to RANDOM.")
    elif emoji == "ℹ️":
        await channel.send(f"ℹ️ Auto status:\nSubreddit: {info.get('subreddit')}\nPoolMix: {info.get('poolmix')}\nType: {info.get('type')}\nPaused: {info.get('paused')}\nDelay: {info.get('delay')}s\nSearch: {info.get('search_term')}")

# --- Keepalive Flask ---
app = Flask("")
@app.route("/")
def home():
    return "Bot is alive."

def run():
    app.run(host="0.0.0.0", port=8080)

def ping():
    while True:
        try:
            requests.get(service_url)
        except:
            pass
        time.sleep(600)

threading.Thread(target=run, daemon=True).start()
threading.Thread(target=ping, daemon=True).start()

# --- Run Bot ---
client.run(user_token)
                
