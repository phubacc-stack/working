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

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    guild = message.guild
    category = channel.category

    # Check if message is from Poketwo
    if message.author.id == poketwo:
        if message.channel.category.name == 'catch':
            if message.embeds:
                embed_title = message.embeds[0].title
                if 'wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)
                    await channel.send('<@716390085896962058> h')

            # Handle "Congratulations" message
            if 'Congratulations' in message.content:
                if 'You caught a Level' in message.content:
                    # Start a 10-second timer for cancellation
                    await asyncio.sleep(10)

                    # Check if the cancel message is not triggered
                    if 'these colors seem unusual...✨' not in message.content:
                        # Prevent deletion if the channel is in the 'catch' category
                        if category.name != 'catch':
                            # Delete the channel if the cancel message isn't detected
                            await channel.delete()
                            print(f"Channel {channel.name} deleted after catching message.")

        # Implement cancel option within 10 seconds
        if message.content == 'cancel' and message.author != client.user:
            # Check if the user is canceling within the allowed window
            await channel.send("Channel deletion canceled!")
            print(f"Deletion of channel {channel.name} canceled by {message.author}.")

        # Handle Pokemon name solving, channel cloning, and moving
        if 'The pokémon is ' in message.content:
            solution = solve(message.content, 'collection')
            if solution:
                await channel.clone()
                category_name = '🎉Friends Col'
                new_category = [c for c in guild.categories if c.name == category_name][0]
                if len(new_category.channels) <= 48:
                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)

            if not solution:
                solution = solve(message.content, 'mythical')
                if solution:
                    await channel.clone()
                    category_name = '😈Collection'
                    new_category = [c for c in guild.categories if c.name == category_name][0]
                    if len(new_category.channels) <= 48:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)

        # Send redirect command
        await channel.send('<@716390085896962058> redirect 1 2 3 4 5 6')

# Task that sends a random spam message at intervals
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
    
