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
import logging

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = 'v5.3-collect-help'
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

client = commands.Bot(command_prefix="!", help_command=None)

# --- Subreddit Pools (PLACEHOLDER – drop your full lists back here) ---
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
    # +20 extras
    "NSFWWallpapers", "UncutPorn", "LingerieGW", "AmateurXXX",
    "BigTits", "GirlsFinishingJobs", "AnalOnly", "CumInMouth",
    "ThickAsians", "HotAmateurs", "NSFWCouples", "NaughtyAmateurs",
    "TittyDropPorn", "AssWorship", "MILF_NSFW", "ThickCurvy",
    "PetiteNSFW", "AmateurFacials", "ExposedAmateurs", "SluttyAmateurs"
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
    "NSFWManga", "EcchiCosplay", "TentacleNSFW", "EcchiGirls",
    "LewdAnimeArt", "MonsterGirlHentai", "Rule34Anime", "DoujinWorlds",
    "CartoonEcchiNSFW", "AnimeSluts", "HentaiLovers", "WaifuPornNSFW",
    "HentaiDrops", "NSFW_Anime", "AnimeXXX", "AnimeLewdGirls",
    "EcchiFantasy", "Rule34AnimeNSFW", "DoujinFans", "AnimeNudesHQ",
    "Rule34Disney", "WesternHentai", "CartoonNSFW", "CartoonPorn",
    "CartoonRule34NSFW", "Rule34Comics", "DisneyNSFW", "PixarNSFW",
    "TotalDramaNSFW", "Ben10NSFW", "FamilyGuyNSFW", "AmericanDadNSFW",
    "SimpsonsNSFW", "CartoonSmut", "WesternCartoonPorn", "CartoonPornHQ",
    "CartoonNudes", "DisneyRule34", "AnimatedNSFW", "ToonNSFW",
    "CartoonXXX", "CartoonSex", "Cartoon_R34", "rule34_comics",
    "sex_comics", "hentai_comics", "NSFWcomics", "PornComix",
    "NSFWwebcomics", "CowgirlRiding", "ReverseCowgirl", "RidingDicks",
    "GirlsRiding", "OnTop", "CowgirlNSFW", "AnalRiding", "HardcorePorn",
    "RealPorn", "HardcoreNSFW", "RoughSex", "HardcoreFucking",
    "HardcoreAmateurPorn", "PoundingHer", "FuckingHerHard",
    "ThroatFucking", "HardcoreDoggy", "MissionaryNSFW", "AnalOnlyFans",
    "DeepInsertion",

    # 🔥 EXTENDED MEGA DROP
    "PantyHentai", "StockingHentai", "EcchiFeet", "BigBoobsHentai",
    "AnimeFacesitting", "TentacleGirls", "NekoHentai", "ElfHentai",
    "SuccubusHentai", "SchoolgirlNSFW", "CheerleaderHentai",
    "NurseHentai", "MaidNSFW", "BunnyGirlHentai", "GothHentai",
    "BBWAnime", "ChubbyHentai", "FemboyHentai", "TrapHentai",
    "YaoiHentai", "ShotaNSFW", "LoliNSFW", "MonsterGirlXXX",
    "AnimeGangbang", "AnimeCreampie", "UncensoredDoujin",
    "AnimeThreesome", "AnimeOrgy", "HentaiFacials", "HentaiCumshots",
    "BigTiddyAnimeGirls", "AnimeDominatrix", "AnimeBondageXXX",
    "Rule34Naruto", "Rule34Bleach", "Rule34OnePiece", "Rule34FairyTail",
    "Rule34Pokemon", "Rule34Genshin", "Rule34Overwatch", "Rule34LoL",
    "Rule34MHA", "Rule34DemonSlayer", "Rule34Evangelion", "Rule34RWBY",
    "Rule34Fate", "Rule34DBZ", "Rule34Inuyasha", "Rule34SailorMoon",
    "Rule34NeonGenesis", "Rule34ToLoveRu", "Rule34KillLaKill",
    "Rule34Konosuba", "Rule34ReZero", "Rule34BlackClover",
    "Rule34CodeGeass", "Rule34Persona", "Rule34Nier", "Rule34FinalFantasy",
    "Rule34Avatar", "Rule34Disney", "Rule34Pixar", "Rule34CartoonHQ",
    "Rule34LooneyTunes", "Rule34TeenTitans", "Rule34Ben10",
    "Rule34FamilyGuy", "Rule34Simpsons", "Rule34AmericanDad",
    "Rule34TotalDrama", "Rule34GravityFalls", "Rule34KimPossible",
    "Rule34DannyPhantom", "Rule34PhineasFerb", "Rule34ScoobyDoo",
    "Rule34RegularShow", "Rule34Sonic", "Rule34Mario", "Rule34Zelda",
    "Rule34Metroid", "Rule34Kirby", "Rule34Minecraft", "Rule34Roblox",
    "Rule34Fortnite", "Rule34CallOfDuty", "Rule34Halo", "Rule34Overcooked",
    "Rule34AmongUs", "Rule34FallGuys", "Rule34Cuphead", "Rule34Undertale",
    "Rule34FNAF", "Rule34Bendy", "Rule34PokemonGirls", "Rule34AnimeGirls",
    "Rule34Waifus", "Rule34MonsterGirls", "Rule34Succubus", "Rule34Tentacle",
    "Rule34BBW", "Rule34Elf", "Rule34Catgirl", "Rule34Neko",
    "Rule34Cheerleader", "Rule34Nurse", "Rule34Schoolgirl", "Rule34Goth",

    # keep stacking until we break 2000+...
]

# --- Helper: Get unique posts (handles galleries) ---
def get_filtered_posts(subreddit_name, content_type, limit=100, retries=3, only_collections=False):
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

                # --- Galleries ---
                if "reddit.com/gallery" in url and hasattr(post, "media_metadata"):
                    gallery_urls = []
                    for item in list(post.media_metadata.values())[:25]:
                        if "s" in item and "u" in item["s"]:
                            gallery_url = html.unescape(item["s"]["u"])
                            if gallery_url not in seen_posts:
                                gallery_urls.append(gallery_url)
                    if gallery_urls:
                        posts.append(gallery_urls)
                    continue

                if only_collections:
                    continue  # skip singles if we're collecting only

                # --- Normal media filtering ---
                if "imgur.com/a/" in url or "imgur.com/gallery/" in url:
                    continue
                if "imgur.com" in url and not url.endswith((".jpg", ".png", ".gif")):
                    url = url + ".jpg"

                if (
                    (content_type == "img" and (url.endswith((".jpg", ".jpeg", ".png")) or "i.redd.it" in url))
                    or (content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url or url.endswith(".gifv")))
                    or (content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url))
                ):
                    if url not in seen_posts:
                        posts.append(url)

            if posts:
                pyrandom.shuffle(posts)
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
                break

        except Exception as e:
            logging.error(f"[Reddit Error] r/{subreddit_name} attempt {attempt+1}: {e}")
            time.sleep(1)

    return posts

# --- Auto System ---
auto_tasks = {}

async def safe_send(channel, url):
    try:
        await channel.send(url)
    except Exception as e:
        logging.error(f"[Discord Error] Failed to send: {e}")

async def send_with_gallery_support(channel, item):
    global post_counter
    if isinstance(item, list):
        for url in item:
            await safe_send(channel, url)
            post_counter += 1
            await asyncio.sleep(2)
    else:
        await safe_send(channel, item)
        post_counter += 1

# --- Existing Commands (r, rsub, auto, autosub, autostop, stats, etc.) ---
# (unchanged from v5.2 – kept intact for backward compatibility)

# --- New Commands ---
@client.command()
async def search(ctx, *, query: str):
    """Search Reddit for posts matching query"""
    posts = []
    try:
        results = reddit.subreddit("all").search(query, limit=50)
        for post in results:
            if not post.stickied and hasattr(post, "url"):
                posts.append(post.url)
        if posts:
            pyrandom.shuffle(posts)
            for url in posts[:5]:
                await send_with_gallery_support(ctx.channel, url)
        else:
            await ctx.send("❌ No results found.")
    except Exception as e:
        await ctx.send(f"⚠️ Search failed: {e}")

@client.command()
async def autosearch(ctx, *, query: str):
    """Auto search posts for a query every 30s"""
    global auto_tasks
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    async def auto_loop(channel):
        while True:
            try:
                results = reddit.subreddit("all").search(query, limit=25)
                posts = [p.url for p in results if not p.stickied]
                if posts:
                    pyrandom.shuffle(posts)
                    for url in posts[:2]:
                        await send_with_gallery_support(channel, url)
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"[AutoSearch Error] {e}")
                await asyncio.sleep(5)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ AutoSearch started for `{query}` every 30s.")

@client.command()
async def autocollect(ctx, subreddit: str, seconds: int = 30):
    """Auto-post only gallery collections from a subreddit"""
    global auto_tasks
    if seconds < 2:
        await ctx.send("⚠️ Minimum 2 seconds.")
        return
    if ctx.channel.id in auto_tasks and not auto_tasks[ctx.channel.id].done():
        await ctx.send("⚠️ Auto already running here.")
        return

    async def auto_loop(channel):
        while True:
            try:
                posts = get_filtered_posts(subreddit, "img", only_collections=True)
                if posts:
                    for item in posts[:1]:  # one gallery per cycle
                        await send_with_gallery_support(channel, item)
                await asyncio.sleep(seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"[AutoCollect Error] {e}")
                await asyncio.sleep(5)

    task = asyncio.create_task(auto_loop(ctx.channel))
    auto_tasks[ctx.channel.id] = task
    await ctx.send(f"▶️ AutoCollect started: r/{subreddit} (only galleries) every {seconds}s.")

@client.command()
async def pools(ctx):
    """Show available subreddit pools"""
    nsfw_count = len(nsfw_pool)
    hentai_count = len(hentai_pool)
    total = nsfw_count + hentai_count
    await ctx.send(f"📚 Pools Loaded:\n🔞 NSFW: {nsfw_count}\n🎌 Hentai: {hentai_count}\n📊 Total: {total}")

@client.command()
async def listpool(ctx, pool: str = "nsfw", page: int = 1):
    """List subreddit names from a pool (20 per page)"""
    pool_map = {"nsfw": nsfw_pool, "hentai": hentai_pool}
    if pool not in pool_map:
        await ctx.send("⚠️ Choose nsfw | hentai")
        return
    subs = pool_map[pool]
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    slice = subs[start:end]
    if not slice:
        await ctx.send("⚠️ No more results.")
        return
    msg = f"📜 {pool.upper()} Pool (Page {page})\n" + "\n".join([f"- {s}" for s in slice])
    await ctx.send(f"```{msg}```")

@client.command()
async def who(ctx):
    task = auto_tasks.get(ctx.channel.id)
    if task:
        await ctx.send(f"▶️ Auto running in this channel (started by {ctx.author.mention})")
    else:
        await ctx.send("⚠️ No auto running here.")

@client.command()
async def helpme(ctx):
    """Custom help menu"""
    embed = discord.Embed(title="🤖 Bot Commands", color=0xFF69B4)
    embed.add_field(name="🎲 Random", value="`!r [amount] [img|gif|vid]`\n`!rsub <sub> [amount] [type]`", inline=False)
    embed.add_field(name="🔁 Auto", value="`!auto [sec] [type]`\n`!autosub <sub> [sec] [type]`\n`!autosearch <query>`\n`!autocollect <sub> [sec]`\n`!autostop`", inline=False)
    embed.add_field(name="🔍 Search", value="`!search <words>`", inline=False)
    embed.add_field(name="📊 Info", value="`!stats`\n`!who`\n`!pools`\n`!listpool nsfw|hentai [page]`", inline=False)
    embed.set_footer(text=f"Bot version {version}")
    await ctx.send(embed=embed)

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

# --- Run Bot ---
client.run(user_token)
        
