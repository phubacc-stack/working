import re, os, asyncio, random
from discord.ext import commands, tasks

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read().splitlines()  # Read lines as a list of Pokémon names
with open('mythical', 'r') as file:
    mythical_list = file.read().splitlines()  # Read lines as a list of mythical names

num_pokemon = 0
shiny = 0
legendary = 0
mythical = 0

poketwo = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

def solve(message, file_name):
    hint_start = message.find('The pokémon is ') + len('The pokémon is ')
    hint_string = message[hint_start:].strip()

    if hint_string:
        # Replace underscores with dots for regex matching
        hint_replaced = hint_string.replace('_', '.').lower()  # Also make it lowercase for case-insensitive matching
        
        # Select the correct list based on the file_name argument
        target_list = pokemon_list if file_name == 'collection' else mythical_list
        
        # Log the hint for debugging
        print(f"Searching for: {hint_replaced} in {file_name}")

        # Try to find a match using regex, case-insensitive
        for name in target_list:
            if re.fullmatch(hint_replaced, name.lower()):
                print(f"Match found: {name}")
                return [name]  # Return the matched name
        
    return None

async def move_channel_to_category(channel, solution):
    guild = channel.guild
    category_name = '🎉Friends Col'
    new_category = None

    for i in range(1, 6):
        category_name = f'🎉Friends Col {i}' if i > 1 else '🎉Friends Col'
        new_category = discord.utils.get(guild.categories, name=category_name)
        if len(new_category.channels) < 48:
            break

    if new_category:
        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
    else:
        print("No available category found with fewer than 48 channels.")
    
    await channel.send(f'<@{poketwo}> redirect 1 2 3 4 5 6')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.id == poketwo:
        if message.channel.category and message.channel.category.name == "catch":
            if message.embeds and "wild pokémon has appeared!" in message.embeds[0].title.lower():
                print("Detected a wild Pokémon!")
                await asyncio.sleep(1)
                await message.channel.send(f"<@{poketwo}> h")
            else:
                content = message.content
                if 'The pokémon is ' in content:
                    print(f"Received hint: {content}")
                    solution = solve(content, 'collection')

                    if solution:
                        print(f"Match found in collection: {solution[0]}")
                        await message.channel.clone()  # Clone the channel
                        await move_channel_to_category(message.channel, solution)
                    else:
                        print("No match found in collection.")
                        solution = solve(content, 'mythical')

                        if solution:
                            print(f"Match found in mythical: {solution[0]}")
                            await message.channel.clone()  # Clone the channel
                            await move_channel_to_category(message.channel, solution)
                        else:
                            print("No match found in mythical.")

@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    print("Bot is ready.")

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

@client.command()
async def report(ctx, *, args):
    await ctx.send(args)

@client.command()
async def reboot(ctx):
    if not spam.is_running():
        spam.start()
    await ctx.send("Spam task has been restarted!")

@client.command()
async def pause(ctx):
    if spam.is_running():
        spam.cancel()
    await ctx.send("Spam task has been paused!")

async def main():
    async with client:
        spam.start()  # Start the spam task
        await client.start(user_token)

if __name__ == "__main__":
    asyncio.run(main())
    
