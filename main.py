import os
import sys
import asyncio
import random as pyrandom
import discord
from discord.ext import commands, tasks
import threading
from flask import Flask
import requests
import time
import praw

version = 'v4.0'

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

# --- Reddit API setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

poketwo = 716390085896962058
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# --- Subreddit Pools (Massive) ---
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
    "NSFW_GIF", "TrueAmateurs", "AltGoneWild", "brunette", "redheads",
    "legalteensxxx", "fitgirls", "boobies", "asstastic", "NSFWVideos",
    "DeepThroat", "gonewildcurvy", "DirtyGaming", "nsfw_college",
    "facials", "hugeboobs", "Upskirt", "ThickFit", "NSFWFunny",
    "hairypussy", "NaughtyWives", "cumcovered", "ebony", "Latinas",
    "nsfw_videos", "BiggerThanYouThought", "FutanariGoneWild",
    # Extra expansion:
    "RealGirlsGW", "slutsofreddit", "NSFW_HTML5", "porn_gifs",
    "chubby", "amateur_milfs", "gonewildcouples", "shemales", "traps",
    "publicsex", "nsfw_Porn_GIFs", "nsfwdeepthroat", "OralCreampie",
    "cfnm", "bondage", "TabooPorn", "OnlyFansGirls101"
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
    "EcchiHentai", "HentaiCouples", "MonsterGirlNSFW",
    "DoujinHentai", "HentaiThicc", "UncensoredEcchi", "LewdHentai",
    "AnimeNSFW", "CartoonRule34", "nsfwcosplayhentai", "EcchiWaifus",
    # Extra expansion:
    "TrainerFucks", "rule34hentai", "AnimeCumsluts", "ThiccAnime",
    "FutaHentai", "AnimeOral", "BigAnimeAss", "TentaclePorn",
    "DoujinshiNSFW", "UncensoredHentaiGIFs"
]

# --- Poketwo Spam Loop ---
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
    while True:
        try:
            r = requests.get(service_url)
            print(f"Pinged {service_url} - status: {r.status_code}")
        except Exception as e:
            print(f"Error pinging self: {e}")
        await asyncio.sleep(600)

# --- NSFW helpers ---
def get_filtered_posts(subreddit_name, content_type, limit=50):
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.hot(limit=limit):
            if post.stickied:
                continue
            url = str(post.url)

            if content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url):
                posts.append(url)
            elif content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")):
                posts.append(url)
            elif content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url):
                posts.append(url)
    except Exception as e:
        print(f"[Reddit Error] r/{subreddit_name}: {e}")
    return posts

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 10:
        await ctx.send("⚠️ Max 10 posts.")
        return

    pool = nsfw_pool + hentai_pool
    results = []
    for _ in range(amount * 6):  # oversample
        subreddit = pyrandom.choice(pool)
        posts = get_filtered_posts(subreddit, content_type)
        if posts:
            results.append(pyrandom.choice(posts))
        if len(results) >= amount:
            break

    if results:
        for url in results[:amount]:
            await ctx.send(url)
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    posts = get_filtered_posts(subreddit, content_type)
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
    posts = get_filtered_posts(subreddit, ctype)
    if posts:
        await ctx.send(pyrandom.choice(posts))
    else:
        await ctx.send("❌ No posts found.")

# --- Auto system ---
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
        await ctx.send("⚠️ Auto already running.")
        return

    async def auto_loop(channel):
        while True:
            pool = nsfw_pool + hentai_pool
            ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
            subreddit = pyrandom.choice(pool)
            posts = get_filtered_posts(subreddit, ctype)
            if posts:
                await channel.send(pyrandom.choice(posts))
            await asyncio.sleep(seconds)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started every {seconds}s for {content_type}.")

@client.command()
async def autostop(ctx):
    global auto_tasks
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ Auto was not running.")

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
        
