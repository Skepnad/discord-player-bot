import discord
from discord.ext import tasks
import os

# Configuration - Edit these values or use environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))  # Your voice channel ID
MAX_PLAYERS = int(os.getenv('MAX_PLAYERS', '32'))
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '10'))  # Minutes
HOT_THRESHOLD = int(os.getenv('HOT_THRESHOLD', '24'))  # Players count for 🔥

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Bot logged in as {client.user}')
    print(f'📊 Monitoring channel ID: {CHANNEL_ID}')
    print(f'⏰ Update interval: {UPDATE_INTERVAL} minutes')
    print(f'🔥 Hot threshold: {HOT_THRESHOLD}/{MAX_PLAYERS} players')
    update_channel.start()

@tasks.loop(minutes=UPDATE_INTERVAL)
async def update_channel():
    try:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print(f'❌ Error: Could not find channel with ID {CHANNEL_ID}')
            return
            
        current_players = get_current_players()
        
        # Conditional emoji based on activity level
        if current_players == 0:
            emoji = "⚪"  # Empty/Neutral
        elif current_players >= HOT_THRESHOLD:
            emoji = "🔥"  # Hot
        else:
            emoji = "🟢"  # Populated/Active
        
        # Format channel name
        new_name = f"{emoji} Players: {current_players}/{MAX_PLAYERS}"
        
        await channel.edit(name=new_name)
        print(f"✅ Updated channel to: {new_name}")
        
    except discord.errors.Forbidden:
        print("❌ Error: Bot doesn't have permission to edit channel")
    except Exception as e:
        print(f"❌ Error updating channel: {e}")

def get_current_players():
    """
    Get current player count from your data source.
    
    For now, returns dummy data. Replace this function with:
    - API call to your game server
    - API call to WordPress REST endpoint
    - Database query
    - File reading
    """
    
    # TODO: Replace with actual data source
    # Example for WordPress API:
    # import requests
    # response = requests.get('https://yoursite.com/wp-json/custom/v1/players')
    # return response.json()['count']
    
    return 0  # Dummy data - returns 0 players

# Error handling for startup
try:
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Error: Please set your Discord bot token in config.py or environment variable")
        exit(1)
    if CHANNEL_ID == 0:
        print("❌ Error: Please set your channel ID in config.py or environment variable")
        exit(1)
        
    client.run(TOKEN)
except discord.errors.LoginFailure:
    print("❌ Error: Invalid Discord bot token")
except Exception as e:
    print(f"❌ Error starting bot: {e}")
