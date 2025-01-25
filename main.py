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

# Function to solve the hint and search for partial matches
def solve(message, file_name):
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''.join(hint)
    hint_replaced = hint_string.replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall(hint_replaced, solutions, re.MULTILINE)  # Partial match for Pokémon name
    if len(solution) == 0:
        return None
    return solution

# Event triggered when a message is sent
@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    guild = message.guild
    category = channel.category

    # Check if message is from Poketwo
    if message.author.id == poketwo:
        # If message is from the 'catch' category, try to find Pokémon name
        if message.channel.category.name == 'catch':
            # Check if message contains a Pokémon embed
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await channel.send('<@716390085896962058> h')
            else:
                content = message.content
                solution = None

                # Try to solve the Pokémon name from the message content
                if 'The pokémon is ' in content:
                    solution = solve(content, 'collection')
                    if solution:
                        await channel.clone()

                        # Move to designated category and sync permissions
                        category_name = '🎉Friends Col'
                        guild = message.guild
                        old_category = channel.category
                        new_category = [c for c in guild.categories if c.name == category_name][0]
                        if len(new_category.channels) <= 48:
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        else:
                            category_name = '🎉Friends Col 2'
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)

                        await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')
                    else:
                        solution = solve(content, 'mythical')
                        if solution:
                            await channel.clone()

                            # Move to designated category and sync permissions
                            category_name = '😈Collection'
                            guild = message.guild
                            old_category = channel.category
                            new_category = [c for c in guild.categories if c.name == category_name][0]
                            if len(new_category.channels) <= 48:
                                await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                            else:
                                category_name = '😈Collection 2'
                                new_category = [c for c in guild.categories if c.name == category_name][0]
                                await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)

                            await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')

        # Check for 'Congratulations' message for auto-delete feature
        elif "Congratulations" in message.content and message.channel.category.name not in ['catch']:
            if "you caught a" in message.content:
                await asyncio.sleep(10)
                if not message.deleted:  # Check if message has been deleted before
                    if "✨" not in message.content:  # If no special message about unusual colors
                        await channel.delete()
                        print(f"Deleted channel: {channel.name}")
                    else:
                        print(f"Skipped delete for channel: {channel.name}, message had unusual colors.")

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
                            
