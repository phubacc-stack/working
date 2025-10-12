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

version = 'v5.6-auto-pool-fullwalk-r34fix'
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

# --- Auto system ---
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

# --- Reddit Commands ---
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

# (Reddit autos remain unchanged here for brevity – same as before)

# --- Rule34 Commands (Fixed + Fullwalk) ---
@client.command()
async def r34(ctx, *, tags: str):
    tags = tags.replace(" ", "_")
    headers = {"User-Agent": "Mozilla/5.0 (DiscordBot)"}
    urls = [
        f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={tags}",
        f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={tags}"
    ]

    response_data = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, list):
                        response_data = [item.get("file_url") for item in data if isinstance(item, dict) and item.get("file_url")]
                        if response_data:
                            break
                except Exception as je:
                    print(f"[Rule34 JSON Error] {je}")
        except Exception as e:
            print(f"[Rule34 Fetch Error] {e}")

    if not response_data:
        await ctx.send(f"❌ No posts found for `{tags}`.")
        return

    for post_url in response_data:
        await send_with_gallery_support(ctx.channel, post_url)
        await asyncio.sleep(1)

@client.command()
async def auto_r34(ctx, seconds: int = 5, *, tags_list: str):
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if not tags_list.strip():
        await ctx.send("❌ You must provide at least one tag.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    tags_pool = [tag.strip().replace(" ", "_") for tag in tags_list.split(",") if tag.strip()]
    headers = {"User-Agent": "Mozilla/5.0 (DiscordBot)"}

    async def auto_loop(channel):
        await channel.send(f"▶ Now auto posting Rule34 from {len(tags_pool)} tag sets")
        tag_iter = 0

        while True:
            try:
                tag_query = tags_pool[tag_iter]
                urls = [
                    f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={tag_query}",
                    f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={tag_query}"
                ]
                response_data = []

                for url in urls:
                    try:
                        r = requests.get(url, headers=headers, timeout=10)
                        if r.status_code == 200:
                            try:
                                data = r.json()
                                if isinstance(data, list):
                                    response_data = [item.get("file_url") for item in data if isinstance(item, dict) and item.get("file_url")]
                                    if response_data:
                                        break
                            except Exception as je:
                                print(f"[Rule34 JSON Error] {je}")
                    except Exception as e:
                        print(f"[Rule34 Fetch Error] {e}")

                if response_data:
                    for post_url in response_data:
                        if skip_flags[ctx.channel.id]:
                            skip_flags[ctx.channel.id] = False
                            break
                        await send_with_gallery_support(channel, post_url)
                        await asyncio.sleep(1)
                else:
                    print(f"[Rule34] No posts found for: {tag_query}")

                tag_iter += 1
                if tag_iter >= len(tags_pool):
                    tag_iter = 0

                await asyncio.sleep(seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Auto_R34 Error] {e}")
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto_R34 started for {len(tags_pool)} tag sets every {seconds}s.")

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
    
