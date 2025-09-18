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
import logging

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v8.1-full-feature'
start_time = datetime.now(timezone.utc)
post_counter = 0
seen_posts = set()
AUTOS_FILE = "autos.json"

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)
if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"

# --- Reddit API setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

# Initialize the bot without intents
client = commands.Bot(command_prefix="!", help_command=None)

# --- Pools from GitHub ---
POOLS_URL = "https://raw.githubusercontent.com/phubacc-stack/working/8ce06d533b0ba820fedd0001368215a3d42fff29/pools.json"

nsfw_pool, hentai_pool = [], []

def load_pools():
    global nsfw_pool, hentai_pool
    try:
        r = requests.get(POOLS_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        nsfw_pool = data.get("nsfw_pool", ["exampleNSFW1"])
        hentai_pool = data.get("hentai_pool", ["exampleHentai1"])
        logging.info(f"[Pools] Loaded {len(nsfw_pool)} NSFW and {len(hentai_pool)} Hentai subs.")
    except Exception as e:
        logging.warning(f"[Pools] Failed to load from GitHub, using placeholders: {e}")
        nsfw_pool = ["exampleNSFW1"]
        hentai_pool = ["exampleHentai1"]

load_pools()

# --- Persistent autos ---
if os.path.exists(AUTOS_FILE):
    with open(AUTOS_FILE, "r") as f:
        auto_tasks_data = json.load(f)
else:
    auto_tasks_data = {}

auto_tasks = {}

def save_autos():
    data = {}
    for cid, info in auto_tasks.items():
        data[str(cid)] = {
            "paused": info.get("paused", False),
            "type": info.get("type", "img"),
            "subreddit": info.get("subreddit", ""),
            "delay": info.get("delay", 30),
            "only_collections": info.get("only_collections", False)
        }
    with open(AUTOS_FILE, "w") as f:
        json.dump(data, f)

# --- Reddit Helpers ---
def get_filtered_posts(subreddit_name, content_type, only_collections=False, fetch_mode=None, search_term=None):
    global seen_posts
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        fetch_method = fetch_mode or pyrandom.choice(["hot", "new", "top"])
        listings = getattr(subreddit, fetch_method)(limit=100)

        for post in listings:
            if post.stickied: continue
            url = str(post.url)

            # Search filtering
            if search_term and search_term.lower() not in post.title.lower(): continue

            # Collections only
            if only_collections and "reddit.com/gallery" not in url: continue

            # Gallery handling
            if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                gallery_urls = []
                for item in list(post.media_metadata.values())[:25]:
                    if "s" in item and "u" in item["s"]:
                        gallery_url = html.unescape(item["s"]["u"])
                        if gallery_url not in seen_posts:
                            gallery_urls.append(gallery_url)
                if gallery_urls: posts.append(gallery_urls)
                continue

            # Skip imgur albums
            if "imgur.com/a/" in url or "imgur.com/gallery/" in url: continue
            if "imgur.com" in url and not url.endswith((".jpg",".png",".gif")): url += ".jpg"

            if ((content_type=="img" and (url.endswith((".jpg",".jpeg",".png")) or "i.redd.it" in url))
                or (content_type=="gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")))
                or (content_type=="vid" and (url.endswith(".mp4") or "v.redd.it" in url))):
                if url not in seen_posts: posts.append(url)

        if posts:
            pyrandom.shuffle(posts)
            flat = []
            for p in posts:
                if isinstance(p,list): flat.append(p)
                else: flat.append(p); seen_posts.add(p)
            posts = flat
            if len(seen_posts)>5000: seen_posts.clear()
    except Exception as e:
        logging.error(f"[Reddit Error] r/{subreddit_name}: {e}")
    return posts

async def safe_send(channel, url):
    try: await channel.send(url)
    except Exception as e: logging.error(f"[Discord Error] Failed to send: {e}")

async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item,list):
        for url in item:
            await safe_send(channel,url)
            post_counter +=1
            await asyncio.sleep(2)
    else:
        await safe_send(channel,item)
        post_counter +=1

# --- Auto loop ---
async def auto_loop(channel_id):
    info = auto_tasks[channel_id]
    sent_posts = set()
    while True:
        try:
            # Log paused state
            logging.info(f"[AutoLoop] Channel {channel_id} - paused state: {info.get('paused')}")

            if info.get("paused"):
                logging.info(f"[AutoLoop] Channel {channel_id} is paused. Waiting...")
                await asyncio.sleep(3)
                continue
            subreddit = info.get("subreddit") or pyrandom.choice(nsfw_pool+hentai_pool)
            content_type = info.get("type","img")
            only_collections = info.get("only_collections",False)
            delay = info.get("delay",30)
            fetch_mode = pyrandom.choice(["hot","new","top"])
            search_term = info.get("search_term")
            posts = get_filtered_posts(subreddit, content_type, only_collections, fetch_mode, search_term)
            for item in posts:
                if isinstance(item,list):
                    new_urls=[u for u in item if u not in sent_posts]
                    if new_urls:
                        await send_with_gallery_support(client.get_channel(channel_id), new_urls)
                        sent_posts.update(new_urls)
                else:
                    if item not in sent_posts:
                        await send_with_gallery_support(client.get_channel(channel_id), item)
                        sent_posts.add(item)
            await asyncio.sleep(delay)
        except asyncio.CancelledError: break
        except Exception as e: logging.error(f"[AutoLoop Error] {e}"); await asyncio.sleep(5)

def start_auto(channel_id, subreddit="", content_type="img", delay=30, only_collections=False, search_term=None):
    if channel_id in auto_tasks:
        if auto_tasks[channel_id]["task"].done():
            logging.info(f"[StartAuto] Task for channel {channel_id} already done, skipping cancel.")
        else:
            auto_tasks[channel_id]["task"].cancel()
            logging.info(f"[StartAuto] Canceled previous task for channel {channel_id}.")
    auto_tasks[channel_id] = {
        "task": asyncio.create_task(auto_loop(channel_id)),
        "paused": False,
        "type": content_type,
        "subreddit": subreddit,
        "delay": delay,
        "only_collections": only_collections,
        "search_term": search_term
    }
    save_autos()
    return auto_tasks[channel_id]["task"]

# --- Commands ---
@client.command()
async def r(ctx, amount:int=1, content_type:str="img"):
    if amount>50: amount=50
    pool = nsfw_pool+hentai_pool
    collected, tries, max_tries = [],0,amount*3
    while len(collected)<amount and tries<max_tries:
        sub = pyrandom.choice(pool)
        posts = get_filtered_posts(sub, content_type)
        for url in posts:
            if len(collected)>=amount: break
            collected.append(url)
        tries+=1
    if collected:
        for item in collected: await send_with_gallery_support(ctx.channel,item)
    else: await ctx.send("❌ No posts found.")

@client.command()
async def rsub(ctx, subreddit:str, amount:int=1, content_type:str="img"):
    if amount>50: amount=50
    collected, tries, max_tries = [],0,amount*3
    while len(collected)<amount and tries<max_tries:
        posts = get_filtered_posts(subreddit, content_type)
        for url in posts:
            if len(collected)>=amount: break
            collected.append(url)
        tries+=1
    if collected:
        for item in collected: await send_with_gallery_support(ctx.channel,item)
    else: await ctx.send("❌ No posts found.")

@client.command()
async def autosub(ctx, subreddit:str, seconds:int=30, content_type:str="img"):
    start_auto(ctx.channel.id, subreddit=subreddit, content_type=content_type, delay=seconds)
    msg = await ctx.send(f"▶️ AutoSub started: r/{subreddit} every {seconds}s for {content_type}. Use reactions to control.")
    for r in ["⏸️","▶️","⏹️","🖼️","🎥","🎬","🔀","ℹ️"]: await msg.add_reaction(r)

# --- Reaction Controls ---
@client.event
async def on_reaction_add(reaction,user):
    if user.bot: return
    channel_id = reaction.message.channel.id
    if channel_id not in auto_tasks: return
    info = auto_tasks[channel_id]
    emoji = str(reaction.emoji)
    if emoji=="⏸️": info["paused"]=True; await reaction.message.channel.send("⏸️ Auto paused.")
    elif emoji=="▶️": info["paused"]=False; await reaction.message.channel.send("▶️ Auto resumed.")
    elif emoji=="⏹️": info["task"].cancel(); auto_tasks.pop(channel_id,None); await reaction.message.channel.send("⏹️ Auto stopped.")
    elif emoji=="🖼️": info["type"]="img"; await reaction.message.channel.send("🖼️ Type set to IMG.")
    elif emoji=="🎬": info["type"]="gif"; await reaction.message.channel.send("🎬 Type set to GIF.")
    elif emoji=="🎥": info["type"]="vid"; await reaction.message.channel.send("🎥 Type set to VID.")
    elif emoji=="🔀": info["type"]="random"; await reaction.message.channel.send("🔀 Type set to RANDOM.")
    elif emoji=="ℹ️": await reaction.message.channel.send(f"ℹ️ Auto status:\nSubreddit: {info.get('subreddit')}\nType: {info.get('type')}\nPaused: {info.get('paused')}\nDelay: {info.get('delay')}s\nCollections Only: {info.get('only_collections')}\nSearch: {info.get('search_term')}")
    save_autos()

# --- Keepalive Flask ---
app = Flask("")
@app.route("/")
def home(): return "Bot is alive."
def run():
    app.run(host="0.0.0.0", port=8080)
def ping():
    while True:
        try: requests.get(service_url)
        except: pass
        time.sleep(600)
threading.Thread(target=run).start()
threading.Thread(target=ping,daemon=True).start()

# --- Run Bot ---
client.run(user_token)
