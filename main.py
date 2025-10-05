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

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.6-auto-pool-random3'
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

# --- Iterator cache ---
sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        listings = getattr(subreddit, fetch_method)(limit=None)
        sub_iterators[key] = iter(listings)
    return sub_iterators[key]

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

            if post.stickied:
                continue
            url = str(post.url)

            # Handle galleries
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

            # Ignore Imgur albums
            if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                continue
            if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                url += ".jpg"

            # Filter
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
                    flat.append(p)
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
    pause_flags[ctx.channel.id] = False

    async def auto_loop(channel):
        while True:
            try:
                ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type=="random" else content_type
                posts = get_filtered_posts(subreddit, ctype)
                if not posts:
                    await channel.send(f"❌ No posts found for r/{subreddit}.")
                    return
                await channel.send(f"▶ Now playing from r/{subreddit}")
                for post in posts:
                    while pause_flags.get(channel.id, False):
                        await asyncio.sleep(1)
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
    if pool_name not in ["nsfw", "hentai", "both", "random"]:
        await ctx.send("⚠️ Pool must be nsfw | hentai | both | random.")
        return
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be img | gif | vid | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False

    if pool_name == "nsfw":
        pool = nsfw_pool
    elif pool_name == "hentai":
        pool = hentai_pool
    else:
        pool = nsfw_pool + hentai_pool

    async def auto_loop(channel):
        while True:
            try:
                if pool_name == "random":
                    chosen_subs = pyrandom.sample(pool, min(3, len(pool)))
                    for sub in chosen_subs:
                        ctype = pyrandom.choice(["img","gif","vid"]) if content_type=="random" else content_type
                        posts = get_filtered_posts(sub, ctype, batch_size=30)
                        if not posts:
                            continue
                        selected = pyrandom.sample(posts, min(15, len(posts)))
                        await channel.send(f"🎲 Random mode → r/{sub}")
                        for post in selected:
                            while pause_flags.get(channel.id, False):
                                await asyncio.sleep(1)
                            if skip_flags[ctx.channel.id]:
                                skip_flags[ctx.channel.id] = False
                                break
                            await send_with_gallery_support(channel, post)
                            await asyncio.sleep(seconds)
                else:
                    sub = pyrandom.choice(pool)
                    ctype = pyrandom.choice(["img","gif","vid"]) if content_type=="random" else content_type
                    posts = get_filtered_posts(sub, ctype)
                    if not posts:
                        continue
                    await channel.send(f"▶ Now playing from r/{sub}")
                    for post in posts:
                        while pause_flags.get(channel.id, False):
                            await asyncio.sleep(1)
                        if skip_flags[ctx.channel.id]:
                            skip_flags[ctx.channel.id] = False
                            break
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
async def pause(ctx):
    if ctx.channel.id not in auto_tasks or auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ No auto running here.")
        return
    pause_flags[ctx.channel.id] = True
    await ctx.send("⏸️ Auto paused.")

@client.command()
async def resume(ctx):
    if ctx.channel.id not in auto_tasks or auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ No auto running here.")
        return
    if not pause_flags.get(ctx.channel.id, False):
        await ctx.send("⚠️ Auto is not paused.")
        return
    pause_flags[ctx.channel.id] = False
    await ctx.send("▶️ Auto resumed.")

@client.command()
async def pool(ctx, pool_name: str = "both", amount: int = 5):
    if pool_name not in ["nsfw", "hentai", "both"]:
        await ctx.send("⚠️ Pool must be nsfw | hentai | both.")
        return
    if pool_name == "nsfw":
        pool = nsfw_pool
    elif pool_name == "hentai":
        pool = hentai_pool
    else:
        pool = nsfw_pool + hentai_pool

    if not pool:
        await ctx.send("⚠️ Pool is empty.")
        return

    picks = pyrandom.sample(pool, min(amount, len(pool)))
    await ctx.send(f"🎲 Random from {pool_name} pool:\n" + ", ".join([f"r/{p}" for p in picks]))

# --- UPDATED SEARCH COMMAND ---
@client.command()
async def search(ctx, *args, amount: int = 5, content_type: str = "img"):
    """
    Search Reddit with multi-word query.
    Usage: !search keyword1 keyword2 ... [amount] [content_type]
    """
    if not args:
        await ctx.send("⚠️ Please provide search keywords.")
        return

    # Extract keywords (all arguments except last two if they are numbers/type)
    keywords = list(args)
    try:
        if args[-1].isdigit():
            amount = int(args[-1])
            keywords = keywords[:-1]
        if args[-2] in ["img", "gif", "vid", "random"]:
            content_type = args[-2]
            keywords = keywords[:-1]
    except:
        pass

    query = " ".join(keywords)
    await ctx.send(f"🔎 Searching Reddit for: **{query}**")

    collected = []
    try:
        results = reddit.subreddit("all").search(query, sort="relevance", limit=50)
        for post in results:
            url = str(post.url)
            if post.stickied:
                continue

            if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                continue
            if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                url += ".jpg"

            if (
                content_type == "img" and url.endswith((".jpg", ".jpeg", ".png"))
            ) or (
                content_type == "gif" and (url.endswith(".gif") or "redgifs" in url)
            ) or (
                content_type == "vid" and ("v.redd.it" in url or url.endswith(".mp4"))
            ) or (
                content_type == "random" and url.endswith((".jpg",".jpeg",".png",".gif",".gifv",".mp4")) or "v.redd.it" in url or "redgifs" in url
            ):
                collected.append(url)

            if len(collected) >= amount:
                break
    except Exception as e:
        print(f"[Search Error] {e}")

    if collected:
        for item in collected:
            await send_with_gallery_support(ctx.channel, item)
    else:
        await ctx.send(f"❌ No results found for query: {query}")

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
                                                          
