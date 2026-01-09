import discord
from discord.ext import tasks
import os
import requests
from datetime import datetime

"""
Discord Player Count Bot - WordPress Integration Version
Updates Discord voice channel names with live player counts from WordPress
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

# Discord Configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))  # Voice channel ID to update

# WordPress API Configuration
WORDPRESS_API_URL = os.getenv('WORDPRESS_API_URL', 'https://yoursite.com/wp-json/discord-bot/v1/stats/Main-Server')
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '10'))  # Seconds

# Server Configuration
MAX_PLAYERS = int(os.getenv('MAX_PLAYERS', '32'))
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '10'))  # Minutes
HOT_THRESHOLD = int(os.getenv('HOT_THRESHOLD', '24'))  # Players count for 🔥 emoji

# Channel Name Format
# Available variables: {emoji}, {current}, {max}, {status}
CHANNEL_NAME_FORMAT = os.getenv('CHANNEL_NAME_FORMAT', '{emoji} Players: {current}/{max}')

# ============================================================================
# BOT INITIALIZATION
# ============================================================================

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Global variables for tracking
last_player_count = -1
last_update_time = None
consecutive_errors = 0
MAX_CONSECUTIVE_ERRORS = 5

# ============================================================================
# EVENT HANDLERS
# ============================================================================

@client.event
async def on_ready():
    """Called when bot successfully connects to Discord"""
    print('=' * 60)
    print('Discord Player Count Bot - CONNECTED')
    print('=' * 60)
    print(f'✅ Bot logged in as: {client.user}')
    print(f'📊 Monitoring channel ID: {CHANNEL_ID}')
    print(f'🌐 WordPress API: {WORDPRESS_API_URL}')
    print(f'⏰ Update interval: {UPDATE_INTERVAL} minutes')
    print(f'🔥 Hot threshold: {HOT_THRESHOLD}/{MAX_PLAYERS} players')
    print(f'📝 Channel format: {CHANNEL_NAME_FORMAT}')
    print('=' * 60)
    
    # Start the update loop
    update_channel.start()
    
    # Run first update immediately
    await update_channel_once()

@client.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors"""
    print(f'❌ Bot error in event {event}')
    import traceback
    traceback.print_exc()

# ============================================================================
# MAIN UPDATE LOOP
# ============================================================================

@tasks.loop(minutes=UPDATE_INTERVAL)
async def update_channel():
    """Main loop - updates Discord channel name periodically"""
    await update_channel_once()

async def update_channel_once():
    """Single update execution"""
    global last_player_count, last_update_time, consecutive_errors
    
    try:
        # Get the Discord channel
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print(f'❌ Error: Could not find channel with ID {CHANNEL_ID}')
            print(f'   Make sure the channel ID is correct and the bot has access')
            return
        
        # Fetch player data from WordPress
        player_data = get_player_data_from_wordpress()
        
        if player_data is None:
            consecutive_errors += 1
            print(f'⚠️  Failed to fetch data ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})')
            
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print(f'❌ Too many consecutive errors. Using last known data.')
                if last_player_count >= 0:
                    player_data = {
                        'current_players': last_player_count,
                        'max_players': MAX_PLAYERS,
                        'server_status': 'unknown'
                    }
                else:
                    return
            else:
                return
        else:
            consecutive_errors = 0  # Reset error counter on success
        
        current_players = player_data['current_players']
        max_players = player_data.get('max_players', MAX_PLAYERS)
        server_status = player_data.get('server_status', 'online')
        
        # Determine emoji based on player count and status
        emoji = get_status_emoji(current_players, max_players, server_status)
        
        # Format channel name
        new_name = CHANNEL_NAME_FORMAT.format(
            emoji=emoji,
            current=current_players,
            max=max_players,
            status=server_status
        )
        
        # Only update if name changed (to avoid unnecessary API calls)
        if channel.name != new_name:
            await channel.edit(name=new_name)
            print(f'✅ Updated channel to: {new_name}')
            print(f'   Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        else:
            print(f'ℹ️  No change needed (still: {new_name})')
        
        # Update tracking variables
        last_player_count = current_players
        last_update_time = datetime.now()
        
    except discord.errors.Forbidden:
        print('❌ Error: Bot does not have permission to edit channel')
        print('   Make sure the bot has "Manage Channels" permission')
    except discord.errors.HTTPException as e:
        if e.status == 429:  # Rate limited
            print('⚠️  Rate limited by Discord. Waiting before next update...')
        else:
            print(f'❌ Discord API error: {e}')
    except Exception as e:
        print(f'❌ Unexpected error updating channel: {e}')
        import traceback
        traceback.print_exc()

# ============================================================================
# DATA FETCHING
# ============================================================================

def get_player_data_from_wordpress():
    """
    Fetch player count data from WordPress REST API
    
    Returns:
        dict: Player data with keys: current_players, max_players, server_status
        None: If request fails
    """
    try:
        print(f'📡 Fetching data from WordPress API...')
        
        response = requests.get(
            WORDPRESS_API_URL,
            timeout=API_TIMEOUT,
            headers={'User-Agent': 'Discord-Player-Bot/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle both single server and array responses
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            player_data = {
                'current_players': int(data.get('current_players', 0)),
                'max_players': int(data.get('max_players', MAX_PLAYERS)),
                'server_status': data.get('server_status', 'online')
            }
            
            print(f'✅ API Success: {player_data["current_players"]}/{player_data["max_players"]} players')
            return player_data
            
        elif response.status_code == 404:
            print(f'❌ API Error: Server not found (404)')
            print(f'   Check that the server name in the URL is correct')
            return None
        else:
            print(f'❌ API returned status code: {response.status_code}')
            print(f'   Response: {response.text[:200]}')
            return None
            
    except requests.exceptions.Timeout:
        print(f'❌ API request timed out after {API_TIMEOUT} seconds')
        return None
    except requests.exceptions.ConnectionError:
        print(f'❌ Could not connect to WordPress API')
        print(f'   Check that the URL is correct and WordPress is accessible')
        return None
    except requests.exceptions.RequestException as e:
        print(f'❌ API request failed: {e}')
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f'❌ Error parsing API response: {e}')
        return None
    except Exception as e:
        print(f'❌ Unexpected error fetching data: {e}')
        return None

def get_player_data_fallback():
    """
    Fallback method - returns dummy data for testing
    Replace this with alternative data sources if needed
    """
    print('⚠️  Using fallback data source (dummy data)')
    return {
        'current_players': 0,
        'max_players': MAX_PLAYERS,
        'server_status': 'unknown'
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_status_emoji(current_players, max_players, server_status):
    """
    Determine emoji based on player count and server status
    
    Args:
        current_players (int): Current number of players
        max_players (int): Maximum player slots
        server_status (str): Server status (online, offline, maintenance)
    
    Returns:
        str: Emoji character
    """
    # Handle offline/maintenance status
    if server_status == 'offline':
        return '🔴'
    elif server_status == 'maintenance':
        return '🟡'
    
    # Normal status - based on player count
    if current_players == 0:
        return '⚪'  # Empty/Neutral
    elif current_players >= HOT_THRESHOLD:
        return '🔥'  # Hot/Busy
    else:
        return '🟢'  # Populated/Active

def validate_configuration():
    """Validate configuration before starting bot"""
    errors = []
    
    if TOKEN == 'YOUR_BOT_TOKEN_HERE' or not TOKEN:
        errors.append('Discord bot token not configured')
    
    if CHANNEL_ID == 0:
        errors.append('Channel ID not configured')
    
    if WORDPRESS_API_URL == 'https://yoursite.com/wp-json/discord-bot/v1/stats/Main-Server':
        errors.append('WordPress API URL not configured')
    
    if errors:
        print('=' * 60)
        print('❌ CONFIGURATION ERRORS:')
        print('=' * 60)
        for error in errors:
            print(f'   • {error}')
        print('=' * 60)
        print('')
        print('Please configure the bot by either:')
        print('1. Editing the configuration values at the top of bot.py')
        print('2. Setting environment variables:')
        print('   - DISCORD_BOT_TOKEN')
        print('   - CHANNEL_ID')
        print('   - WORDPRESS_API_URL')
        print('=' * 60)
        return False
    
    return True

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point"""
    print('')
    print('=' * 60)
    print('Discord Player Count Bot')
    print('WordPress Integration Version')
    print('=' * 60)
    print('')
    
    # Validate configuration
    if not validate_configuration():
        exit(1)
    
    # Start the bot
    try:
        client.run(TOKEN)
    except discord.errors.LoginFailure:
        print('=' * 60)
        print('❌ LOGIN FAILED')
        print('=' * 60)
        print('Invalid Discord bot token.')
        print('Please check your token and try again.')
        print('=' * 60)
        exit(1)
    except KeyboardInterrupt:
        print('')
        print('=' * 60)
        print('Bot stopped by user')
        print('=' * 60)
        exit(0)
    except Exception as e:
        print('=' * 60)
        print('❌ FATAL ERROR')
        print('=' * 60)
        print(f'Error starting bot: {e}')
        print('=' * 60)
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    main()
