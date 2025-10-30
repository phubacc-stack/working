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

version = 'v5.8-auto-dualsub-fastgallery-nsfwsearch-fixed'
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

intents = discord.Intents.default()
client = commands.Bot(command_prefix="!", intents=intents)

# --- Fuzzy match ---
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

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        listings = getattr(subreddit, fetch_method)(limit=None)
        sub_iterators[key] = iter(listings)
    return sub_iterators[key]

# --- Helper: normalize imgur / gifv etc. ---
def normalize_url(url):
    if not url:
        return url
    if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
        return None
    if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
        return url + ".jpg"
    if url.endswith(".gifv"):
        return url[:-5] + ".mp4"
    return url

# --- Fetch posts (gallery + normal) ---
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

            if getattr(post, "stickied", False):
                continue

            # ensure we only take media posts
            try:
                url = str(post.url)
            except Exception:
                url = ""

            # Galleries (reddit native)
            is_gallery = getattr(post, "is_gallery", False) or hasattr(post, "gallery_data")
            if is_gallery and hasattr(post, "media_metadata"):
                gallery_urls = []
                items = []
                try:
                    items = post.gallery_data.get("items", []) if getattr(post, "gallery_data", None) else []
                except Exception:
                    items = []
                for item in items[:25]:
                    media_id = item.get("media_id")
                    media = post.media_metadata.get(media_id, {})
                    # pick 's' -> 'u' if available, fallback to other fields
                    src = None
                    try:
                        if "s" in media and "u" in media["s"]:
                            src = html.unescape(media["s"]["u"])
                        elif "p" in media and media["p"]:
                            src = html.unescape(media["p"][-1].get("u"))
                    except Exception:
                        src = None
                    if src:
                        src = normalize_url(src)
                        if src and src not in seen_posts:
                            gallery_urls.append(src)
                if gallery_urls:
                    posts.append(gallery_urls)
                continue

            # other media (img, gif, mp4, redgifs, v.redd.it)
            url_norm = normalize_url(url)
            if not url_norm:
                continue

            # Filter by type
            is_img = url_norm.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url_norm
            is_gif = url_norm.endswith(".gif") or "gfycat" in url_norm or "redgifs" in url_norm or url_norm.endswith(".mp4") and "gif" in url_norm
            is_vid = url_norm.endswith(".mp4") or "v.redd.it" in url_norm or "redgifs" in url_norm or "gfycat" in url_norm

            if (
                (content_type == "img" and is_img)
                or (content_type == "gif" and (is_gif or url_norm.endswith(".gif") or "gfycat" in url_norm or "redgifs" in url_norm))
                or (content_type == "vid" and is_vid)
                or (content_type == "random" and (is_img or is_gif or is_vid))
            ):
                if url_norm not in seen_posts:
                    posts.append(url_norm)

        # flatten posts (we already store lists for galleries)
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
skip_flags = {}            # preserved but repurposed for single-subreddit skipping if needed
pause_flags = {}
# New state per-channel:
current_subs_by_channel = {}    # channel.id -> [sub1, sub2]
change_subs_flags = {}         # channel.id -> True when auto should pick new random subs
next_to_second_flags = {}      # channel.id -> True when user invoked !next
auto_locks = {}                # per-channel asyncio.Lock to avoid races

async def safe_send(channel, url):
    try:
        # send strings or embed as needed; keep simple send
        await channel.send(url)
    except Exception as e:
        print(f"[Discord Error] Failed to send: {e}")

# --- Fast gallery send ---
async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item, list):
        # send all images in list (fast sleep between)
        for url in item:
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(0.4)
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
    max_tries = amount * 4
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

# --- NSFW Search (improved) ---
@client.command()
async def nsfwsearch(ctx, *, query: str):
    """Search Reddit for NSFW content by phrase (returns up to 3 full posts)."""
    await ctx.send(f"🔍 Searching for `{query}` (looking for NSFW posts)...")
    try:
        # broader limit to find more results
        results = reddit.subreddit("all").search(query, sort="relevance", limit=200)
        found_count = 0
        for post in results:
            if found_count >= 3:
                break
            try:
                if not getattr(post, "over_18", False):
                    continue

                # Try to collect all media URLs for this post
                media_to_send = []

                # native gallery
                is_gallery = getattr(post, "is_gallery", False) or hasattr(post, "gallery_data")
                if is_gallery and hasattr(post, "media_metadata"):
                    items = []
                    try:
                        items = post.gallery_data.get("items", []) if getattr(post, "gallery_data", None) else []
                    except Exception:
                        items = []
                    for item in items[:25]:
                        media_id = item.get("media_id")
                        media = post.media_metadata.get(media_id, {})
                        src = None
                        try:
                            if "s" in media and "u" in media["s"]:
                                src = html.unescape(media["s"]["u"])
                            elif "p" in media and media["p"]:
                                src = html.unescape(media["p"][-1].get("u", ""))
                        except Exception:
                            src = None
                        if src:
                            src = normalize_url(src)
                            if src:
                                media_to_send.append(src)
                else:
                    url = str(getattr(post, "url", "") or "")
                    url = normalize_url(url)
                    # v.redd.it often needs to be sent as is (Discord will embed)
                    if url:
                        media_to_send.append(url)

                    # If the post has media in preview / media fields, try to pick mp4 fallback
                    try:
                        if getattr(post, "media", None):
                            # reddit hosted video
                            reddit_media = post.media
                            if isinstance(reddit_media, dict):
                                reddit_video = reddit_media.get("reddit_video")
                                if reddit_video:
                                    fallback = reddit_video.get("fallback_url")
                                    if fallback:
                                        media_to_send.append(fallback)
                    except Exception:
                        pass

                # filter duplicates and empties
                media_to_send = [m for i, m in enumerate(media_to_send) if m and m not in media_to_send[:i]]

                if not media_to_send:
                    continue

                # send the post (all media collected)
                await ctx.send(f"🔞 Found: r/{post.subreddit.display_name} — {post.title}")
                await send_with_gallery_support(ctx.channel, media_to_send)
                found_count += 1
            except Exception as e:
                print("[nsfwsearch] single post handling error:", e)
                continue

        if found_count == 0:
            await ctx.send("❌ No NSFW results found.")
    except Exception as e:
        await ctx.send(f"⚠️ Error during search: {e}")

# --- AutoSub (manual 1 or 2 subs) ---
@client.command()
async def autosub(ctx, sub1: str, sub2: str = None, seconds: int = 5, content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False

    async def auto_loop(channel):
        subs = [sub1] if sub2 is None else [sub1, sub2]
        await channel.send(f"▶️ Autosub manual started for: {', '.join(subs)} every {seconds}s")
        while True:
            for s in subs:
                ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
                posts = get_filtered_posts(s, ctype)
                if not posts:
                    await channel.send(f"❌ No posts found for r/{s}.")
                    continue
                await channel.send(f"▶ Now playing from r/{s}")
                for post in posts:
                    if skip_flags.get(channel.id):
                        skip_flags[channel.id] = False
                        break
                    while pause_flags.get(channel.id, False):
                        await asyncio.sleep(1)
                    await send_with_gallery_support(channel, post)
                    await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Autosub started for r/{sub1}" + (f" + r/{sub2}" if sub2 else "") + f" every {seconds}s.")

# --- Auto (dual random subs) - improved interleaving + controls ---
@client.command()
async def auto(ctx, seconds: int = 5, pool_name: str = "both", content_type: str = "img"):
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if pool_name not in ["nsfw", "hentai", "both"]:
        await ctx.send("⚠️ Pool must be nsfw | hentai | both.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    pause_flags[ctx.channel.id] = False
    skip_flags[ctx.channel.id] = False
    change_subs_flags[ctx.channel.id] = False
    next_to_second_flags[ctx.channel.id] = False
    auto_locks[ctx.channel.id] = asyncio.Lock()

    pool = nsfw_pool if pool_name == "nsfw" else hentai_pool if pool_name == "hentai" else nsfw_pool + hentai_pool
    if not pool:
        await ctx.send("⚠️ The selected pool is empty.")
        return

    async def auto_loop(channel):
        # initial pick
        async with auto_locks[channel.id]:
            subs = pyrandom.sample(pool, 2) if len(pool) >= 2 else [pyrandom.choice(pool)]
            current_subs_by_channel[channel.id] = subs
        await channel.send(f"▶️ Auto started for {pool_name} pool every {seconds}s (2 subs per loop).")
        while True:
            # if requested, change subs
            if change_subs_flags.get(channel.id):
                async with auto_locks[channel.id]:
                    subs = pyrandom.sample(pool, 2) if len(pool) >= 2 else [pyrandom.choice(pool)]
                    current_subs_by_channel[channel.id] = subs
                    change_subs_flags[channel.id] = False
                await channel.send(f"🔁 New subs selected: {', '.join(subs)}")
            else:
                async with auto_locks[channel.id]:
                    subs = current_subs_by_channel.get(channel.id) or (pyrandom.sample(pool, 2) if len(pool) >= 2 else [pyrandom.choice(pool)])
                    current_subs_by_channel[channel.id] = subs

            # if user pressed !next, start with second sub this cycle
            start_with_index = 0
            if next_to_second_flags.get(channel.id):
                start_with_index = 1
                next_to_second_flags[channel.id] = False
                await channel.send("⏭️ Jumping to second sub now.")

            # fetch posts for both subs first (to enable interleaving)
            posts_lists = []
            for s in subs:
                ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
                posts = get_filtered_posts(s, ctype)
                posts_lists.append(posts if posts else [])

            # if both empty, pick new subs next loop
            if not any(posts_lists):
                await channel.send("⚠️ No posts found for selected subs, selecting new subs...")
                change_subs_flags[channel.id] = True
                await asyncio.sleep(1)
                continue

            await channel.send(f"🎲 Now picking from: {', '.join(subs)}")

            # interleave: send one from sub[start_with_index], then one from the other, repeat.
            max_len = max((len(l) for l in posts_lists), default=0)
            for i in range(max_len):
                for offset in range(2):
                    idx = (start_with_index + offset) % 2
                    # if there is no second sub (single), break accordingly
                    if idx >= len(posts_lists):
                        continue
                    # bounds check
                    if i >= len(posts_lists[idx]):
                        continue
                    # flags: pause -> wait, change_subs or skip -> break
                    if change_subs_flags.get(channel.id):
                        break
                    if skip_flags.get(channel.id):
                        skip_flags[channel.id] = False
                        # when skip requested, pick two new random ones immediately
                        change_subs_flags[channel.id] = True
                        break
                    while pause_flags.get(channel.id, False):
                        await asyncio.sleep(1)
                    post = posts_lists[idx][i]
                    await send_with_gallery_support(channel, post)
                    await asyncio.sleep(seconds)
                # if change_subs/skip flags set, break out to outer loop to select new subs
                if change_subs_flags.get(channel.id):
                    break

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task

# --- New commands: next / skip (pull 2 new random subs) ---
@client.command()
async def next(ctx):
    """Jump to the second subreddit in the current auto pair immediately (for !auto)."""
    if ctx.channel.id not in auto_tasks or auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ No auto running here.")
        return
    # set flag to start with second sub on next cycle
    next_to_second_flags[ctx.channel.id] = True
    await ctx.send("⏭️ Will jump to the second sub on the next send.")

@client.command()
async def skip(ctx):
    """Pick two new random subs for the channel and continue (for !auto)."""
    if ctx.channel.id not in auto_tasks or auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ No auto running here.")
        return
    change_subs_flags[ctx.channel.id] = True
    await ctx.send("🔁 Selecting 2 new random subs now.")

# --- Pause / Resume / Skip (legacy) / Stop / Stats ---
@client.command()
async def pause(ctx):
    pause_flags[ctx.channel.id] = True
    await ctx.send("⏸️ Auto paused.")

@client.command()
async def resume(ctx):
    if pause_flags.get(ctx.channel.id, False):
        pause_flags[ctx.channel.id] = False
        await ctx.send("▶️ Auto resumed.")
    else:
        await ctx.send("⚠️ Auto not paused here.")

# keep a legacy skip command handler for single-subreddit autosub usage if ever used
@client.command(name="legacy_skip")
async def legacy_skip(ctx):
    if ctx.channel.id in skip_flags:
        skip_flags[ctx.channel.id] = True
        await ctx.send("⏭ Skipping current subreddit...")

@client.command()
async def autostop(ctx):
    if ctx.channel.id in auto_tasks:
        try:
            auto_tasks[ctx.channel.id].cancel()
        except Exception:
            pass
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

# --- Keepalive ---
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

client.run(user_token)
