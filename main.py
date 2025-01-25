import re, os, asyncio, random
from discord.ext import commands, tasks

# Bot version and settings
version = 'v2.7'
user_token = os.environ['user_token']
spam_id = os.environ['spam_id']

# Load the Pokémon and Mythical lists
with open('pokemon', 'r', encoding='utf8') as file:
    pokemon_list = file.read()
with open('mythical', 'r') as file:
    mythical_list = file.read()

# Initialize counters
num_pokemon = 0
shiny = 0
legendary = 0
mythical = 0

poketwo = 716390085896962058
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

# Function to solve Pokémon name from a hint
def solve(message, file_name):
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''.join(hint)
    
    # Convert underscores (_) to a dot (.) and escape regex special characters
    hint_replaced = hint_string.replace('_', r'\.')  # Replace _ with escaped dot \.
    
    # Ensure regex doesn't interpret it as a wildcard
    hint_length = len(hint_string)
    
    with open(f"{file_name}", "r") as f:
        solutions = f.read().splitlines()

    # Using fullmatch to only match the exact length and pattern
    matches = [solution for solution in solutions if re.fullmatch(hint_replaced, solution) and len(solution) == hint_length]

    if len(matches) == 0:
        return None
    return matches

# Event that triggers when a message is received
@client.event
async def on_message(message):
    # Check if the message is from Pokétwo
    if message.author.id == poketwo:
        # Check if the message is in the "catch" category
        channel = client.get_channel(message.channel.id)
        if channel.category and channel.category.name.lower() == 'catch':  # Detect if it's in 'catch' category
            # If the message contains embeds, send the @Pokétwo h command
            if message.embeds:
                await asyncio.sleep(1)  # Optional: small delay
                await channel.send('<@716390085896962058> h')  # Send @Pokétwo h

        # Handle the Pokémon collection and mythical collection logic
        else:
            content = message.content
            solution = None
            
            # Try to solve the Pokémon name from the message content
            if 'The pokémon is ' in content:
                solution = solve(content, 'collection')
                if solution:
                    await channel.clone()  # Clone the channel if a match is found
                    category_name = '🎉Friends Col'
                    guild = message.guild
                    old_category = channel.category
                    new_category = [c for c in guild.categories if c.name == category_name][0]
                    num_channels = len(new_category.channels)
                    print(f"There are {num_channels} channels in the {category_name} category.")
                    
                    # Check if the category is full (more than 48 channels), if so, create a new one
                    if len(new_category.channels) <= 48:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                    else:
                        # Create new category if full
                        new_category_name = category_name + ' 2'
                        new_category = await guild.create_category(new_category_name)
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                    await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 ')
                if not solution:
                    solution = solve(content, 'mythical')
                    if solution:
                        await channel.clone()
                        category_name = '😈Collection'
                        guild = message.guild
                        new_category = [c for c in guild.categories if c.name == category_name][0]
                        
                        # Check if the category is full (more than 48 channels), if so, create a new one
                        if len(new_category.channels) <= 48:
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
                        else:
                            # Create new category if full
                            new_category_name = category_name + ' 2'
                            new_category = await guild.create_category(new_category_name)
                            await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
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
