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

# --- Random seed ---
pyrandom.seed(os.getpid() ^ int(time.time() * 1000000))
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v6.2-auto-dualsub-autosub-nextskip-nsfwsearch-redgifs'
start_time = datetime.now(timezone.utc)
post_counter = 0
seen_posts = set()

# --- Discord Env ---
user_token = os.getenv("user_token")
service_url = os.getenv("SERVICE_URL") or "https://working-1-uy7j.onrender.com"

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

# --- Load pools ---
try:
    with open("pools.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        nsfw_pool = data.get("nsfw_pool", [])
        hentai_pool = data.get("hentai_pool", [])
except Exception as e:
    print(f"[ERROR] Could not load pools.json: {e}")
    nsfw_pool, hentai_pool = [], []

all_subs_pool = nsfw_pool + hentai_pool

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

client = commands.Bot(command_prefix="!")

# --- Fuzzy correction ---
def correct_subreddit(sub_name):
    match, score, _ = process.extractOne(sub_name, all_subs_pool, scorer=fuzz.ratio)
    if score >= 70:
        print(f"[Fuzzy] Corrected '{sub_name}' -> '{match}'")
        return match
    return sub_name

# --- Iterator cache ---
sub_iterators = {}

def get_sub_iterator(sub_name, fetch_method):
    key = f"{sub_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        sub_iterators[key] = iter(getattr(reddit.subreddit(sub_name), fetch_method)(limit=None))
    return sub_iterators[key]

# --- Fetch posts ---
def get_filtered_posts(sub_name, content_type, fetch_method=None, batch_size=25):
    global seen_posts
    posts = []
    sub_name = correct_subreddit(sub_name)
    fetch_method = fetch_method or pyrandom.choice(["hot", "new", "top"])
    try:
        iterator = get_sub_iterator(sub_name, fetch_method)
        while len(posts) < batch_size:
            try:
                post = next(iterator)
            except StopIteration:
                sub_iterators[f"{sub_name}:{fetch_method}"] = None
                break
            if post.stickied:
                continue
            url = str(post.url)

            # Gallery
            if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                gallery_urls = []
                for item in post.gallery_data["items"][:25]:
                    media = post.media_metadata.get(item["media_id"])
                    if media and "s" in media and "u" in media["s"]:
                        gallery_urls.append(html.unescape(media["s"]["u"]))
                if gallery_urls:
                    posts.append(gallery_urls)
                continue

            # Imgur cleanup
            if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                continue
            if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                url += ".jpg"

            # Filter type
            if ((content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url)) or
                (content_type == "gif" and (url.endswith(".gif") or "redgifs" in url or "gfycat" in url)) or
                (content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url or "redgifs" in url))):
                if url not in seen_posts:
                    posts.append(url)
        if posts:
            flat = []
            for p in posts:
                flat.append(p)
                if not isinstance(p, list):
                    seen_posts.add(p)
            posts = flat
            if len(seen_posts) > 5000:
                seen_posts.clear()
    except Exception as e:
        print(f"[Reddit Error] r/{sub_name}: {e}")
    return posts

# --- Auto system ---
auto_tasks = {}
skip_flags = {}
pause_flags = {}
next_flags = {}

async def safe_send(channel, url):
    try:
        await channel.send(url)
    except:
        pass

async def send_with_gallery(channel, item):
    global post_counter
    if isinstance(item, list):
        for u in item:
            await safe_send(channel, u)
            post_counter += 1
            await asyncio.sleep(0.5)
    else:
        await safe_send(channel, item)
        post_counter += 1

# --- NSFW Search with RedGifs fallback ---
def search_redgifs(query, limit=5):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(f"https://api.redgifs.com/v2/gifs/search?search_text={query}&count={limit}", headers=headers)
        data = r.json()
        urls = []
        for gif in data.get("gifs", []):
            urls.append(gif.get("urls", {}).get("hd") or gif.get("urls", {}).get("sd"))
        return [u for u in urls if u]
    except:
        return []

@client.command()
async def nsfwsearch(ctx, *, query: str):
    await ctx.send(f"🔍 Searching NSFW for `{query}`...")
    try:
        results = list(reddit.subreddit("all").search(query, sort="relevance", limit=50))
        pyrandom.shuffle(results)
        found = 0
        for post in results:
            if found >= 3:
                break
            if not post.over_18:
                continue
            url = str(post.url)
            if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                gallery_urls = []
                for item in post.gallery_data["items"][:25]:
                    media = post.media_metadata.get(item["media_id"])
                    if media and "s" in media and "u" in media["s"]:
                        gallery_urls.append(html.unescape(media["s"]["u"]))
                if gallery_urls:
                    await send_with_gallery(ctx.channel, gallery_urls)
                    found += 1
            elif any(x in url for x in [".jpg",".png",".gif",".mp4","redgifs","v.redd.it"]):
                await safe_send(ctx.channel, url)
                found += 1
        if found == 0:
            await ctx.send("❌ No Reddit results found, trying RedGifs...")
            rg_results = search_redgifs(query, limit=5)
            if rg_results:
                for u in rg_results:
                    await safe_send(ctx.channel, u)
                await ctx.send(f"✅ Found {len(rg_results)} results on RedGifs.")
            else:
                await ctx.send("❌ No NSFW results found anywhere.")
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

# --- Auto ---
@client.command()
async def auto(ctx, seconds: int = 5, pool_name: str = "both", content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    pool = nsfw_pool if pool_name=="nsfw" else hentai_pool if pool_name=="hentai" else nsfw_pool+hentai_pool
    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False
    next_flags[ctx.channel.id] = False

    async def loop(channel):
        while True:
            subs = pyrandom.sample(pool, 2) if len(pool)>=2 else [pyrandom.choice(pool)]
            await channel.send(f"🎲 Now playing: {', '.join(subs)}")
            for i, sub in enumerate(subs):
                posts = get_filtered_posts(sub, content_type)
                if not posts:
                    continue
                await channel.send(f"▶ r/{sub}")
                for p in posts:
                    if skip_flags.get(channel.id) or next_flags.get(channel.id):
                        break
                    while pause_flags.get(channel.id, False):
                        await asyncio.sleep(1)
                    await send_with_gallery(channel, p)
                    await asyncio.sleep(seconds)
                if skip_flags.get(channel.id):
                    skip_flags[ctx.channel.id] = False
                    break
                if next_flags.get(channel.id):
                    next_flags[ctx.channel.id] = False
                    break

    task = asyncio.create_task(loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started ({pool_name} pool, dual-sub).")

# --- AutoSub ---
@client.command()
async def autosub(ctx, sub1: str, sub2: str = None, seconds: int = 5, content_type: str = "img"):
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False
    next_flags[ctx.channel.id] = False

    async def loop(channel):
        subs = [sub1] if not sub2 else [sub1, sub2]
        while True:
            for sub in subs:
                posts = get_filtered_posts(sub, content_type)
                if not posts:
                    await channel.send(f"❌ No posts found for r/{sub}")
                    continue
                await channel.send(f"▶ Now playing r/{sub}")
                for p in posts:
                    if skip_flags.get(channel.id) or next_flags.get(channel.id):
                        break
                    while pause_flags.get(channel.id, False):
                        await asyncio.sleep(1)
                    await send_with_gallery(channel, p)
                    await asyncio.sleep(seconds)
                if skip_flags.get(channel.id):
                    skip_flags[ctx.channel.id] = False
                    break
                if next_flags.get(channel.id):
                    next_flags[ctx.channel.id] = False
                    break

    task = asyncio.create_task(loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ AutoSub started for r/{sub1}" + (f" + r/{sub2}" if sub2 else "") + f" every {seconds}s.")

# --- Controls ---
@client.command()
async def pause(ctx):
    pause_flags[ctx.channel.id] = True
    await ctx.send("⏸️ Paused.")

@client.command()
async def resume(ctx):
    pause_flags[ctx.channel.id] = False
    await ctx.send("▶️ Resumed.")

@client.command()
async def skip(ctx):
    skip_flags[ctx.channel.id] = True
    await ctx.send("⏭ Skipping to new random subs...")

@client.command()
async def next(ctx):
    next_flags[ctx.channel.id] = True
    await ctx.send("⏭ Moving to next sub in current pair...")

@client.command()
async def autostop(ctx):
    if ctx.channel.id in auto_tasks:
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running.")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

# --- Keepalive ---
app = Flask("")

@app.route("/")
def home():
    return "Bot alive."

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

client.run(user_token)
    
