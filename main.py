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
    # Extract the hint from the message (start from index 15 to skip the initial part of the string)
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':  # Only add characters that aren't backslashes
            hint.append(message[i])
    
    hint_string = ''.join(hint)  # Create the full hint string
    print(f"Extracted hint: {hint_string}")  # Debugging: Check the extracted hint
    
    # Replace underscores (_) with dots (.) to match any character in regex
    hint_replaced = hint_string.replace('_', r'\.')  # Replace _ with escaped dot \.
    print(f"Hint for regex match: {hint_replaced}")  # Debugging: Check the regex pattern
    
    hint_length = len(hint_string)  # Get the length of the hint string
    
    # Read the file with Pokémon names
    with open(f"{file_name}", "r") as f:
        solutions = f.read().splitlines()
    
    # Debugging: Check all Pokémon names in the file
    print(f"Total Pokémon in {file_name}: {len(solutions)}")  # Debugging: Show number of Pokémon
    
    # Using fullmatch to only match the exact length and pattern
    matches = [solution for solution in solutions if re.fullmatch(hint_replaced, solution) and len(solution) == hint_length]
    
    if len(matches) == 0:
        print(f"No matches found for hint: {hint_string}")  # Debugging: No matches found
        return None
    
    # Return the matched solutions
    return matches

# Event that triggers when a message is received
@client.event
async def on_message(message):
    # Check if the message is from Pokétwo and if the message is in the "catch" category
    if message.author.id == poketwo:
        channel = client.get_channel(message.channel.id)
        
        # Check if the message is in the "catch" category
        if channel.category and channel.category.name.lower() == 'catch':
            # Check if the message contains an embed
            if message.embeds:
                embed_title = message.embeds[0].title
                # Adjusted check for "A new wild pokémon has appeared!"
                if 'A new wild pokémon has appeared!' in embed_title:
                    await asyncio.sleep(1)  # Optional: small delay before sending
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

# Run the bot
async def main():
    async with client:
        await client.start(user_token)

if __name__ == "__main__":
    asyncio.run(main())
    
