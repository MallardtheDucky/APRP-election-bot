import discord
import asyncio
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

### Configuration
TESTING = True  # Set to False for production - shitty code, I know
dev_guild= discord.Object(id=1407527193470439565)  # Replace with your dev guild ID
# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create bot
bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)

@bot.event
async def on_ready():
    if TESTING:
    # sync to dev guild (instant)
        bot.tree.copy_global_to(guild=dev_guild)
        await bot.tree.sync(guild=dev_guild)
    else:
        # sync globally (can take up to 1 hour, slash commands suck)
        await bot.tree.sync()

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
    print(f"Command error: {error}")

async def main():
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("Please set the DISCORD_BOT_TOKEN environment variable.")
        return

    async with bot: #load cogs here
        await bot.load_extension("cogs.db")
        await bot.load_extension("cogs.basics")
        await bot.load_extension("cogs.setup")
        await bot.load_extension("cogs.time_manager")
        await bot.load_extension("cogs.elections")
        await bot.load_extension("cogs.polling")
        await bot.load_extension("cogs.all_signups")
        await bot.load_extension("cogs.all_winners")
        await bot.load_extension("cogs.party_management")
        await bot.load_extension("cogs.general_campaign_actions")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())