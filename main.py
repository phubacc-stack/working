import re, os, asyncio, random
from discord.ext import commands, tasks

version = 'v2.7'

user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

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

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    guild = message.guild
    category = channel.category

    # Check if message is from Poketwo
    if message.author.id == poketwo:
        if message.channel.category.name == 'catch':
            # Check if message contains Pokemon embed
            if message.embeds:
                embed_title = message.embeds[0].title
                # Check if the embed title contains 'A new wild pokémon has appeared!'
                if 'A new wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    # Sending @Pokétwo#8236 h to trigger the Pokémon response
                    await channel.send('<@716390085896962058> h')
            else:
                content = message.content
                solution = None

                # Try to solve the Pokemon name from the message content
                if 'The pokémon is ' in content:
                    solution = solve(content, 'collection')
                    if solution:
                        # Clone the channel
                        new_channel = await channel.clone(name=solution[0].lower().replace(' ', '-'))
                        print(f"Cloned channel: {new_channel.name}")
                        
                        # Move the original channel to the appropriate category
                        category_name = '🎉Friends Col'
                        guild = message.guild
                        new_category = [c for c in guild.categories if c.name == category_name][0]
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        print(f"Moved original channel {channel.name} to category {new_category.name}")
                        await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')
                    if not solution:
                        solution = solve(content, 'mythical')
                        if solution:
                            # Clone the channel
                            new_channel = await channel.clone(name=solution[0].lower().replace(' ', '-'))
                            print(f"Cloned channel: {new_channel.name}")
                            
                            # Move the original channel to the appropriate category
                            category_name = '😈Collection'
                            guild = message.guild
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                            print(f"Moved original channel {channel.name} to category {new_category.name}")
                            await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')

# Task that sends a random spam message at intervals
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

# On bot ready event
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')

# Handles incoming messages
@client.event
async def on_message(message):
    # Your on_message logic remains unchanged
    pass

# Bot commands
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

# Main function to run the bot
async def main():
    async with client:
        spam.start()  # Start the spam task
        await client.start(user_token)

# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
    
