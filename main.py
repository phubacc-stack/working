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

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.0-gallery'
start_time = datetime.now(timezone.utc)
post_counter = 0
seen_posts = set()

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

# --- Subreddit Pools (yours, untouched, only added a few extras at the end) ---
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
    "NotSafeForWork", "LegalTeens", "CollegeAmateurs", "GoneErotic",
    "RealGirlsGW", "GoneWildPlus", "Curvy", "ThickChixxx",
    "AmateurMILFs", "HotMILFs", "CheatingWives", "PetiteGirls",
    "StackedGoneWild", "WifeSharing", "AmateurCumsluts",
    "SexyTummies", "GoneWildScrubs", "TightShirts", "UnderwearGW",
    "YogaPants", "NSFW_HTML5", "BustyPetites", "TittyDropGIFs",
    "PerfectAsses", "TrueAnal", "DeepFacials", "HardcoreAmateurs",
    "OnlyFansGirls", "OnlyFansNSFW", "ThickChicks", "GoneWild18",
    "BimboGirls", "NSFW_Selfies", "BigAsses", "NSFW_Snap", "Ofaces",
    "AmateurWives", "ExhibitionistSex", "ShowerGirls", "BedroomAmateurs",
    "NSFW_Galleries", "SexyAsians", "ThickLatinas", "BustyAmateurs",
    "EroticArt", "HomeMadeXXX", "SluttyGirls", "AmateurExposed",
    "PawgHQ", "TittyTuesday", "GoneWildAudio", "ThickAndBusty",
    "AmateurThreesomes", "AmateurCouples", "AmateurGirls",
    "AmateurNudes", "AmateurExhibition", "BigBoobsAmateurs",
    "BustyAmateurs", "CurvyAmateurs", "SexyLatinas", "SexyEbony",
    "SexyRedheads", "SexyBlondes", "SexyBrunettes",
    # added extras
    "BigBoobs", "RealGirlsNSFW", "TrueGoneWild", "AmateurXXX"
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
    "EcchiParadise", "LewdWaifu", "WaifuNSFW", "AnimeBooties",
    "MonsterHentai", "EcchiWorld", "TentacleHentai", "LewdFantasy",
    "GamerGirlHentai", "FutaHentai", "YuriHentai", "BondageHentai",
    "DoujinNsfw", "Rule34Hentai", "AnimePussy", "AnimeBoobs",
    "CartoonPorn", "AnimeLewds", "Rule34Cartoons", "UncensoredHentaiGIFs",
    "AnimeNudes", "LewdHentaiGirls", "EcchiBooty", "AnimeAhegao",
    "CartoonEcchi", "AnimeBDSM", "Rule34_NSFW", "MangaHentai",
    "EcchiHQ", "LewdAnime", "AnimeGifsNSFW", "CartoonEcchiPorn",
    "DoujinWorld", "HentaiVerse", "LewdFantasyGirls", "Rule34CartoonHQ",
    # added extras
    "EcchiDreams", "Hentai_Uncensored", "AnimeLewdsHQ"
]

# --- Helper: Get unique posts (handles galleries) ---
def get_filtered_posts(subreddit_name, content_type, limit=100, retries=3):
    global seen_posts
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

                # Handle reddit galleries (send ALL images together)
                if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                    gallery_urls = []
                    for item in post.media_metadata.values():
                        if "s" in item and "u" in item["s"]:
                            gallery_url = html.unescape(item["s"]["u"])
                            if gallery_url not in seen_posts:
                                gallery_urls.append(gallery_url)
                    if gallery_urls:
                        posts.append(gallery_urls)
                    continue

                # Handle imgur albums
                if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                    continue
                if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                    url = url + ".jpg"

                # Match content type + dedupe
                if (
                    (content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url))
                    or (content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")))
                    or (content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url))
                ):
                    if url not in seen_posts:
                        posts.append(url)

            if posts:
                pyrandom.shuffle(posts)
                flat_posts = []
                for p in posts:
                    if isinstance(p, list):
                        flat_posts.extend(p)
                    else:
                        flat_posts.append(p)
                seen_posts.update(flat_posts)

                if len(seen_posts) > 5000:
                    seen_posts.clear()
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
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
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
            for p in posts:
                if len(collected) >= amount:
                    break
                collected.append(p)
        tries += 1

    if collected:
        for p in collected:
            if isinstance(p, list):  # gallery
                for url in p:
                    await safe_send(ctx.channel, url)
                    post_counter += 1
                    await asyncio.sleep(1)
            else:
                await safe_send(ctx.channel, p)
                post_counter += 1
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def rsub(ctx, subreddit: str, amount: int = 1, content_type: str = "img"):
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 50:
        amount = 50

    collected = []
    tries = 0
    max_tries = amount * 3

    while len(collected) < amount and tries < max_tries:
        posts = get_filtered_posts(subreddit, content_type)
        if posts:
            for p in posts:
                if len(collected) >= amount:
                    break
                collected.append(p)
        tries += 1

    if collected:
        for p in collected:
            if isinstance(p, list):  # gallery
                for url in p:
                    await safe_send(ctx.channel, url)
                    post_counter += 1
                    await asyncio.sleep(1)
            else:
                await safe_send(ctx.channel, p)
                post_counter += 1
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def auto(ctx, seconds: int = 30, content_type: str = "img"):
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
                    for p in posts:
                        if isinstance(p, list):  # gallery
                            for url in p:
                                await safe_send(channel, url)
                                await asyncio.sleep(1)
                        else:
                            await safe_send(channel, p)
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
    if ctx.channel.id in auto_tasks:
        auto_tasks[ctx.channel.id].cancel()
        await ctx.send("⏹️ Auto stopped.")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def stats(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"📊 Posts sent: {post_counter}\n⏱️ Uptime: {uptime}\n⚙️ Version: {version}")

@client.command()
async def uptime(ctx):
    uptime = datetime.now(timezone.utc) - start_time
    await ctx.send(f"⏱️ Uptime: {uptime}")

@client.command()
async def search(ctx, keyword: str, amount: int = 1):
    global post_counter
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if amount > 50:
        amount = 50
    posts = []
    try:
        results = reddit.subreddits.search_by_name(keyword, include_nsfw=True)
        for sub in results:
            posts.extend(get_filtered_posts(sub.display_name, "img"))
    except Exception as e:
        await ctx.send(f"❌ Search error: {e}")
        return
    if posts:
        for url in posts[:amount]:
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

# --- Run bot ---
while True:
    try:
        client.run(user_token, log_handler=None)
    except Exception as e:
        print(f"[FATAL] Discord error: {e}")
        time.sleep(5)
        
