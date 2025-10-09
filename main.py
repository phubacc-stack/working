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
import html
from rapidfuzz import process, fuzz

# --- Ensure different randomness every bot run ---
pyrandom.seed(os.getpid() ^ int(time.time() * 1000000))

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.6-auto-pool-fullwalk-search-pause'
start_time = datetime.now(timezone.utc)
post_counter = 0
seen_posts = set()

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
service_url = os.getenv("SERVICE_URL") or "https://working-1-uy7j.onrender.com"

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

# --- Load pools from JSON ---
try:
    with open("pools.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        nsfw_pool = data.get("nsfw_pool", [])
        hentai_pool = data.get("hentai_pool", [])
except Exception as e:
    print(f"[ERROR] Could not load pools.json: {e}")
    nsfw_pool, hentai_pool = [], []

all_subs_pool = nsfw_pool + hentai_pool

# --- Reddit API setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

client = commands.Bot(command_prefix="!")

# --- Helper: Fuzzy subreddit correction ---
def correct_subreddit(subreddit_name):
    match, score, _ = process.extractOne(subreddit_name, all_subs_pool, scorer=fuzz.ratio)
    if score >= 70:
        print(f"[Fuzzy] Corrected '{subreddit_name}' -> '{match}'")
        return match
    return subreddit_name

# --- Iterator cache to walk through subs fully ---
sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        listings = getattr(subreddit, fetch_method)(limit=None)
        sub_iterators[key] = iter(listings)
    return sub_iterators[key]

# --- Helper: Filter URLs by type ---
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

# --- Helper: Get unique posts (walk through subreddit) ---
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
            if post.stickied:
                continue
            url = filter_url(str(post.url), content_type)
            if url and url not in seen_posts:
                posts.append(url)

        if posts:
            seen_posts.update(posts)
            if len(seen_posts) > 5000:
                seen_posts.clear()

    except Exception as e:
        print(f"[Reddit Error] r/{subreddit_name}: {e}")

    print(f"[Fetched] r/{subreddit_name} -> {len(posts)} posts")
    return posts

# --- Auto system ---
auto_tasks = {}
skip_flags = {}
pause_flags = {}

async def safe_send(channel, url):
    try:
        await channel.send(url)
    except Exception as e:
        print(f"[Discord Error] Failed to send: {e}")

async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item, list):
        for url in item:
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(1)
    else:
        await safe_send(channel, item)
        post_counter += 1

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    if amount > 50:
        amount = 50
    pool = nsfw_pool + hentai_pool
    collected = []
    tries = 0
    max_tries = amount * 3
    while len(collected) < amount and tries < max_tries:
        sub = pyrandom.choice(pool)
        posts = get_filtered_posts(sub, content_type)
        if posts:
            for url in posts:
                if len(collected) >= amount:
                    break
                collected.append(url)
        tries += 1
    if collected:
        for item in collected:
            await send_with_gallery_support(ctx.channel, item)
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def search(ctx, *, query: str):
    """Search Reddit NSFW/Hentai pools (and fallback to global) with optional content type."""
    parts = query.split()
    content_type = "any"
    if parts[-1].lower() in ["img", "gif", "vid"]:
        content_type = parts[-1].lower()
        query = " ".join(parts[:-1])

    pool = nsfw_pool + hentai_pool
    collected = []
    tries = 0
    max_tries = 10

    await ctx.send(f"🔎 Searching for '{query}' ({content_type})...")

    while len(collected) < 10 and tries < max_tries:
        sub = pyrandom.choice(pool)
        try:
            subreddit = reddit.subreddit(sub)
            results = subreddit.search(query, sort="relevance", time_filter="all", limit=15)
            for post in results:
                if post.over_18 and not post.stickied:
                    url = filter_url(str(post.url), content_type)
                    if url and url not in seen_posts:
                        collected.append(url)
                        seen_posts.add(url)
                        if len(collected) >= 10:
                            break
        except Exception as e:
            print(f"[Search Error] r/{sub}: {e}")
        tries += 1

    if not collected:
        try:
            await ctx.send("⚠️ Nothing in pools, searching all of Reddit...")
            results = reddit.subreddit("all").search(query, sort="relevance", time_filter="all", limit=20)
            for post in results:
                if post.over_18 and not post.stickied:
                    url = filter_url(str(post.url), content_type)
                    if url and url not in seen_posts:
                        collected.append(url)
                        seen_posts.add(url)
                        if len(collected) >= 10:
                            break
        except Exception as e:
            print(f"[Search Error Global] {e}")

    if collected:
        await ctx.send(f"✅ Found {len(collected)} results for '{query}':")
        for url in collected:
            await safe_send(ctx.channel, url)
    else:
        await ctx.send(f"❌ No results found for '{query}'.")

@client.command()
async def pool(ctx):
    """Show random sample of subs from pools."""
    sample = pyrandom.sample(all_subs_pool, min(10, len(all_subs_pool)))
    await ctx.send("🎲 Random subs:\n" + ", ".join(f"r/{s}" for s in sample))

@client.command()
async def pause(ctx):
    pause_flags[ctx.channel.id] = True
    await ctx.send("⏸️ Auto paused.")

@client.command()
async def resume(ctx):
    pause_flags[ctx.channel.id] = False
    await ctx.send("▶️ Auto resumed.")

@client.command()
async def autosub(ctx, subreddit: str, seconds: int = 5, content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random", "any"]:
        await ctx.send("⚠️ Type must be img | gif | vid | any | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False

    async def auto_loop(channel):
        while True:
            try:
                if pause_flags.get(ctx.channel.id):
                    await asyncio.sleep(2)
                    continue
                ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type=="random" else content_type
                posts = get_filtered_posts(subreddit, ctype)
                if not posts:
                    await channel.send(f"❌ No posts found for r/{subreddit}.")
                    return
                await channel.send(f"▶ Now playing from r/{subreddit}")
                for post in posts:
                    if skip_flags[ctx.channel.id]:
                        skip_flags[ctx.channel.id] = False
                        break
                    if pause_flags.get(ctx.channel.id):
                        while pause_flags.get(ctx.channel.id):
                            await asyncio.sleep(2)
                    await send_with_gallery_support(channel, post)
                    await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AutoSub Error] {e}")
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ AutoSub started for r/{subreddit} every {seconds}s for {content_type}.")

@client.command()
async def auto(ctx, seconds: int = 5, pool_name: str = "both", content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if pool_name not in ["nsfw", "hentai", "both"]:
        await ctx.send("⚠️ Pool must be nsfw | hentai | both.")
        return
    if content_type not in ["img", "gif", "vid", "random", "any"]:
        await ctx.send("⚠️ Type must be img | gif | vid | any | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False

    if pool_name=="nsfw":
        pool = nsfw_pool
    elif pool_name=="hentai":
        pool = hentai_pool
    else:
        pool = nsfw_pool + hentai_pool

    async def auto_loop(channel):
        while True:
            try:
                if pause_flags.get(ctx.channel.id):
                    await asyncio.sleep(2)
                    continue
                sub = pyrandom.choice(pool)
                ctype = pyrandom.choice(["img","gif","vid"]) if content_type=="random" else content_type
                posts = get_filtered_posts(sub, ctype)
                if not posts:
                    continue
                await channel.send(f"▶ Now playing from r/{sub}")
                for post in posts:
                    if skip_flags[ctx.channel.id]:
                        skip_flags[ctx.channel.id] = False
                        break
                    if pause_flags.get(ctx.channel.id):
                        while pause_flags.get(ctx.channel.id):
                            await asyncio.sleep(2)
                    await send_with_gallery_support(channel, post)
                    await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Auto Error] {e}")
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started for {pool_name} pool every {seconds}s for {content_type}.")

@client.command()
async def skip(ctx):
    if ctx.channel.id in skip_flags:
        skip_flags[ctx.channel.id] = True
        await ctx.send("⏭ Skipping current subreddit...")

@client.command()
async def autostop(ctx):
    if ctx.channel.id in auto_tasks:
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

# --- Keepalive Pin ---
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

threading.Thread(target=run).start()
threading.Thread(target=ping, daemon=True).start()

# --- Run Bot ---
client.run(user_token)
            
