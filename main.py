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

poketwo = 716390085896962058  # Ensure this is the correct ID for Pokétwo
client = commands.Bot(command_prefix='Lickitysplit')
intervals = [2.2, 2.4, 2.6, 2.8]

# Function to solve the hint and find matches in the files
def solve(message, file_name):
    hint = []
    # Start reading the hint from after the "The Pokémon is "
    hint_start = message.find('The pokémon is ') + len('The pokémon is ')
    hint_string = message[hint_start:].strip()
    
    if hint_string:
        # Replace underscores with dots for regex matching
        hint_replaced = hint_string.replace('_', '.')
        
        # Open the respective file and search for matches
        with open(file_name, "r") as f:
            solutions = f.read()
        solution = re.findall('^' + hint_replaced + '$', solutions, re.MULTILINE)
        
        if solution:
            return solution
    return None

# Function to move the cloned channel to the right category
async def move_channel_to_category(channel, solution):
    guild = channel.guild
    category_name = '🎉Friends Col'
    new_category = None

    # Check for the category with fewer than 48 channels
    for i in range(1, 6):
        category_name = f'🎉Friends Col {i}' if i > 1 else '🎉Friends Col'
        new_category = discord.utils.get(guild.categories, name=category_name)
        if len(new_category.channels) < 48:
            break

    # If no category found with fewer than 48 channels, send message
    if new_category:
        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category, sync_permissions=True)
    else:
        print("No available category found with fewer than 48 channels.")
    
    # Send redirect message to Pokétwo
    await channel.send(f'<@{poketwo}> redirect 1 2 3 4 5 6')

@client.event
async def on_message(message):
    # Ensure the bot does not respond to its own messages
    if message.author == client.user:
        return

    if message.author.id == poketwo:
        # Check if the message is in a category named "catch"
        if message.channel.category and message.channel.category.name == "catch":
            # Check if the message contains the phrase "wild pokémon has appeared!"
            if message.embeds and "wild pokémon has appeared!" in message.embeds[0].title.lower():
                print("Detected a wild Pokémon!")
                await asyncio.sleep(1)
                await message.channel.send(f"<@{poketwo}> h")
            else:
                # Check for the hint message after @Pokétwo h
                content = message.content
                if 'The pokémon is ' in content:
                    print(f"Received hint: {content}")
                    solution = solve(content, 'collection')
                    
                    if solution:
                        print(f"Match found: {solution[0]}")
                        await message.channel.clone()  # Clone the channel
                        await move_channel_to_category(message.channel, solution)  # Move cloned channel
                    else:
                        print("No match found in collection.")
                        solution = solve(content, 'mythical')
                        
                        if solution:
                            print(f"Match found in mythical: {solution[0]}")
                            await message.channel.clone()  # Clone the channel
                            await move_channel_to_category(message.channel, solution)  # Move cloned channel
                        else:
                            print("No match found in mythical.")
                            
# Debugging event for bot readiness
@client.event
async def on_ready():
    print(f'Logged into account: {client.user.name}')
    print("Bot is ready.")

# Task that sends a random spam message at intervals
@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    await channel.send(''.join(random.sample('1234567890', 7) * 5))

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()

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
    
