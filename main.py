import os
import sys
import re
import asyncio
import random
import discord
from discord.ext import commands, tasks
import threading
from flask import Flask
import requests
import time
import praw

version = 'v3.0'

# --- Discord Environment Variables ---
user_token = os.getenv("user_token")
spam_id = os.getenv("spam_id")
service_url = os.getenv("SERVICE_URL")  # Optional: Render URL for self-ping

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

if not spam_id:
    print("[ERROR] Missing environment variable: spam_id")
    sys.exit(1)

if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"  # fallback

# --- Reddit API setup (hardcoded) ---
reddit = praw.Reddit(
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
    "justthetip", "60fpsporn", "porninfifteenseconds",
    "cuckold", "anal", "blowjobsandwich", "tightdresses", "leggingsgonewild",
    "SuicideGirls", "nsfwoutfits", "ToplessInJeans", "publicplug",
    "workoutgonewild", "Hotwife", "MomsGoneWild", "milf", "hotchickswithtattoos",
    "nsfwcosplay", "BDSMGW", "pussy", "gwcumsluts", "squirting_gifs",
    "thickwhitegirls", "slutwife", "PornStars", "PerfectPussies",
    "realgirls", "SexyGirlsInBoots", "nsfw2", "Blonde", "nsfwoutfits2",
    "nsfwart", "rearpussy", "workplacegonewild", "MatureMilfs",
    "bustypetite2", "analgw", "thickasses", "Stacked",
    "TrickshotCum", "AmateurCumsluts", "cumcoveredfucking",
    "Assholes", "GirlsWithBigToys", "O_Faces", "GirlsInYogaPants"
]

hentai_pool = [
    "hentai", "rule34", "AnimeBooty", "thick_hentai", "ahegao",
    "ecchi", "hentaibondage", "oppai_gif", "HQHentai", "HentaiGIF",
    "NarutoHentai", "DragonBallHentai", "PokemonNSFW",
    "DisneyNSFW", "OverwatchNSFW", "OnePieceHentai",
    "AnimeArmpits", "BigAnimeTiddies", "MaidHentai", "MonsterGirls",
    "hentai_gifs", "HentaiBlowjobs", "thighhighs", "animelegs",
    "Tentai", "HentaiAnal", "futa", "UncensoredHentai", "YuriNSFW",
    "AnimeMILFS", "WaifuPorn", "hentaiass", "ecchiGIFs",
    "TouhouNSFW", "BDSMhentai", "DragonBallZNSFW", "NarutoRule34",
    "FairyTailNSFW", "BleachNSFW", "DigimonNSFW", "HentaiThighs",
    "HentaiPetgirls", "LeagueOfLegendsNSFW", "GenshinImpactNSFW",
    "SailorMoonNSFW", "EvangelionNSFW", "FateHentai",
    "hentaicaptions", "OverwatchHentai", "RWBYNSFW",
    "AvatarNSFW", "KantaiCollectionNSFW", "ReZeroNSFW",
    "KonosubaNSFW", "MyHeroHentai", "DemonSlayerHentai",
    "OnePunchManNSFW", "AttackOnTitanNSFW", "InuyashaNSFW",
    "CodeGeassNSFW", "BlackCloverNSFW", "BorutoHentai",
    "YuGiOhNSFW", "KillLaKillNSFW", "PersonaNSFW", "NierNSFW",
    "FinalFantasyNSFW", "DisneyHentai", "CartoonHentai",
    "GravityFallsNSFW", "KimPossibleNSFW", "TeenTitansNSFW",
    "ScoobyDooNSFW", "LooneyTunesNSFW", "RegularShowNSFW",
    "TotalDramaNSFW", "DannyPhantomNSFW", "PhineasAndFerbNSFW"
]

# --- Spam intervals ---
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

# --- Solve hints ---
def solve(message, file_name):
    hint = [c for c in message[15:-1] if c != '\\']
    hint_string = ''.join(hint).replace('_', '.')
    with open(file_name, "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_string}$', solutions, re.MULTILINE)
    return solution if solution else None

# --- Safe message sender ---
async def send_message_safe(channel, content):
    while True:
        try:
            await channel.send(content)
            break
        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', 5)
                print(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
            else:
                print(f"HTTPException: {e}. Retrying in 60 seconds...")
                await asyncio.sleep(60)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)

# --- Spam loop ---
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    if not channel:
        print("Channel not found.")
        return
    message_content = ''.join(random.sample('1234567890', 7) * 5)
    await send_message_safe(channel, message_content)

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# --- On ready ---
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    spam.start()
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

# --- Move to category ---
async def move_to_category(channel, solution, base_category_name, guild, max_channels=48, max_categories=5):
    for i in range(1, max_categories + 1):
        category_name = f"{base_category_name} {i}" if i > 1 else base_category_name
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)
        if len(category.channels) < max_channels:
            await channel.edit(
                name=solution.lower().replace(' ', '-'),
                category=category,
                sync_permissions=True,
            )
            return

# --- Commands ---
@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if spam.is_running():
        spam.cancel()
        await ctx.send("Spam loop stopped.")
    spam.start()
    await ctx.send("Spam loop restarted.")

@client.command()
async def pause(ctx):
    spam.cancel()

# --- NSFW helpers ---
def get_filtered_posts(subreddit_name, content_type, limit=50):
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.hot(limit=limit):
            if post.stickied:
                continue
            url = str(post.url)
            if content_type == "img" and any(url.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                posts.append(url)
            elif content_type == "gif" and (url.endswith(".gif") or "gfycat" in url or "redgifs" in url):
                posts.append(url)
            elif content_type == "vid" and (url.endswith(".mp4") or "v.redd.it" in url):
                posts.append(url)
    except Exception as e:
        print(f"Failed to fetch from r/{subreddit_name}: {e}")
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

    pool = nsfw_pool + hentai_pool
    results = []
    for _ in range(amount * 3):  # oversample for safety
        subreddit = random.choice(pool)
        posts = get_filtered_posts(subreddit, content_type)
        if posts:
            results.append(random.choice(posts))
        if len(results) >= amount:
            break

    if results:
        for url in results[:amount]:
            await ctx.send(url)
    else:
        await ctx.send("❌ No posts found.")

@client.command()
async def random(ctx):
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    pool = nsfw_pool + hentai_pool
    subreddit = random.choice(pool)
    posts = get_filtered_posts(subreddit, random.choice(["img", "gif", "vid"]))
    if posts:
        await ctx.send(random.choice(posts))
    else:
        await ctx.send("❌ No posts found.")

auto_task = None

@client.command()
async def auto(ctx, seconds: int = 30):
    global auto_task
    if not ctx.channel.is_nsfw():
        await ctx.send("⚠️ NSFW only command.")
        return
    if seconds < 10:
        await ctx.send("⚠️ Minimum is 10 seconds.")
        return
    if auto_task and not auto_task.done():
        await ctx.send("⚠️ Auto already running.")
        return

    async def auto_loop():
        while True:
            pool = nsfw_pool + hentai_pool
            subreddit = random.choice(pool)
            posts = get_filtered_posts(subreddit, random.choice(["img", "gif", "vid"]))
            if posts:
                await ctx.send(random.choice(posts))
            await asyncio.sleep(seconds)

    auto_task = asyncio.create_task(auto_loop())
    await ctx.send(f"▶️ Auto started every {seconds}s.")

@client.command()
async def autostop(ctx):
    global auto_task
    if auto_task and not auto_task.done():
        auto_task.cancel()
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
        print(f"Bot crashed: {e}. Restarting in 10 seconds...")
        time.sleep(10)
