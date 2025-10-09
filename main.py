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
import json
from datetime import datetime, timezone
from rapidfuzz import process, fuzz

# --- Ensure randomness ---
pyrandom.seed(os.getpid() ^ int(time.time() * 1000000))

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.9-full-gallery-fix'
start_time = datetime.now(timezone.utc)
post_counter = 0
seen_posts = set()

# --- Discord Env ---
user_token = os.getenv("user_token")
service_url = os.getenv("SERVICE_URL") or "https://working-1-uy7j.onrender.com"

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

# --- Pools ---
try:
    with open("pools.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        nsfw_pool = data.get("nsfw_pool", [])
        hentai_pool = data.get("hentai_pool", [])
except Exception as e:
    print(f"[ERROR] Could not load pools.json: {e}")
    nsfw_pool, hentai_pool = [], []

all_subs_pool = nsfw_pool + hentai_pool

# --- Reddit API (your credentials) ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

client = commands.Bot(command_prefix="!")

# --- Fuzzy correction ---
def correct_subreddit(subreddit_name):
    match, score, _ = process.extractOne(subreddit_name, all_subs_pool, scorer=fuzz.ratio)
    if score >= 70:
        print(f"[Fuzzy] Corrected '{subreddit_name}' -> '{match}'")
        return match
    return subreddit_name

# --- Iterator cache ---
sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        listings = getattr(subreddit, fetch_method)(limit=None)
        sub_iterators[key] = iter(listings)
    return sub_iterators[key]

# --- URL filter ---
def filter_url(url, content_type):
    if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
        return None
    if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
        url += ".jpg"
    if content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url):
        return url
    if content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")):
        return url
    if content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url or "redgifs" in url):
        return url
    if content_type == "any":
        return url
    return None

# --- Fetch posts ---
def get_filtered_posts(subreddit_name, content_type, fetch_method=None, batch_size=25):
    global seen_posts
    posts = []
    subreddit_name = correct_subreddit(subreddit_name)
    fetch_method = fetch_method or pyrandom.choice(["hot", "new", "top"])
    print(f"[Fetching] r/{subreddit_name} via {fetch_method}...")

    try:
        iterator = get_subreddit_iterator(subreddit_name, fetch_method)
        while len(posts) < batch_size:
            try:
                post = next(iterator)
            except StopIteration:
                sub_iterators[f"{subreddit_name}:{fetch_method}"] = None
                break
            if post.stickied or not post.over_18:
                continue

            # Handle galleries separately
            if getattr(post, "is_gallery", False):
                if post.id not in seen_posts:
                    posts.append(post)
                    seen_posts.add(post.id)
            else:
                url = filter_url(str(post.url), content_type)
                if url and url not in seen_posts:
                    posts.append(url)
                    seen_posts.add(url)

        if len(seen_posts) > 5000:
            seen_posts.clear()

    except Exception as e:
        print(f"[Reddit Error] r/{subreddit_name}: {e}")

    print(f"[Fetched] r/{subreddit_name} -> {len(posts)} posts")
    return posts

# --- Safe send ---
async def safe_send(channel, url):
    try:
        await channel.send(url)
    except Exception as e:
        print(f"[Discord Error] {e}")

# --- Send with gallery support ---
async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item, list):
        for url in item:
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(pyrandom.uniform(2, 3))
    elif getattr(item, "is_gallery", False):
        media = getattr(item, "media_metadata", {})
        gallery_items = getattr(item, "gallery_data", {}).get("items", [])
        for i in gallery_items:
            media_id = i['media_id']
            url = media[media_id]['s']['u'].replace("&amp;", "&")
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(pyrandom.uniform(2, 3))
    else:
        await safe_send(channel, item)
        post_counter += 1

# --- Auto system ---
auto_tasks = {}
skip_flags = {}
pause_flags = {}

async def auto_loop(ctx, pool, content_type, delay):
    channel = ctx.channel
    while True:
        if pause_flags.get(channel.id):
            await asyncio.sleep(2)
            continue
        if skip_flags.pop(channel.id, False):
            await ctx.send("⏭️ Skipped post")
        subreddit = pyrandom.choice(pool)
        posts = get_filtered_posts(subreddit, content_type, fetch_method="hot", batch_size=1)
        if posts:
            await send_with_gallery_support(channel, posts[0])
        await asyncio.sleep(delay)

# --- Commands ---
@client.command()
async def auto(ctx, content_type: str = "any", delay: int = 30):
    if ctx.channel.id in auto_tasks:
        await ctx.send("⚠️ Auto already running here")
        return
    task = asyncio.create_task(auto_loop(ctx, all_subs_pool, content_type, delay))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started ({content_type}, every {delay}s)")

@client.command()
async def autosub(ctx, sub: str, content_type: str = "any", delay: int = 30):
    if ctx.channel.id in auto_tasks:
        await ctx.send("⚠️ Auto already running here")
        return
    task = asyncio.create_task(auto_loop(ctx, [sub], content_type, delay))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started for r/{sub} ({content_type}, {delay}s)")

@client.command()
async def stop(ctx):
    task = auto_tasks.pop(ctx.channel.id, None)
    if task:
        task.cancel()
        await ctx.send("⏹️ Auto stopped")
    else:
        await ctx.send("❌ No auto running")

@client.command()
async def skip(ctx):
    skip_flags[ctx.channel.id] = True
    await ctx.send("⏭️ Next post will be skipped")

@client.command()
async def pause(ctx):
    pause_flags[ctx.channel.id] = True
    await ctx.send("⏸️ Auto paused")

@client.command()
async def resume(ctx):
    pause_flags[ctx.channel.id] = False
    await ctx.send("▶️ Auto resumed")

@client.command()
async def pool(ctx):
    pick = pyrandom.sample(all_subs_pool, min(10, len(all_subs_pool)))
    await ctx.send("🎲 Random pool: " + ", ".join(pick))

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts: {post_counter} | Uptime: {uptime} | Version: {version}")

@client.command()
async def search(ctx, *, query: str):
    parts = query.split()
    content_type = "any"
    if parts[-1].lower() in ["img", "gif", "vid"]:
        content_type = parts[-1].lower()
        query = " ".join(parts[:-1])

    await ctx.send(f"🔎 Searching '{query}' ({content_type})...")

    collected = []

    # Case 1: Subreddit search
    try:
        subreddit = reddit.subreddit(query)
        for post in subreddit.hot(limit=100):
            if not post.over_18 or post.stickied:
                continue
            if getattr(post, "is_gallery", False) or filter_url(str(post.url), content_type):
                collected.append(post)
                if len(collected) >= 10:
                    break
        if collected:
            await ctx.send(f"✅ Found {len(collected)} posts in r/{query}:")
            for item in collected:
                await send_with_gallery_support(ctx.channel, item)
            return
    except Exception as e:
        print(f"[Subreddit Search Error] {e}")

    # Case 2: Keyword search
    try:
        results = reddit.subreddit("all").hot(limit=300)
        for post in results:
            if not post.over_18 or post.stickied:
                continue
            if query.lower() in post.title.lower() or query.lower() in post.subreddit.display_name.lower():
                if getattr(post, "is_gallery", False) or filter_url(str(post.url), content_type):
                    collected.append(post)
                    if len(collected) >= 10:
                        break
    except Exception as e:
        print(f"[Keyword Search Error] {e}")

    if collected:
        await ctx.send(f"✅ Found {len(collected)} results for '{query}':")
        for item in collected:
            await send_with_gallery_support(ctx.channel, item)
    else:
        await ctx.send(f"❌ No results for '{query}'")

# --- Startup ---
@client.event
async def on_ready():
    print(f"[READY] Logged in as {client.user} ({version})")
    await client.change_presence(activity=discord.Game(name="!search boobs"))

# --- Keepalive ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def ping_render():
    while True:
        try:
            requests.get(service_url)
            print("[PING] Sent keepalive")
        except Exception as e:
            print(f"[PING ERROR] {e}")
        time.sleep(300)

threading.Thread(target=run_web).start()
threading.Thread(target=ping_render).start()

# --- Run ---
client.run(user_token)
    
