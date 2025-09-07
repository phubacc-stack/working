import os
import sys
import asyncio
import random as pyrandom
import discord
from discord.ext import commands
import threading
from flask import Flask
import time
import praw
from datetime import datetime
import logging
from collections import defaultdict

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v7.0-self'
start_time = datetime.utcnow()
post_counter = 0
sub_usage_counter = defaultdict(int)
last_posts = []  # store last sent posts

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nsfwbot")

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)
if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"

# --- Reddit API setup (praw) ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2LacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

# --- Pools ---
nsfw_pool = [
    "nsfw", "gonewild", "RealGirls", "rule34", "porn", "nsfw_gifs",
    "ass", "boobs", "NSFW_Snapchat", "BustyPetite", "collegesluts",
    "Amateur", "nsfwhardcore", "Blowjobs", "gwcumsluts", "pawg",
    "chickswithtattoos", "PetiteGoneWild", "cumsluts", "thick",
    "nsfwbikinis", "OnOff", "smalltits", "BigBoobsGW", "HighResNSFW",
    "GirlsFinishingTheJob", "palegirls", "TheUnderbun", "workgonewild",
    "justthetip", "60fpsporn", "porninfifteenseconds", "cuckold",
    "anal", "blowjobsandwich", "tightdresses", "leggingsgonewild",
    "SuicideGirls", "nsfwoutfits", "ToplessInJeans", "publicplug",
    "workoutgonewild", "Hotwife", "MomsGoneWild", "milf",
    "hotchickswithtattoos", "nsfwcosplay", "BDSMGW", "pussy",
    "squirting_gifs", "thickwhitegirls", "slutwife", "PornStars",
    "PerfectPussies", "SexyGirlsInBoots", "Blonde", "nsfwart",
    "rearpussy", "MatureMilfs", "analgw", "thickasses", "Stacked",
    "Assholes", "GirlsWithBigToys", "O_Faces", "GirlsInYogaPants",
    "NSFW_GIF", "TrueAmateurs", "AltGoneWild", "brunette",
    "redheads", "legalteensxxx", "fitgirls", "boobies",
    "asstastic", "NSFWVideos", "DeepThroat", "gonewildcurvy",
    "DirtyGaming", "nsfw_college", "facials", "hugeboobs",
    "Upskirt", "ThickFit", "NSFWFunny", "hairypussy",
    "NaughtyWives", "cumcovered", "ebony", "Latinas",
    "nsfw_videos", "BiggerThanYouThought", "FutanariGoneWild",
    "trainerfucks", "AmateurPorn", "Exxxtras", "BustyNaturals",
    "TittyDrop", "TheGape", "WorkGoneWild", "Nudes", "Rule34LoL",
    "NotSafeForWork", "LegalTeens",
    "AmateurGirls", "NSFW_Wallpapers", "porn_gifs",
    "RealAmateur", "TrueFucking", "homemadexxx",
    "NSFW_Girls", "Tgirls", "NSFW_Snapchat2"
]

hentai_pool = [
    "hentai", "rule34", "AnimeBooty", "thick_hentai", "ahegao",
    "ecchi", "hentaibondage", "oppai_gif", "HQHentai", "HentaiGIF",
    "NarutoHentai", "DragonBallHentai", "PokemonNSFW", "DisneyNSFW",
    "OverwatchNSFW", "OnePieceHentai", "AnimeArmpits", "BigAnimeTiddies",
    "MaidHentai", "MonsterGirls", "hentai_gifs", "HentaiBlowjobs",
    "thighhighs", "animelegs", "Tentai", "HentaiAnal", "futa",
    "UncensoredHentai", "YuriNSFW", "AnimeMILFS", "WaifuPorn",
    "hentaiass", "ecchiGIFs", "TouhouNSFW", "BDSMhentai",
    "DragonBallZNSFW", "NarutoRule34", "FairyTailNSFW", "BleachNSFW",
    "DigimonNSFW", "HentaiThighs", "HentaiPetgirls",
    "LeagueOfLegendsNSFW", "GenshinImpactNSFW", "SailorMoonNSFW",
    "EvangelionNSFW", "FateHentai", "OverwatchHentai", "RWBYNSFW",
    "AvatarNSFW", "KantaiCollectionNSFW", "ReZeroNSFW", "KonosubaNSFW",
    "MyHeroHentai", "DemonSlayerHentai", "OnePunchManNSFW",
    "AttackOnTitanNSFW", "InuyashaNSFW", "CodeGeassNSFW",
    "BlackCloverNSFW", "BorutoHentai", "YuGiOhNSFW", "KillLaKillNSFW",
    "PersonaNSFW", "NierNSFW", "FinalFantasyNSFW", "DisneyHentai",
    "CartoonHentai", "GravityFallsNSFW", "KimPossibleNSFW",
    "TeenTitansNSFW", "ScoobyDooNSFW", "LooneyTunesNSFW",
    "RegularShowNSFW", "TotalDramaNSFW", "DannyPhantomNSFW",
    "PhineasAndFerbNSFW", "ecchibabes", "rule34cartoons",
    "LewdAnimeGirls", "OppaiHentai", "AnimeNsfw", "BunnyGirlsNSFW",
    "WaifuNsfw", "HentaiHQ", "AnimeEcchi", "nsfwanimegifs",
    "EcchiHentai", "HentaiCouples", "ShotaHentai", "MonsterGirlNSFW",
    "DoujinHentai", "HentaiThicc", "UncensoredEcchi", "LewdHentai",
    "AnimeNSFW", "CartoonRule34", "nsfwcosplayhentai", "EcchiWaifus",
    "Rule34Cartoon", "EcchiParadise", "LewdCartoons", "AnimeThighs",
    "HentaiXXX", "Doujinshi", "LewdWaifus", "AnimeLewd", "Rule34Overwatch",
    "HentaiEcchi", "LewdAnimeArt", "AnimeLewds",
    "EcchiGirls", "HentaiArts", "EcchiCollections",
    "NSFWHentaiArt", "LewdAnimeGirlsHQ", "ThiccAnime"
]

# --- Cache ---
post_cache = {}

def get_cached_posts(subreddit, content_type, limit=500):
    key = (subreddit, content_type)
    if key not in post_cache or not post_cache[key]:
        post_cache[key] = get_filtered_posts(subreddit, content_type, limit=limit)
    if post_cache[key]:
        return post_cache[key].pop()
    return None

def get_filtered_posts(subreddit_name, content_type, limit=500):
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        fetch_method = pyrandom.choice(["hot", "new", "top"])
        if fetch_method == "hot":
            listings = subreddit.hot(limit=limit)
        elif fetch_method == "new":
            listings = subreddit.new(limit=limit)
        else:
            listings = subreddit.top(limit=limit)

        for post in listings:
            if post.stickied:
                continue
            url = str(post.url)

            if content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url):
                posts.append(url)
            elif content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url):
                posts.append(url)
            elif content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url):
                posts.append(url)

        pyrandom.shuffle(posts)

    except Exception as e:
        logger.error(f"[Reddit Error] r/{subreddit_name}: {e}")
    return posts

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    """Usage: !r <amount> <type>"""
    global post_counter, last_posts
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ NSFW only command.")
    if amount > 10:
        return await ctx.send("⚠️ Max 10 posts at once.")
    if content_type not in ["img", "gif", "vid"]:
        return await ctx.send("⚠️ Type must be img | gif | vid.")

    pool = nsfw_pool + hentai_pool
    results = []
    for _ in range(amount * 10):
        subreddit = pyrandom.choice(pool)
        post = get_cached_posts(subreddit, content_type)
        if post:
            results.append(post)
            sub_usage_counter[subreddit] += 1
        if len(results) >= amount:
            break

    if results:
        post_counter += len(results[:amount])
        last_posts = results[:amount]
        for url in results[:amount]:
            await ctx.send(url)
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def batch(ctx, amount: int = 5, content_type: str = "img"):
    global last_posts
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ NSFW only.")
    pool = nsfw_pool + hentai_pool
    posts = []
    for _ in range(amount * 10):
        subreddit = pyrandom.choice(pool)
        post = get_cached_posts(subreddit, content_type)
        if post:
            posts.append(post)
            sub_usage_counter[subreddit] += 1
        if len(posts) >= amount:
            break
    if posts:
        last_posts = posts[:amount]
        await ctx.send("\n".join(posts[:amount]))
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def search(ctx, keyword: str, amount: int = 3, content_type: str = "img"):
    """Search Reddit for keyword"""
    global last_posts
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ NSFW only.")
    results = []
    try:
        for post in reddit.subreddit("all").search(keyword, limit=500, sort="relevance"):
            url = str(post.url)
            if content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url):
                results.append(url)
            elif content_type == "gif" and (".gif" in url or "gfycat" in url or "redgifs" in url):
                results.append(url)
            elif content_type == "vid" and (".mp4" in url or "v.redd.it" in url):
                results.append(url)
            if len(results) >= amount:
                break
    except Exception as e:
        return await ctx.send(f"⚠️ Search failed: {e}")
    if results:
        last_posts = results
        await ctx.send("\n".join(results))
    else:
        await ctx.send("❌ No results found.")

@client.command()
async def last(ctx, amount: int = 3):
    """Resend last posts"""
    if not last_posts:
        return await ctx.send("ℹ️ No posts saved yet.")
    await ctx.send("\n".join(last_posts[:amount]))

@client.command()
async def randomsub(ctx):
    sub = pyrandom.choice(nsfw_pool + hentai_pool)
    post = get_cached_posts(sub, "img")
    if post:
        await ctx.send(f"🎲 r/{sub} → {post}")
    else:
        await ctx.send(f"❌ Couldn’t fetch from r/{sub}")

@client.command()
async def poolsize(ctx):
    await ctx.send(f"📂 NSFW: {len(nsfw_pool)} subs | Hentai: {len(hentai_pool)} subs")

@client.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency {round(client.latency*1000)}ms")

# --- Auto Posting (same as before) ---
auto_tasks = {}

async def auto_loop(channel, seconds, content_type, mix=False):
    pool = nsfw_pool + hentai_pool
    try:
        while True:
            ctype = pyrandom.choice(["img", "gif", "vid"]) if (content_type == "random" or mix) else content_type
            subreddit = pyrandom.choice(pool)
            post = get_cached_posts(subreddit, ctype)
            if post:
                await channel.send(post)
                sub_usage_counter[subreddit] += 1
            await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        await channel.send("⏹️ Auto stopped.")
        raise
    except Exception as e:
        await channel.send(f"⚠️ Auto crashed: {e}")

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ NSFW only.")
    if seconds < 5:
        return await ctx.send("⚠️ Minimum is 5 seconds.")
    if content_type not in ["img", "gif", "vid", "random"]:
        return await ctx.send("⚠️ Type must be img | gif | vid | random.")
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        return await ctx.send("⚠️ Auto already running here.")
    task = asyncio.create_task(auto_loop(ctx.channel, seconds, content_type))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started every {seconds}s for {content_type}.")

@client.command()
async def automix(ctx, seconds: int = 30):
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ NSFW only.")
    if seconds < 5:
        return await ctx.send("⚠️ Minimum is 5 seconds.")
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        return await ctx.send("⚠️ Auto already running here.")
    task = asyncio.create_task(auto_loop(ctx.channel, seconds, "random", mix=True))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Automix started every {seconds}s.")

@client.command()
async def autostop(ctx):
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped here.")
    else:
        await ctx.send("⚠️ Auto was not running.")

# --- Stats ---
@client.command()
async def stats(ctx):
    uptime = datetime.utcnow() - start_time
    await ctx.send(f"📊 Uptime: {uptime} | Posts sent: {post_counter} | Version: {version}")

@client.command()
async def rstats(ctx):
    if not sub_usage_counter:
        return await ctx.send("ℹ️ No subreddit stats yet.")
    top = sorted(sub_usage_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    msg = "\n".join([f"r/{sub}: {count}" for sub, count in top])
    await ctx.send(f"📊 **Top Subreddits Used**\n{msg}")

@client.command()
async def helpme(ctx):
    await ctx.send(
        "**Commands:**\n"
        "`!r <amount> <type>` - Random posts\n"
        "`!batch <amount> <type>` - Multiple posts\n"
        "`!search <keyword> <amount> <type>` - Search Reddit\n"
        "`!last <amount>` - Resend last posts\n"
        "`!randomsub` - Random subreddit post\n"
        "`!auto <seconds> <type>` - Auto posting\n"
        "`!automix <seconds>` - Auto random type\n"
        "`!autostop` - Stop auto/automix\n"
        "`!stats` - Show stats\n"
        "`!rstats` - Top subreddits used\n"
        "`!poolsize` - Pool sizes\n"
        "`!ping` - Latency check\n"
        "`!alive` - Quick check\n"
    )

@client.command()
async def alive(ctx):
    await ctx.send("✅ Bot is alive and running!")

# --- Flask ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server).start()

# --- Run bot ---
while True:
    try:
        client.run(user_token, bot=False)
    except Exception as e:
        logger.error(f"[Bot Error] Restarting: {e}")
        time.sleep(5)
    
