import re, os, asyncio, random
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
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

def solve(message, file_name):
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''.join(hint)
    hint_replaced = hint_string.replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall('^' + hint_replaced + '$', solutions, re.MULTILINE)
    if len(solution) == 0:
        return None
    return solution

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    guild = message.guild
    category = channel.category
    if message.author.id == poketwo:
        if message.channel.category.name == 'catch':
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await channel.send('<@716390085896962058> h')
            else:
                content = message.content
                solution = None
                if 'The pokémon is ' in content:
                    solution = solve(content, 'collection')
                    if solution:
                        await channel.clone()
                        category_name = '🎉Friends Col'
                        guild = message.guild
                        new_category = [c for c in guild.categories if c.name == category_name][0]
                        if len(new_category.channels) <= 48:
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        else:
                            await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')
                    if not solution:
                        solution = solve(content, 'mythical')
                        if solution:
                            await channel.clone()
                            category_name = '😈Collection'
                            guild = message.guild
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            if len(new_category.channels) <= 48:
                                await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                            else:
                                await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')

@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    spam.start()

@client.command()
async def pause(ctx):
    spam.cancel()

# Main entry point
client.run(user_token)
