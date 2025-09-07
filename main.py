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
from datetime import datetime

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v4.0-self'
start_time = datetime.utcnow()
post_counter = 0

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
spam_id = os.getenv("spam_id")  # not used anymore, but kept for compatibility
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)
if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"

# --- Reddit API setup (praw) ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

# --- Read Files (pokemon/mythical placeholders for legacy support) ---
if os.path.exists("pokemon"):
    with open('pokemon', 'r', encoding='utf8') as file:
        pokemon_list = file.read()
if os.path.exists("mythical"):
    with open('mythical', 'r', encoding='utf8') as file:
        mythical_list = file.read()

client = commands.Bot(command_prefix="!")

# --- Subreddit Pools ---
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
    "NotSafeForWork", "LegalTeens"
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
    "HentaiXXX", "Doujinshi", "LewdWaifus", "AnimeLewd", "Rule34Overwatch"
]

# --- NSFW helpers ---
def get_filtered_posts(subreddit_name, content_type, limit=50):
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.hot(limit=limit):
            if post.stickied:
                continue
            url = str(post.url)

            if content_type == "img" and (
                url.endswith((".jpg", ".jpeg", ".png"))
                or "i.redd.it" in url or "preview.redd.it" in url
            ):
                posts.append(url)

            elif content_type == "gif" and (
                url.endswith(".gif")
                or "gfycat" in url or "redgifs" in url
                or url.endswith(".gifv")
            ):
                posts.append(url)

            elif content_type == "vid" and (
                url.endswith(".mp4")
                or "v.redd.it" in url
            ):
                posts.append(url)

    except Exception as e:
        print(f"[Reddit Error] Failed in r/{subreddit_name}: {e}")
    return posts

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    """Usage: !r <amount> <type>"""
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 10:
        await ctx.send("⚠️ Max 10 posts at once.")
        return
    if content_type not in ["img", "gif", "vid"]:
        await ctx.send("⚠️ Type must be img | gif | vid.")
        return

    pool = nsfw_pool + hentai_pool
    results = []
    for _ in range(amount * 4):
        subreddit = pyrandom.choice(pool)
        posts = get_filtered_posts(subreddit, content_type)
        if posts:
            results.append(pyrandom.choice(posts))
        if len(results) >= amount:
            break

    if results:
        post_counter += len(results[:amount])
        for url in results[:amount]:
            await ctx.send(url)
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 10:
        await ctx.send("⚠️ Max 10 posts at once.")
        return
    posts = get_filtered_posts(subreddit, content_type)
    if posts:
        post_counter += len(posts[:amount])
        for url in posts[:amount]:
            await ctx.send(url)
    else:
        await ctx.send(f"❌ No posts found in r/{subreddit}.")

@client.command()
async def random(ctx):
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    pool = nsfw_pool + hentai_pool
    subreddit = pyrandom.choice(pool)
    ctype = pyrandom.choice(["img", "gif", "vid"])
    posts = get_filtered_posts(subreddit, ctype)
    if posts:
        post_counter += 1
        await ctx.send(pyrandom.choice(posts))
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def mix(ctx):
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    pool = nsfw_pool + hentai_pool
    subreddit = pyrandom.choice(pool)
    ctype = pyrandom.choice(["img", "gif", "vid"])
    posts = get_filtered_posts(subreddit, ctype)
    if posts:
        post_counter += 1
        await ctx.send(pyrandom.choice(posts))
    else:
        await ctx.send("❌ No posts found in mix.")

# --- Auto System ---
auto_tasks = {}

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
    global auto_tasks, post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if seconds < 5:
        await ctx.send("⚠️ Minimum is 5 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be img | gif | vid | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    async def auto_loop(channel):
        while True:
            pool = nsfw_pool + hentai_pool
            ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
            subreddit = pyrandom.choice(pool)
            posts = get_filtered_posts(subreddit, ctype)
            if posts:
                nonlocal_post_counter = 0
                nonlocal_post_counter += 1
                await channel.send(pyrandom.choice(posts))
            await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started every {seconds}s for {content_type}.")

@client.command()
async def automix(ctx, seconds: int = 30):
    global auto_tasks, post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if seconds < 5:
        await ctx.send("⚠️ Minimum is 5 seconds.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    async def automix_loop(channel):
        while True:
            pool = nsfw_pool + hentai_pool
            ctype = pyrandom.choice(["img", "gif", "vid"])
            subreddit = pyrandom.choice(pool)
            posts = get_filtered_posts(subreddit, ctype)
            if posts:
                nonlocal_post_counter = 0
                nonlocal_post_counter += 1
                await channel.send(pyrandom.choice(posts))
            await asyncio.sleep(seconds)

    task = asyncio.create_task(automix_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Automix started every {seconds}s.")

@client.command()
async def autostop(ctx):
    global auto_tasks
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped here.")
    else:
        await ctx.send("⚠️ Auto was not running.")

# --- Stats & Help ---
@client.command()
async def stats(ctx):
    uptime = datetime.utcnow() - start_time
    await ctx.send(
        f"📊 **Stats**\n"
        f"🕒 Uptime: {uptime}\n"
        f"📩 Posts sent: {post_counter}\n"
        f"🤖 Version: {version}"
    )

@client.command()
async def helpme(ctx):
    await ctx.send(
        "**Commands:**\n"
        "`!r <amount> <type>` - Random posts (img/gif/vid)\n"
        "`!rsub <subreddit> <amount> <type>` - From specific sub\n"
        "`!random` - Random post from pool\n"
        "`!mix` - Mixed nsfw+hentai post\n"
        "`!auto <seconds> <type>` - Auto posting\n"
        "`!automix <seconds>` - Auto mix posting\n"
        "`!autostop` - Stop auto/automix\n"
        "`!stats` - Show bot stats\n"
        "`!alive` - Quick bot check\n"
    )

@client.command()
async def alive(ctx):
    await ctx.send("✅ Bot is alive and running!")

# --- Flask server ---
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
        client.run(user_token)
    except Exception as e:
        print(f"Bot crashed: {e}. Restarting in 10s...")
        time.sleep(10)
        
