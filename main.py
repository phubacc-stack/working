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

version = 'v5.4-auto-pool-fullwalk+newNSFW'
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

# --------------------------
# Reddit Helpers (unchanged)
# --------------------------
def correct_subreddit(subreddit_name):
    match, score, _ = process.extractOne(subreddit_name, all_subs_pool, scorer=fuzz.ratio)
    if score >= 70:
        print(f"[Fuzzy] Corrected '{subreddit_name}' -> '{match}'")
        return match
    return subreddit_name

sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        listings = getattr(subreddit, fetch_method)(limit=None)
        sub_iterators[key] = iter(listings)
    return sub_iterators[key]

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
            url = str(post.url)

            if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                gallery_urls = []
                sorted_items = sorted(post.media_metadata.items(), key=lambda x: x[1]["s"]["u"])  
                for _, item in sorted_items[:25]:
                    if "s" in item and "u" in item["s"]:
                        gallery_url = html.unescape(item["s"]["u"])
                        if gallery_url not in seen_posts:
                            gallery_urls.append(gallery_url)
                if gallery_urls:
                    posts.append(gallery_urls)
                continue

            if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                continue
            if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                url += ".jpg"

            if (
                (content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url))
                or (content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")))
                or (content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url or "redgifs" in url))
            ):
                if url not in seen_posts:
                    posts.append(url)

        if posts:
            flat = []
            for p in posts:
                if isinstance(p, list):
                    flat.extend(p)
                    for url in p:
                        seen_posts.add(url)
                else:
                    flat.append(p)
                    seen_posts.add(p)
            posts = flat
            if len(seen_posts) > 5000:
                seen_posts.clear()

    except Exception as e:
        print(f"[Reddit Error] r/{subreddit_name}: {e}")

    print(f"[Fetched] r/{subreddit_name} -> {len(posts)} posts")
    return posts

# --------------------------
# Auto system for Reddit
# --------------------------
auto_tasks = {}
skip_flags = {}

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

# --------------------------
# Reddit Commands
# --------------------------
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
async def autosub(ctx, subreddit: str, seconds: int = 5, content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be img | gif | vid | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False

    async def auto_loop(channel):
        ctype = content_type
        if content_type == "random":
            ctype = pyrandom.choice(["img", "gif", "vid"])
        await channel.send(f"▶ Now playing from r/{subreddit}")

        while True:
            try:
                posts = get_filtered_posts(subreddit, ctype, batch_size=50)
                if not posts:
                    await asyncio.sleep(seconds)
                    continue

                for post in posts:
                    if skip_flags[ctx.channel.id]:
                        skip_flags[ctx.channel.id] = False
                        break
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
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be img | gif | vid | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False

    if pool_name=="nsfw":
        pool = nsfw_pool
    elif pool_name=="hentai":
        pool = hentai_pool
    else:
        pool = nsfw_pool + hentai_pool

    async def auto_loop(channel):
        shuffled_pool = pool.copy()
        pyrandom.shuffle(shuffled_pool)
        sub_index = 0

        while True:
            try:
                if sub_index >= len(shuffled_pool):
                    sub_index = 0
                    pyrandom.shuffle(shuffled_pool)

                sub = shuffled_pool[sub_index]
                ctype = pyrandom.choice(["img","gif","vid"]) if content_type=="random" else content_type

                await channel.send(f"▶ Now playing from r/{sub}")

                posts = get_filtered_posts(sub, ctype, batch_size=50)
                if not posts:
                    sub_index += 1
                    continue

                for post in posts:
                    if skip_flags[ctx.channel.id]:
                        skip_flags[ctx.channel.id] = False
                        break
                    await send_with_gallery_support(channel, post)
                    await asyncio.sleep(seconds)

                sub_index += 1

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

# --------------------------
# New NSFW Sources Helpers
# --------------------------
async def fetch_rule34(tag=""):
    try:
        url = f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags={tag}"
        r = requests.get(url, timeout=10).json()
        if not r:
            return []
        return [p["file_url"] for p in r if "file_url" in p]
    except:
        return []

async def fetch_e621(tag=""):
    try:
        url = f"https://e621.net/posts.json?limit=100&tags={tag}"
        headers = {"User-Agent": "DiscordNSFWBot/1.0"}
        r = requests.get(url, headers=headers, timeout=10).json()
        posts = r.get("posts", [])
        return [p["file"]["url"] for p in posts if "file" in p and "url" in p["file"]]
    except:
        return []

async def fetch_coomer(tag=""):
    try:
        url = f"https://api.coomer.party/gallery/random?tags={tag}"
        r = requests.get(url, timeout=10).json()
        return [p["file_url"] for p in r]
    except:
        return []

async def fetch_kemono(tag=""):
    try:
        url = f"https://kemono.party/api/v1/posts?search={tag}"
        r = requests.get(url, timeout=10).json()
        return [p["url"] for p in r.get("data", [])]
    except:
        return []

# --------------------------
# New NSFW Commands
# --------------------------
async def send_source_posts(ctx, source_name, fetch_func, tag=""):
    posts = await fetch_func(tag)
    if not posts:
        await ctx.send(f"❌ No posts found on {source_name} for `{tag}`")
        return
    await ctx.send(f"▶ Source: {source_name}")
    for url in posts[:10]:
        await send_with_gallery_support(ctx.channel, url)

@client.command()
async def rule34(ctx, *, tag=""):
    await send_source_posts(ctx, "Rule34", fetch_rule34, tag)

@client.command()
async def e621(ctx, *, tag=""):
    await send_source_posts(ctx, "e621", fetch_e621, tag)

@client.command()
async def coomer(ctx, *, tag=""):
    await send_source_posts(ctx, "Coomer", fetch_coomer, tag)

@client.command()
async def kemono(ctx, *, tag=""):
    await send_source_posts(ctx, "Kemono", fetch_kemono, tag)

# --------------------------
# New NSFW Auto (Randomized from all 4 sources)
# --------------------------
new_auto_tasks = {}
new_skip_flags = {}

@client.command()
async def auto_new(ctx, seconds: int = 5, tag: str = ""):
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if ctx.channel.id in new_auto_tasks and not new_auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    new_skip_flags[ctx.channel.id] = False
    sources = [
        ("Rule34", fetch_rule34),
        ("e621", fetch_e621),
        ("Coomer", fetch_coomer),
        ("Kemono", fetch_kemono)
    ]

    async def auto_loop(channel):
        while True:
            try:
                source_name, fetch_func = pyrandom.choice(sources)
                posts = await fetch_func(tag)
                if not posts:
                    await asyncio.sleep(seconds)
                    continue
                await channel.send(f"▶ Source: {source_name}")
                for url in posts[:10]:
                    if new_skip_flags[ctx.channel.id]:
                        new_skip_flags[ctx.channel.id] = False
                        break
                    await send_with_gallery_support(channel, url)
                    await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[New Auto Error] {e}")
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    new_auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto_new started pulling from all sources every {seconds}s.")

# --------------------------
# Keepalive Pin
# --------------------------
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

# --------------------------
# Run Bot
# --------------------------
client.run(user_token)
