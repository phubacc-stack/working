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
from rapidfuzz import process, fuzz

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v6.2-auto-pools-r'
start_time = datetime.now(timezone.utc)
post_counter = 0

# --- Flask server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# --- Discord setup ---
user_token = os.getenv("user_token")
bot = commands.Bot(command_prefix="!")

# --- Reddit setup with your credentials ---
reddit = praw.Reddit(
    client_id="FkQW0wCGFovtAw",
    client_secret="NGFVQ4u9RUJcJX9SpEhmLsAKmiCydQ",
    password="Justforthis69!",
    user_agent="Justforthis69!",
    username="Justforthis69"
)

# --- Load pools from pools.json ---
def load_pools():
    try:
        with open("pools.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load pools.json: {e}")
        return {"default": []}

POOLS = load_pools()

# --- Globals for auto mode ---
auto_running = False
auto_task = None
current_pool = []
current_index = 0

# --- Helper: send post ---
async def send_post(ctx, submission):
    global post_counter
    post_counter += 1
    title = html.unescape(submission.title)
    url = submission.url
    await ctx.send(f"**{title}**\n{url}")

# --- Helper: fetch posts from subreddit ---
def fetch_subreddit_posts(subreddit_name, limit=25):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        return list(subreddit.hot(limit=limit))
    except Exception as e:
        print(f"[ERROR] Failed fetching r/{subreddit_name}: {e}")
        return []

# --- Auto loop ---
async def auto_loop(ctx, subs):
    global current_index, auto_running
    auto_running = True

    while auto_running:
        if not subs:
            await ctx.send("⚠ No subreddits found in pool.")
            break

        sub = subs[current_index % len(subs)]

        # Announce subreddit
        await ctx.send(f"▶ Now playing from **r/{sub}**")

        posts = fetch_subreddit_posts(sub, limit=10)
        for submission in posts:
            if not auto_running:
                return
            await send_post(ctx, submission)
            await asyncio.sleep(5)

        # move to next subreddit
        current_index += 1

    await ctx.send("⏹ Auto stopped.")

# --- Commands ---
@bot.command()
async def auto(ctx, pool_name: str = "default"):
    global auto_task, current_index
    subs = POOLS.get(pool_name, [])
    if not subs:
        await ctx.send(f"⚠ Pool '{pool_name}' not found.")
        return

    if auto_task and not auto_task.done():
        await ctx.send("⚠ Auto is already running!")
        return

    current_index = 0
    auto_task = asyncio.create_task(auto_loop(ctx, subs))
    await ctx.send(f"✅ Auto started with pool '{pool_name}'")

@bot.command()
async def autosub(ctx, sub: str):
    global auto_task, current_index
    subs = [sub]
    current_index = 0

    if auto_task and not auto_task.done():
        await ctx.send("⚠ Auto is already running!")
        return

    auto_task = asyncio.create_task(auto_loop(ctx, subs))
    await ctx.send(f"✅ Auto started with subreddit r/{sub}")

@bot.command()
async def stop(ctx):
    global auto_running
    auto_running = False
    await ctx.send("⏹ Auto stopped manually.")

@bot.command()
async def skip(ctx):
    global current_index
    current_index += 1
    await ctx.send("⏭ Skipped to next subreddit.")

# --- NEW: !r command for single subreddit fetch ---
@bot.command()
async def r(ctx, sub: str, limit: int = 5):
    """Fetch a few posts from a subreddit without auto mode"""
    posts = fetch_subreddit_posts(sub, limit=limit)
    if not posts:
        await ctx.send(f"⚠ Could not fetch from r/{sub}")
        return
    await ctx.send(f"📥 Fetching {limit} posts from **r/{sub}**")
    for submission in posts:
        await send_post(ctx, submission)
        await asyncio.sleep(2)

# --- Run bot ---
if user_token:
    bot.run(user_token)
else:
    print("[ERROR] No user_token found in environment!")
    
