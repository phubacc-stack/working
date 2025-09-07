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

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v4.5-self'
start_time = datetime.now(timezone.utc)
post_counter = 0

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
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

client = commands.Bot(command_prefix="!")

# --- Subreddit Pools (expanded, no removals) ---
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
    # --- Added more NSFW pools ---
    "CollegeAmateurs", "GoneErotic", "RealGirlsGW", "GoneWildPlus",
    "Curvy", "ThickChixxx", "AmateurMILFs", "HotMILFs", "CheatingWives",
    "PetiteGirls", "StackedGoneWild", "WifeSharing", "AmateurCumsluts",
    "SexyTummies", "GoneWildScrubs", "TightShirts", "UnderwearGW",
    "YogaPants", "NSFW_HTML5", "BustyPetites", "TittyDropGIFs",
    "PerfectAsses", "TrueAnal", "DeepFacials", "HardcoreAmateurs"
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
    # --- Added more Hentai pools ---
    "EcchiParadise", "LewdWaifu", "WaifuNSFW", "AnimeBooties",
    "MonsterHentai", "EcchiWorld", "TentacleHentai", "LewdFantasy",
    "GamerGirlHentai", "FutaHentai", "YuriHentai", "BondageHentai",
    "DoujinNsfw", "Rule34Hentai", "AnimePussy", "AnimeBoobs",
    "CartoonPorn", "AnimeLewds", "Rule34Cartoons", "UncensoredHentaiGIFs"
]

# --- Helper: Get unique posts with retries + gallery/imgur support ---
def get_filtered_posts(subreddit_name, content_type, limit=100, retries=3):
    posts = []
    for attempt in range(retries):
        try:
            subreddit = reddit.subreddit(subreddit_name)
            fetch_method = pyrandom.choice(["hot", "new", "top"])
            listings = getattr(subreddit, fetch_method)(limit=limit)

            for post in listings:
                if post.stickied:
                    continue
                url = str(post.url)

                # Handle reddit galleries
                if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                    for item in post.media_metadata.values():
                        if "s" in item and "u" in item["s"]:
                            posts.append(item["s"]["u"])
                    continue

                # Handle imgur albums
                if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                    continue
                if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                    url = url + ".jpg"

                if content_type == "img" and (
                    url.endswith((".jpg", ".jpeg", ".png"))
                    or "i.redd.it" in url or "preview.redd.it" in url
                ):
                    posts.append(url)

                elif content_type == "gif" and (
                    url.endswith(".gif") or "gfycat" in url
                    or "redgifs" in url or url.endswith(".gifv")
                ):
                    posts.append(url)

                elif content_type == "vid" and (
                    url.endswith(".mp4") or "v.redd.it" in url
                ):
                    posts.append(url)

            if posts:
                pyrandom.shuffle(posts)
                break

        except Exception as e:
            print(f"[Reddit Error] r/{subreddit_name} attempt {attempt+1}: {e}")
            time.sleep(1)

    return posts

# --- Auto System ---
auto_tasks = {}

async def safe_send(channel, url):
    try:
        await channel.send(url)
    except Exception as e:
        print(f"[Discord Error] Failed to send: {e}")

# --- Commands ---
@client.command()
async def r(ctx, amount: int = 1, content_type: str = "img"):
    """Pulls random post from NSFW pool"""
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 25:  # limit increased
        amount = 25
    pool = nsfw_pool + hentai_pool
    for _ in range(amount):
        sub = pyrandom.choice(pool)
        posts = get_filtered_posts(sub, content_type)
        if posts:
            url = pyrandom.choice(posts)
            await safe_send(ctx.channel, url)
            post_counter += 1
        else:
            await ctx.send("❌ No posts found.")

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    """Pulls random post from a specific subreddit"""
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 25:
        amount = 25
    posts = get_filtered_posts(subreddit, content_type)
    if posts:
        for _ in range(amount):
            url = pyrandom.choice(posts)
            await safe_send(ctx.channel, url)
            post_counter += 1
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
    """Start auto posting loop"""
    global auto_tasks
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if seconds < 5:
        await ctx.send("⚠️ Minimum 5 seconds.")
        return
    if content_type not in ["img", "gif", "vid", "random"]:
        await ctx.send("⚠️ Type must be img | gif | vid | random.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    async def auto_loop(channel):
        while True:
            try:
                pool = nsfw_pool + hentai_pool
                ctype = pyrandom.choice(["img", "gif", "vid"]) if content_type == "random" else content_type
                sub = pyrandom.choice(pool)
                posts = get_filtered_posts(sub, ctype)
                if posts:
                    await safe_send(channel, pyrandom.choice(posts))
                else:
                    print(f"[AutoLoop] No posts from r/{sub} ({ctype})")
                await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                print(f"[AutoLoop] Cancelled in {channel.id}")
                break
            except Exception as e:
                print(f"[AutoLoop Error] {e}")
                await asyncio.sleep(5)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ Auto started every {seconds}s for {content_type}.")

@client.command()
async def autostop(ctx):
    """Stop auto posting"""
    if ctx.channel.id in auto_tasks:
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def stats(ctx):
    """Show stats"""
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

@client.command()
async def uptime(ctx):
    """Show uptime"""
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"⏱️ Uptime: {uptime}")

@client.command()
async def search(ctx, keyword: str, amount: int = 1):
    """Search subreddits for keyword"""
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 25:
        amount = 25
    posts = []
    try:
        results = reddit.subreddits.search_by_name(keyword, include_nsfw=True)
        for sub in results:
            posts.extend(get_filtered_posts(sub.display_name, "img"))
    except Exception as e:
        await ctx.send(f"❌ Search error: {e}")
        return
    if posts:
        for _ in range(amount):
            url = pyrandom.choice(posts)
            await safe_send(ctx.channel, url)
            post_counter += 1
    else:
        await ctx.send("❌ No results.")

# --- Flask server ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

threading.Thread(target=run_server).start()

# --- Run bot (your restart loop preserved) ---
while True:
    try:
        client.run(user_token)
    except Exception as e:
        print(f"Bot crashed: {e}. Restarting in 10s...")
        time.sleep(10)
                                 
