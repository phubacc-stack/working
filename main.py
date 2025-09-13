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
from datetime import datetime, timezone
import html

# --- Suppress async warning ---
os.environ["PRAW_NO_ASYNC_WARNING"] = "1"

version = "v6.0-nsfw-master"

# --- Flask keep-alive server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# --- Discord Setup ---
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Pools (placeholders) ---
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
    # +20 extras
    "NSFWManga", "EcchiCosplay", "TentacleNSFW", "EcchiGirls",
    "LewdAnimeArt", "MonsterGirlHentai", "Rule34Anime", "DoujinWorlds",
    "CartoonEcchiNSFW", "AnimeSluts", "HentaiLovers", "WaifuPornNSFW",
    "HentaiDrops", "NSFW_Anime", "AnimeX
XX", "AnimeLewdGirls",
    "EcchiFantasy", "Rule34AnimeNSFW", "DoujinFans", "AnimeNudesHQ"
]

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=os.environ.get("reddit_client_id"),
    client_secret=os.environ.get("reddit_client_secret"),
    user_agent="discord-bot"
)

async def fetch_reddit(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    posts = [post async for post in subreddit.hot(limit=50)]
    if not posts:
        return None
    post = pyrandom.choice(posts)
    return post.url

# --- Rule34 Fetch ---
async def fetch_rule34(tag=None):
    url = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1"
    if tag:
        url += f"&tags={tag}"
    try:
        resp = requests.get(url, timeout=10).json()
        if not resp:
            return None
        post = pyrandom.choice(resp)
        return post.get("file_url")
    except:
        return None

# --- Gelbooru Fetch ---
async def fetch_gelbooru(tag=None):
    base = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1"
    if tag:
        base += f"&tags={tag}"
    try:
        resp = requests.get(base, timeout=10).json()
        if not resp:
            return None
        post = pyrandom.choice(resp)
        return post.get("file_url")
    except:
        return None

# --- Nekos.life Fetch ---
async def fetch_neko():
    try:
        resp = requests.get("https://nekos.life/api/v2/img/Random_hentai_gif").json()
        return resp.get("url")
    except:
        return None

# --- RedGifs Fetch ---
async def fetch_redgif_random():
    try:
        resp = requests.get("https://api.redgifs.com/v2/gifs/random").json()
        return resp.get("gif", {}).get("urls", {}).get("hd")
    except:
        return None

# --- Commands ---
@bot.command()
async def helpnsfw(ctx):
    commands_list = [
        "**Reddit:** !search <sub>, !autosub <sub> <delay>, !autostop, !pool",
        "**Rule34:** !r34 <tag>, !autor34 <tag> <delay>, !autostopr34, !r34pool",
        "**Gelbooru:** !gel <tag>, !autogel <tag> <delay>, !autostopgel",
        "**Nekos:** !nekonsfw, !autoneko <delay>, !autostopneko",
        "**RedGifs:** !redgif, !redgifsearch <tag>, !redgifuser <name>, !autoreddgif <delay>, !autostopredgif"
    ]
    await ctx.send("\n".join(commands_list))

@bot.command()
async def search(ctx, *, subreddit):
    url = await fetch_reddit(subreddit)
    if url:
        await ctx.send(url)
    else:
        await ctx.send("No posts found.")

@bot.command()
async def r34(ctx, *, tag=None):
    url = await fetch_rule34(tag)
    if url:
        await ctx.send(url)
    else:
        await ctx.send("Nothing found.")

@bot.command()
async def gel(ctx, *, tag=None):
    url = await fetch_gelbooru(tag)
    if url:
        await ctx.send(url)
    else:
        await ctx.send("Nothing found.")

@bot.command()
async def nekonsfw(ctx):
    url = await fetch_neko()
    if url:
        await ctx.send(url)
    else:
        await ctx.send("Nothing found.")

@bot.command()
async def redgif(ctx):
    url = await fetch_redgif_random()
    if url:
        await ctx.send(url)
    else:
        await ctx.send("Nothing found.")

# --- Run ---
keep_alive()
bot.run(os.environ["user_token"])
