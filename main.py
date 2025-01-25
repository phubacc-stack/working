import re
import os
import asyncio
import random
from discord.ext import commands, tasks

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

num_pokemon = 0
shiny = 0
legendary = 0
mythical = 0

poketwo = 716390085896962058
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)
intervals = [2.2, 2.4, 2.6, 2.8]


def solve(message, file_name):
    hint = message[15:].strip('\\')
    hint_replaced = hint.replace('_', '.')
    with open(file_name, "r") as f:
        solutions = f.read()
    solution = re.findall('^' + hint_replaced + '$', solutions, re.MULTILINE)
    return solution if solution else None


@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    if channel:
        await channel.send(''.join(random.sample('1234567890', 7) * 5))


@spam.before_loop
async def before_spam():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')


@client.event
async def on_message(message):
    if message.author.id == poketwo and message.channel.category and message.channel.category.name == 'catch':
        if message.embeds:
            embed_title = message.embeds[0].title
            if 'wild pokémon has appeared!' in embed_title:
                await asyncio.sleep(1)
                await message.channel.send('<@716390085896962058> h')
        else:
            content = message.content
            solution = solve(content, 'collection')
            if solution:
                await handle_solution(message.channel, solution[0], '🎉Friends Col')
            else:
                solution = solve(content, 'mythical')
                if solution:
                    await handle_solution(message.channel, solution[0], '😈Collection')


async def handle_solution(channel, solution, base_category_name):
    guild = channel.guild
    categories = [c for c in guild.categories if c.name.startswith(base_category_name)]
    for category in categories:
        if len(category.channels) < 48:
            await channel.edit(name=solution.lower().replace(' ', '-'), category=category, sync_permissions=True)
            await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6')
            return

    # If no available category, create a new one
    new_category_name = f"{base_category_name} {len(categories) + 1}"
    new_category = await guild.create_category(new_category_name)
    await channel.edit(name=solution.lower().replace(' ', '-'), category=new_category, sync_permissions=True)
    await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6')


@client.command()
async def report(ctx, *, args):
    await ctx.send(args)


@client.command()
async def reboot(ctx):
    spam.start()


@client.command()
async def pause(ctx):
    spam.cancel()


if __name__ == '__main__':
    spam.start()
    client.run(user_token)
    
