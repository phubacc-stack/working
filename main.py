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
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v7.1-full'
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

# --- Reddit API ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    username="phubacc-stack",
    password="Mypassword123!",
    user_agent="NsfwDiscordBot/1.0"
)

client = commands.Bot(command_prefix="!")

# --- Fuzzy correction ---
def correct_subreddit(subreddit_name):
    try:
        match, score, _ = process.extractOne(subreddit_name, all_subs_pool, scorer=fuzz.ratio)
        if score >= 70:
            print(f"[Fuzzy] Corrected '{subreddit_name}' -> '{match}'")
            return match
    except Exception:
        pass
    return subreddit_name

# --- Iterator cache ---
sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method="new"):
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
def get_filtered_posts(subreddit_name, content_type, fetch_method="new", batch_size=25):
    global seen_posts
    posts = []
    subreddit_name = correct_subreddit(subreddit_name)
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

            if getattr(post, "is_gallery", False):
                if post.id not in seen_posts:
                    posts.append(post)
                    seen_posts.add(post.id)
            else:
                url = filter_url(str(post.url), content_type)
                if url and post.id not in seen_posts:
                    posts.append(post)
                    seen_posts.add(post.id)

        if len(seen_posts) > 5000:
            seen_posts.clear()

    except Exception as e:
        print(f"[Reddit Error] r/{subreddit_name}: {e}")

    print(f"[Fetched] r/{subreddit_name} -> {len(posts)} posts")
    return posts

# --- Send helpers ---
async def safe_send(channel, content):
    try:
        await channel.send(content)
    except Exception as e:
        print(f"[Discord Send Error] Channel {channel.id}: {e}")

async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item, praw.models.Submission) and getattr(item, "is_gallery", False):
        media = getattr(item, "media_metadata", {})
        gallery_items = getattr(item, "gallery_data", {}).get("items", [])
        for i in gallery_items:
            media_id = i["media_id"]
            url = media[media_id]["s"]["u"].replace("&amp;", "&")
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(2.5)
    else:
        await safe_send(channel, item if isinstance(item, str) else f"https://redd.it/{item.id}")
        post_counter += 1

# --- Auto state ---
auto_task = None
paused = False

@client.command()
async def auto(ctx):
    """Auto fetch from random pool sequentially"""
    global auto_task
    if auto_task and not auto_task.done():
        await ctx.send("⚠️ Auto is already running.")
        return

    async def run_auto():
        global paused
        while True:
            if paused:
                await asyncio.sleep(2)
                continue
            pool_choice = pyrandom.choice([nsfw_pool, hentai_pool])
            sub = pyrandom.choice(pool_choice)
            posts = get_filtered_posts(sub, "any", fetch_method="new", batch_size=3)
            for post in posts:
                await send_with_gallery_support(ctx.channel, post)
                await asyncio.sleep(5)
            await asyncio.sleep(10)

    auto_task = asyncio.create_task(run_auto())
    await ctx.send("▶️ Auto started.")

@client.command()
async def autosub(ctx, subreddit: str):
    """Auto fetch sequentially from a specific subreddit"""
    global auto_task
    if auto_task and not auto_task.done():
        await ctx.send("⚠️ Auto is already running.")
        return

    async def run_autosub():
        global paused
        subreddit_name = correct_subreddit(subreddit)
        while True:
            if paused:
                await asyncio.sleep(2)
                continue
            posts = get_filtered_posts(subreddit_name, "any", fetch_method="new", batch_size=3)
            for post in posts:
                await send_with_gallery_support(ctx.channel, post)
                await asyncio.sleep(5)
            await asyncio.sleep(10)

    auto_task = asyncio.create_task(run_autosub())
    await ctx.send(f"▶️ Auto started for r/{subreddit}")

@client.command()
async def stop(ctx):
    global auto_task
    if auto_task:
        auto_task.cancel()
        auto_task = None
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ Auto is not running.")

@client.command()
async def pause(ctx):
    global paused
    paused = True
    await ctx.send("⏸️ Auto paused.")

@client.command()
async def resume(ctx):
    global paused
    paused = False
    await ctx.send("▶️ Auto resumed.")

@client.command()
async def skip(ctx):
    global auto_task
    if auto_task and not auto_task.done():
        auto_task.cancel()
        auto_task = None
        await auto(ctx)
    else:
        await ctx.send("⚠️ Auto is not running.")

@client.command()
async def pool(ctx):
    pool_choice = pyrandom.choice([nsfw_pool, hentai_pool])
    sub = pyrandom.choice(pool_choice)
    await ctx.send(f"🎲 Random pool pick: r/{sub}")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Version: {version}\nPosts sent: {post_counter}\nUptime: {uptime}")

@client.command()
async def search(ctx, *, query: str):
    try:
        results = [p for p in reddit.subreddit("all").search(query, limit=10) if p.over_18]
        if not results:
            await ctx.send("❌ No results found.")
            return
        for post in results[:5]:
            if getattr(post, "is_gallery", False):
                await send_with_gallery_support(ctx.channel, post)
            else:
                await safe_send(ctx.channel, str(post.url))
    except Exception as e:
        await ctx.send(f"❌ Search error: {e}")

# --- Keepalive ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

# --- Run ---
keep_alive()
client.run(user_token)
    
