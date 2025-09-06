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
service_url = os.getenv("SERVICE_URL")

if not user_token:
    print("[ERROR] Missing environment variable: user_token")
    sys.exit(1)

if not spam_id:
    print("[ERROR] Missing environment variable: spam_id")
    sys.exit(1)

if not service_url:
    service_url = "https://working-1-uy7j.onrender.com"  # fallback

# --- Reddit API setup ---
reddit = praw.Reddit(
    client_id="lQ_-b50YbnuDiL_uC6B7OQ",
    client_secret="1GqXW2xEWOGjqMl2lNacWdOc4tt9YA",
    user_agent="NsfwDiscordBot/1.0"
)

# --- NSFW subreddit pools ---
real_subs = [
    "nsfw", "gonewild", "RealGirls", "amateurs", "nsfw_gifs", "gwcouples", "PetiteGoneWild",
    "gonewild30plus", "Nude_Selfie", "Amateur", "NSFW_Snapchat", "Hotchickswithtattoos",
    "Thick", "BiggerThanYouThought", "LegalTeens", "CollegeAmateurs", "RealNSFW", "AmateurPorn",
    "gonewildcolor", "milf", "nsfw_videos", "CasualNSFW", "AssholeBehindThong", "OnOff", "Boobies",
    "tittydrop", "GodPussy", "pawg", "HappyEmbarrassedGirls", "Blowjobs", "cumsluts", "AnalGW",
    "AmateurGirls", "CandidFashionPolice", "GirlsFinishingTheJob", "homemadexxx", "randomsexiness",
    "TooHotForYou", "exxxtras", "funsized", "nsfwhardcore", "gwcumsluts", "pawg_gonewild",
    "nsfwoutfits", "NaughtyWives", "thickfit", "tightdresses", "thicker", "BBWGW", "ThickThighs",
    "curvy", "latinas", "asianhotties", "gonewildcurvy", "PetiteGoneWild", "dirtysmall",
    "altgonewild", "suicidegirls", "GirlsWithToys", "AmateurSluts", "Facials", "GoneErotic",
    "Rule34Real", "WorkGoneWild", "BarelyLegal", "NSFW_Outdoors", "public", "snapleaks",
    "AmateurRoom", "NSFWfashion", "TheUnderboob", "stockings", "panties", "lingerie", "nsfwoutfits",
    "slutsofsnapchat", "Hotwife", "wifesharing", "cuckold", "AmateurPornVideos"
]

hentai_subs = [
    "hentai", "rule34", "AnimeHentai", "HENTAI_GIF", "hentaibondage", "thick_hentai", "ecchi",
    "hentaipics", "hentaibabes", "OppaiLove", "animelegs", "pantsu", "rule34cartoonporn",
    "WesternHentai", "CartoonRule34", "ParodyHentai", "rule34lol", "cartoonporn", "Futanari",
    "BigAnimeTiddies", "MangaHentai", "Rule34Cartoons", "nsfwanime", "ecchihentai", "HentaiSource",
    "ThickHentaiGirls", "MonsterGirl", "LewdAnimeGirls", "nsfwanimegifs", "Rule34Cartoon", 
    "AlternativeHentai", "UncensoredHentai", "DoujinshiHentai", "HentaiAnal", "NSFWAnime",
    "BigAnimeButts", "DBZHentai", "NarutoHentai", "PokemonHentai", "DisneyHentai", "CartoonHentai",
    "cartoonpornhub", "OverwatchNSFW", "LeagueOfLegendsNSFW", "AnimeBooty", "rule34comics",
    "CartoonPornPics", "AnimatedHentai", "SexyCartoonGirls", "ThiccHentai", "AnimePorn", 
    "EcchiParadise", "rule34gif", "cartoonnsfw", "AnimeNSFWgif", "GifsHentai", "DisneyRule34",
    "DragonBallNSFW", "NarutoNSFW", "PokemonRule34", "AnimeNSFWwallpapers", "cartoonrule34gifs",
    "WesternRule34", "CartoonPornArt", "AnimeGirlsNSFW", "CartoonSmut", "ParodyCartoonPorn",
    "AnimeLewd", "rule34all", "CartoonPornGallery", "EcchiHentai", "WesternCartoonHentai",
    "CrossoverHentai", "AnimeTitties", "AnimeFetish", "CartoonLewd", "AnimeRule34"
]

# --- Read Files ---
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r', encoding='utf8') as file:
    mythical_list = file.read()

poketwo = 716390085896962058
client = commands.Bot(command_prefix="!")

intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

def solve(message, file_name):
    hint = [c for c in message[15:-1] if c != '\\']
    hint_string = ''.join(hint).replace('_', '.')
    with open(file_name, "r") as f:
        solutions = f.read()
    solution = re.findall(f'^{hint_string}$', solutions, re.MULTILINE)
    return solution if solution else None

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
                print(f"HTTPException: {e}. Retrying in 60s...")
                await asyncio.sleep(60)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 60s...")
            await asyncio.sleep(60)

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    if channel:
        message_content = ''.join(random.sample('1234567890', 7) * 5)
        await send_message_safe(channel, message_content)

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Logged in as: {client.user.name}')
    spam.start()
    asyncio.create_task(self_ping_loop())

async def self_ping_loop():
    await client.wait_until_ready()
    while True:
        try:
            r = requests.get(service_url)
            print(f"Pinged {service_url} - status {r.status_code}")
        except Exception as e:
            print(f"Self ping failed: {e}")
        await asyncio.sleep(600)

@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category:
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                try:
                    def check(m):
                        return m.author.id == poketwo and m.channel == message.channel and m.content.startswith("Congratulations")
                    await client.wait_for('message', timeout=55.0, check=check)
                except asyncio.TimeoutError:
                    await message.channel.send('<@716390085896962058> h')
    await client.process_commands(message)

async def move_to_category(channel, solution, base_category_name, guild, max_channels=48, max_categories=5):
    for i in range(1, max_categories + 1):
        category_name = f"{base_category_name} {i}" if i > 1 else base_category_name
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)
        if len(category.channels) < max_channels:
            await channel.edit(name=solution.lower().replace(' ', '-'), category=category, sync_permissions=True)
            return

# --- Helper: fetch Reddit post (handles gallery/media) ---
def fetch_post(subreddit_name, limit=50):
    subreddit = reddit.subreddit(subreddit_name)
    posts = [p for p in subreddit.hot(limit=limit) if not p.stickied]
    if not posts:
        return None
    post = random.choice(posts)
    media_urls = []
    if hasattr(post, "is_gallery") and post.is_gallery:
        for item in post.gallery_data["items"]:
            media_id = item["media_id"]
            media_urls.append(post.media_metadata[media_id]["s"]["u"])
    elif post.url.endswith((".jpg", ".png", ".gif", ".mp4", ".webm")):
        media_urls.append(post.url)
    elif post.url.startswith("https://v.redd.it"):
        media_urls.append(post.url)
    return media_urls if media_urls else [post.url]

# --- Commands ---
@client.command()
async def redditnsfw(ctx, subreddit_name: str = "nsfw"):
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ Use in NSFW channels only.")
    urls = fetch_post(subreddit_name)
    if urls:
        for u in urls:
            await ctx.send(u)
    else:
        await ctx.send(f"❌ No posts found in r/{subreddit_name}")

@client.command()
async def randomnsfw(ctx):
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ Use in NSFW channels only.")
    pool = random.choice([real_subs, hentai_subs])
    urls = fetch_post(random.choice(pool))
    if urls:
        for u in urls:
            await ctx.send(u)
    else:
        await ctx.send("❌ No posts found.")

# --- Auto NSFW Poster ---
auto_post_channel = None
auto_post_task = None

async def auto_nsfw_loop(channel, interval):
    await client.wait_until_ready()
    while auto_post_channel:
        pool = random.choice([real_subs, hentai_subs])
        urls = fetch_post(random.choice(pool))
        if urls:
            for u in urls:
                await channel.send(u)
        await asyncio.sleep(interval)

@client.command()
async def autonsfw(ctx, interval: int = 30):
    global auto_post_channel, auto_post_task
    if not ctx.channel.is_nsfw():
        return await ctx.send("⚠️ Use in NSFW channels only.")
    if interval < 10:
        return await ctx.send("⚠️ Minimum interval is 10s.")
    auto_post_channel = ctx.channel
    if auto_post_task:
        auto_post_task.cancel()
    auto_post_task = asyncio.create_task(auto_nsfw_loop(ctx.channel, interval))
    await ctx.send(f"✅ Auto NSFW started every {interval}s in this channel.")

@client.command()
async def stopnsfw(ctx):
    global auto_post_channel, auto_post_task
    auto_post_channel = None
    if auto_post_task:
        auto_post_task.cancel()
        auto_post_task = None
    await ctx.send("🛑 Auto NSFW stopped.")

# --- Flask server for uptime ---
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
        print(f"Bot crashed: {e}, restarting in 10s...")
        time.sleep(10)
            
