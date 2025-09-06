import os
import sys
import re
import asyncio
import random as pyrandom
import discord
from discord.ext import commands, tasks
import threading
from flask import Flask
import aiohttp
import asyncpraw
import time

version = 'v3.5'

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
spam_id = os.getenv("spam_id")
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)
if not spam_id:
    print("[ERROR] Missing environment variable: spam_id")
    sys.exit(1)
if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"

# --- Reddit API setup (asyncpraw) ---
reddit = asyncpraw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

# --- Read Files ---
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
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

    # New Additions
    "NSFW_GIF", "TrueAmateurs", "AltGoneWild", "brunette",
    "redheads", "legalteensxxx", "fitgirls", "boobies",
    "asstastic", "NSFWVideos", "DeepThroat", "gonewildcurvy",
    "DirtyGaming", "nsfw_college", "facials", "hugeboobs",
    "Upskirt", "ThickFit", "NSFWFunny", "hairypussy",
    "NaughtyWives", "cumcovered", "ebony", "Latinas",
    "nsfw_videos", "BiggerThanYouThought", "FutanariGoneWild"
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
    "PhineasAndFerbNSFW",

    # New Additions
    "ecchibabes", "rule34cartoons", "LewdAnimeGirls",
    "OppaiHentai", "AnimeNsfw", "BunnyGirlsNSFW",
    "WaifuNsfw", "HentaiHQ", "AnimeEcchi", "nsfwanimegifs",
    "EcchiHentai", "HentaiCouples", "ShotaHentai",
    "MonsterGirlNSFW", "DoujinHentai", "HentaiThicc",
    "UncensoredEcchi", "LewdHentai", "AnimeNSFW",
    "CartoonRule34", "nsfwcosplayhentai", "EcchiWaifus"
]

# --- Safe Poketwo spam loop ---
@tasks.loop(seconds=10)
async def poketwo_spam_loop():
    channel = client.get_channel(int(spam_id))
    if not channel:
        print("Poketwo channel not found.")
        return
    message_content = ''.join(pyrandom.sample("1234567890", 7) * 5)
    try:
        await channel.send(message_content)
        print(f"[Poketwo] Sent spam: {message_content}")
    except Exception as e:
        print(f"[Poketwo Spam Error] {e}")

@poketwo_spam_loop.before_loop
async def before_poketwo_spam():
    await client.wait_until_ready()

# --- On ready ---
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user.name}')
    poketwo_spam_loop.start()
    asyncio.create_task(self_ping_loop())

# --- Self-ping loop ---
async def self_ping_loop():
    await client.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(service_url) as resp:
                    print(f"Pinged {service_url} - status: {resp.status}")
            except Exception as e:
                print(f"Error pinging self: {e}")
            await asyncio.sleep(600)

# --- NSFW helpers ---
async def get_filtered_posts(subreddit_name, content_type, limit=50):
    posts = []
    try:
        subreddit = await reddit.subreddit(subreddit_name)
        async for post in subreddit.hot(limit=limit):
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

# --- NSFW Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 10:
        await ctx.send("⚠️ Max 10 posts at once.")
        return
    if content_type not in ["img", "gif", "vid"]:
        await ctx.send("⚠️ Type must be one of: img, gif, vid.")
        return

    pool = nsfw_pool + hentai_pool
    results = []
    for _ in range(amount * 4):
        subreddit = pyrandom.choice(pool)
        posts = await get_filtered_posts(subreddit, content_type)
        if posts:
            results.append(pyrandom.choice(posts))
        if len(results) >= amount:
            break

    if results:
        for url in results[:amount]:
            await ctx.send(url)
    else:
        await ctx.send("❌ No posts found.")
        print(f"[r] No results for type {content_type}")

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 10:
        await ctx.send("⚠️ Max 10 posts at once.")
        return
    posts = await get_filtered_posts(subreddit, content_type)
    if posts:
        for url in posts[:amount]:
            await ctx.send(url)
    else:
        await ctx.send(f"❌ No posts found in r/{subreddit}.")

@client.command()
async def random(ctx):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    pool = nsfw_pool + hentai_pool
    subreddit = pyrandom.choice(pool)
    ctype = pyrandom.choice(["img", "gif", "vid"])
    posts = await get_filtered_posts(subreddit, ctype)
    if posts:
        await ctx.send(pyrandom.choice(posts))
    else:
        await ctx.send("❌ No posts found.")
        print(f"[random] No posts for r/{subreddit} type={ctype}")

# --- Auto System ---
auto_tasks = {}

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
    global auto_tasks
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if seconds < 5:
        await ctx.send("⚠️ Minimum is 5 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be one of: img, gif, vid, random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running in this channel.")
        return

    async def auto_loop(channel):
        while True:
            pool = nsfw_pool + hentai_pool
            ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
            subreddit = pyrandom.choice(pool)
            posts = await get_filtered_posts(subreddit, ctype)
            if posts:
                await channel.send(pyrandom.choice(posts))
            else:
                print(f"[auto] No posts in r/{subreddit} type={ctype}")
            await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started in this channel every {seconds}s for {content_type}.")

@client.command()
async def autostop(ctx):
    global auto_tasks
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped in this channel.")
    else:
        await ctx.send("⚠️ Auto was not running here.")

# --- Flask server ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# Start Flask server in a thread
threading.Thread(target=run_server).start()

# --- Run bot ---
while True:
    try:
        client.run(user_token)
    except Exception as e:
        print(f"Bot crashed: {e}. Restarting in 10 seconds...")
        time.sleep(10)
        
