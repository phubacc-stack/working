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
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.6-auto-pool-fullwalk-pause-galleryfix-extended'
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

# --- Fuzzy match ---
def correct_subreddit(subreddit_name):
    """Return matched subreddit from pool if fuzzy match >= 70, else return original."""
    if not all_subs_pool:
        return subreddit_name
    match = process.extractOne(subreddit_name, all_subs_pool, scorer=fuzz.ratio)
    if match:
        mname, score, _ = match
        if score >= 70:
            if mname != subreddit_name:
                print(f"[Fuzzy] Corrected '{subreddit_name}' -> '{mname}' ({score})")
            return mname
    return subreddit_name

def is_known_subreddit(token):
    """Return (matched_name, score) if token fuzzy matches a pool subreddit; else (None, 0)."""
    if not all_subs_pool:
        return (None, 0)
    match = process.extractOne(token, all_subs_pool, scorer=fuzz.ratio)
    if match:
        mname, score, _ = match
        return (mname, score)
    return (None, 0)

# --- Iterator cache ---
sub_iterators = {}

def get_subreddit_iterator(subreddit_name, fetch_method):
    key = f"{subreddit_name}:{fetch_method}"
    if key not in sub_iterators or sub_iterators[key] is None:
        subreddit = reddit.subreddit(subreddit_name)
        try:
            listings = getattr(subreddit, fetch_method)(limit=None)
            sub_iterators[key] = iter(listings)
        except Exception as e:
            print(f"[Iterator Error] r/{subreddit_name}:{fetch_method} -> {e}")
            sub_iterators[key] = None
    return sub_iterators.get(key)

# --- Gallery extraction ---
def extract_gallery_urls(post):
    """
    Return list of gallery image URLs in correct order for a praw Submission with gallery_data & media_metadata.
    Tries "s" -> "u" first, falls back to highest preview ("p") entry.
    """
    urls = []
    try:
        if not hasattr(post, "gallery_data") or not hasattr(post, "media_metadata"):
            return urls
        meta = post.media_metadata
        items = post.gallery_data.get("items", [])
        for item in items:
            media_id = item.get("media_id")
            if not media_id:
                continue
            if media_id not in meta:
                continue
            media_info = meta[media_id]
            # Prefer 's' -> 'u'
            if "s" in media_info and isinstance(media_info["s"], dict) and "u" in media_info["s"]:
                url = html.unescape(media_info["s"]["u"])
                urls.append(url)
            else:
                # fallback to preview sizes 'p' pick highest resolution available
                if "p" in media_info and isinstance(media_info["p"], list) and media_info["p"]:
                    # the last preview usually has highest resolution
                    preview = media_info["p"][-1]
                    if "u" in preview:
                        urls.append(html.unescape(preview["u"]))
                # last fallback: if 'u' directly present
                elif "u" in media_info:
                    urls.append(html.unescape(media_info["u"]))
    except Exception as e:
        print(f"[Gallery Error] {e}")
    # final small normalization: remove query params like &amp; etc
    cleaned = []
    for u in urls:
        if u:
            cleaned.append(u.replace("&amp;", "&"))
    return cleaned

# --- Fetch posts (supports subreddit name or search query) ---
def get_filtered_posts(source, content_type, fetch_method=None, batch_size=25):
    """
    source: either 'r/subname' or 'search:some words' or plain str (we detect).
    content_type: img|gif|vid|any|random
    fetch_method: only used when source is a subreddit
    """
    global seen_posts
    posts = []
    fetch_method = fetch_method or pyrandom.choice(["hot", "new", "top"])
    is_search = False
    sub_name = None
    # Detect source type
    if isinstance(source, dict) and source.get("type") == "search":
        is_search = True
        query = source.get("query")
    else:
        # plain string candidate
        candidate = source
        # if user prefixed explicitly like 'search:abc', treat as search
        if isinstance(candidate, str) and candidate.lower().startswith("search:"):
            is_search = True
            query = candidate[len("search:"):].strip()
        else:
            # try fuzzy match
            match_name, score = is_known_subreddit(candidate)
            if match_name and score >= 70:
                sub_name = match_name
            else:
                # treat as search
                is_search = True
                query = candidate

    try:
        if is_search:
            # Use reddit search over r/all
            # expand limit a bit to find enough multitype posts
            try:
                results = reddit.subreddit("all").search(query, sort="new", limit=batch_size * 3)
            except Exception:
                results = reddit.subreddit("all").search(query, limit=batch_size * 3)
            for post in results:
                if post.stickied:
                    continue
                url = str(post.url)
                # galleries
                if "reddit.com/gallery" in url and hasattr(post, "gallery_data") and hasattr(post, "media_metadata"):
                    gallery_urls = extract_gallery_urls(post)
                    for g in gallery_urls:
                        if g not in seen_posts:
                            posts.append(g)
                else:
                    # normalize imgur
                    if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                        continue
                    if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                        url += ".jpg"
                    # filter by content_type
                    if content_type == "any":
                        accept = (url.endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4")) or
                                  "i.redd.it" in url or "v.redd.it" in url or "redgifs" in url or "gfycat" in url or url.endswith(".gifv"))
                    elif content_type == "gif":
                        accept = (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv"))
                    elif content_type == "vid":
                        accept = (url.endswith(".mp4") or "v.redd.it" in url or "redgifs" in url)
                    else:  # img
                        accept = (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url)
                    if accept and url not in seen_posts:
                        posts.append(url)

        else:
            # subreddit flow
            subreddit_name = sub_name
            iterator = get_subreddit_iterator(subreddit_name, fetch_method)
            if iterator is None:
                print(f"[Fetch] No iterator for r/{subreddit_name}")
                return []
            while len(posts) < batch_size:
                try:
                    post = next(iterator)
                except StopIteration:
                    sub_iterators[f"{subreddit_name}:{fetch_method}"] = None
                    break
                except Exception as e:
                    print(f"[Iterator Next Error] r/{subreddit_name}: {e}")
                    break

                if getattr(post, "stickied", False):
                    continue
                url = str(post.url)

                # galleries
                if "reddit.com/gallery" in url and hasattr(post, "gallery_data") and hasattr(post, "media_metadata"):
                    gallery_urls = extract_gallery_urls(post)
                    for g in gallery_urls:
                        if g not in seen_posts:
                            posts.append(g)
                    # continue to next post
                    continue

                # Ignore bad imgur links
                if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                    continue
                if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                    url += ".jpg"

                # Filter by type
                if content_type == "any":
                    accept = (url.endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4")) or
                              "i.redd.it" in url or "v.redd.it" in url or "redgifs" in url or "gfycat" in url or url.endswith(".gifv"))
                elif content_type == "gif":
                    accept = (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv"))
                elif content_type == "vid":
                    accept = (url.endswith(".mp4") or "v.redd.it" in url or "redgifs" in url)
                else:  # img
                    accept = (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url)

                if accept and url not in seen_posts:
                    posts.append(url)

        # post-processing: mark seen, limit seen_posts set size
        if posts:
            # Already flattened above: posts is list of URLs
            final = []
            for p in posts:
                if p not in seen_posts:
                    final.append(p)
                    seen_posts.add(p)
            posts = final
            if len(seen_posts) > 8000:
                seen_posts.clear()

    except Exception as e:
        print(f"[Reddit Error] source={source}: {e}")

    print(f"[Fetched] {source} -> {len(posts)} posts")
    return posts

# --- Auto system ---
auto_tasks = {}
skip_flags = {}
pause_flags = {}

async def safe_send(channel, url):
    """Send a URL to discord channel with error handling."""
    try:
        await channel.send(url)
    except Exception as e:
        print(f"[Discord Error] Failed to send: {e}")

async def send_with_gallery_support(channel, item):
    """
    item: either a URL string or a list of URLs (gallery).
    For lists, send sequentially with a small delay to avoid rate limits.
    """
    global post_counter
    if isinstance(item, list):
        for url in item:
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(1)
    else:
        await safe_send(channel, item)
        post_counter += 1

# --- Argument parsing helpers ---
def parse_tail_seconds_and_type(tokens):
    """
    From tokens list (mutable), detect trailing seconds (int) and content_type.
    Returns (seconds, content_type, remaining_tokens).
    Default seconds=5, content_type='img'
    content_type may be one of 'img','gif','vid','any','random'
    """
    seconds = 5
    content_type = "img"
    t = tokens[:]
    # look for trailing content_type token
    if t:
        last = t[-1].lower()
        if last in ("img", "gif", "vid", "random", "any"):
            content_type = last
            t = t[:-1]
    # look for trailing seconds (int)
    if t:
        last = t[-1]
        try:
            sec = int(last)
            if sec >= 2:
                seconds = sec
            t = t[:-1]
        except Exception:
            pass
    return seconds, content_type, t

def group_tokens_into_sources(tokens):
    """
    Given tokens list (already trimmed of seconds & type), group them into sources for autosub/command.
    Behavior per user's choice C + S-Grouping 3 (auto-merge):
      - Walk tokens left-to-right
      - If a token fuzzy-matches a known subreddit (score>=70): it's its own source (use matched name)
      - Else: start merging consecutive non-sub tokens into a single search phrase (space-joined)
    Returns list of sources:
      - For sub source: string of subreddit name
      - For search source: dict {"type":"search","query":"..."}
    """
    i = 0
    sources = []
    n = len(tokens)
    while i < n:
        token = tokens[i]
        # try fuzzy match
        match_name, score = is_known_subreddit(token)
        if match_name and score >= 70:
            sources.append(match_name)
            i += 1
        else:
            # accumulate consecutive non-sub tokens
            parts = [token]
            i += 1
            while i < n:
                next_token = tokens[i]
                mn, sc = is_known_subreddit(next_token)
                if mn and sc >= 70:
                    break
                parts.append(next_token)
                i += 1
            query = " ".join(parts).strip()
            if query:
                sources.append({"type": "search", "query": query})
    return sources

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, *rest):
    """
    Usage:
      !r 5 subname
      !r 3 search terms here
      !r 10 any
    Auto-detects whether rest is subreddit or search. If multiple tokens in rest they are auto-merged into a search phrase unless a fuzzy sub match exists.
    """
    global post_counter
    if amount > 50:
        amount = 50
    tokens = list(rest)
    # if nothing passed, choose random from pool
    if not tokens:
        pool = nsfw_pool + hentai_pool
        if not pool:
            await ctx.send("❌ No sub pools loaded.")
            return
        sub = pyrandom.choice(pool)
        content_type = "img"
        posts = get_filtered_posts(sub, content_type, None)
        collected = posts[:amount]
        if collected:
            for item in collected:
                await send_with_gallery_support(ctx.channel, item)
            return
        else:
            await ctx.send("❌ No posts found.")
            return

    seconds, content_type, remaining = parse_tail_seconds_and_type(tokens)
    # combine remaining into a single source (auto-merge behavior for r command)
    if not remaining:
        await ctx.send("⚠️ No source specified.")
        return
    # For r command, treat the combined remaining tokens as one source (auto-merge)
    combined = " ".join(remaining)
    # Detect if combined is subreddit or search
    match_name, score = is_known_subreddit(combined)
    if match_name and score >= 70:
        source = match_name
    else:
        source = {"type": "search", "query": combined}

    collected = []
    tries = 0
    max_tries = amount * 3
    while len(collected) < amount and tries < max_tries:
        posts = get_filtered_posts(source, content_type)
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
async def search(ctx, *terms):
    """
    Usage:
      !search busty thick cosplay
      (auto-merges all tokens into single search)
    """
    if not terms:
        await ctx.send("⚠️ Usage: !search your search terms here")
        return
    query = " ".join(terms)
    posts = get_filtered_posts({"type":"search","query":query}, "any", None)
    if not posts:
        await ctx.send(f"❌ No search results for `{query}`.")
        return
    # limit to 25
    for item in posts[:25]:
        await send_with_gallery_support(ctx.channel, item)

# --- FIXED: Autosub now supports unlimited subs and searches, mixes randomly (S2) ---
@client.command()
async def autosub(ctx, *args):
    """
    Usage examples:
      !autosub ass busty milf 5 any
      !autosub ass sub2 sub3 4 img
      !autosub search terms without quotes will be auto-merged 6 random
    Behavior:
      - Trailing integer is seconds (min 2)
      - Trailing content type can be img|gif|vid|any|random
      - All tokens before seconds are parsed: fuzzy matched to subs, otherwise auto-merged into search phrases.
      - Sources are mixed randomly each cycle (S2).
    """
    global auto_tasks
    if not args:
        await ctx.send("⚠️ Usage: !autosub <sources...> <seconds> <type>")
        return
    tokens = list(args)
    seconds, content_type, sources_tokens = parse_tail_seconds_and_type(tokens)
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random", "any"]:
        await ctx.send("⚠️ Type must be img | gif | vid | any | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return
    if not sources_tokens:
        await ctx.send("⚠️ No sources specified.")
        return

    # Build sources list (fuzzy detect & auto-merge)
    sources = group_tokens_into_sources(sources_tokens)
    if not sources:
        await ctx.send("⚠️ No valid sources parsed.")
        return

    skip_flags[ctx.channel.id] = False
    pause_flags[ctx.channel.id] = False

    async def auto_loop(channel):
        # infinite loop
        while True:
            # choose a random source each cycle (S2)
            src = pyrandom.choice(sources)
            # pick content type for this source
            ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
            posts = get_filtered_posts(src, ctype)
            if not posts:
                # try next source after a short sleep
                await asyncio.sleep(1)
                continue
            # announce (if subreddit string)
            if isinstance(src, str):
                await channel.send(f"▶ Now playing from r/{src}")
            else:
                # search dict
                await channel.send(f"▶ Now searching `{src.get('query')}`")
            for post in posts:
                if skip_flags.get(ctx.channel.id):
                    skip_flags[ctx.channel.id] = False
                    break
                while pause_flags.get(ctx.channel.id, False):
                    await asyncio.sleep(1)
                await send_with_gallery_support(channel, post)
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    # Make a friendly summary of sources
    summary = []
    for s in sources:
        if isinstance(s, str):
            summary.append(f"r/{s}")
        else:
            summary.append(f"search:`{s.get('query')}`")
    await ctx.send(f"▶️ AutoSub started ({', '.join(summary)}) every {seconds}s (type={content_type}).")

# --- Auto full walk (unchanged except content_type 'any' support) ---
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

    pool = nsfw_pool if pool_name == "nsfw" else hentai_pool if pool_name == "hentai" else nsfw_pool + hentai_pool

    async def auto_loop(channel):
        while True:
            sub = pyrandom.choice(pool)
            ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
            posts = get_filtered_posts(sub, ctype)
            if not posts:
                await asyncio.sleep(1)
                continue
            await channel.send(f"▶ Now walking full r/{sub}")
            for post in posts:
                if skip_flags.get(ctx.channel.id):
                    skip_flags[ctx.channel.id] = False
                    break
                while pause_flags.get(ctx.channel.id, False):
                    await asyncio.sleep(1)
                await send_with_gallery_support(channel, post)
                await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started for {pool_name} pool every {seconds}s for {content_type}.")

# --- Pause / Resume ---
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

# --- Skip / Stop / Stats ---
@client.command()
async def skip(ctx):
    if ctx.channel.id in skip_flags:
        skip_flags[ctx.channel.id] = True
        await ctx.send("⏭ Skipping current source...")

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
