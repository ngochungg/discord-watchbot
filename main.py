import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MY_GUILD_ID = os.getenv('MY_GUILD_ID')
ADMIN_ID = os.getenv('ADMIN_ID')

# 2. Create a bot instance with the specified command prefix and intents
class MyBot(commands.Bot):

    # 3. Initialize the bot with the necessary intents
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        
        # 4. Load the cogs (extensions) from the 'cogs' directory
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    try:

                        await self.load_extension(f'cogs.{filename[:-3]}')
                        print(f'✅ Loaded cog: {filename}')

                    except Exception as e:

                        print(f'❌ Failed to load cog: {filename}. Error: {e}')

        MY_GUILD = discord.Object(id=MY_GUILD_ID)
        self.tree.copy_global_to(guild=MY_GUILD)  # Copy global commands to the specified guild
        await self.tree.sync(guild=MY_GUILD)  # Sync the command tree with Discord
        print("✅ Command tree synced with Discord.")
    
    # 5. Define the on_ready event to print a message when the bot is ready
    async def on_ready(self):

        print(f"✅ Bot {self.user} is online!")

        for guild in self.guilds:
            if guild.system_channel:

                # await guild.system_channel.send(f"✅ Bot {self.user} is online!")
                print(f'📢 Sent notification to system channel of server: {guild.name}')
                
bot = MyBot()

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)