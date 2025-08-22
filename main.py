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
    print("on_ready event triggered!")

    try:
        if TESTING:
            print("Testing mode: syncing to dev guild...")
            # sync to dev guild (instant)
            bot.tree.copy_global_to(guild=dev_guild)
            print("Commands copied to dev guild")
            await bot.tree.sync(guild=dev_guild)
            print("Commands synced to dev guild successfully")
        else:
            print("Production mode: syncing globally...")
            # sync globally (can take up to 1 hour, slash commands suck)
            await bot.tree.sync()
            print("Commands synced globally successfully")

        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print("------")
        print("Bot is ready and all commands are synced!")

    except Exception as e:
        print(f"Error in on_ready: {e}")
        import traceback
        traceback.print_exc()

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
        try:
            print("Loading cogs...")
            await bot.load_extension("cogs.db")
            print("✓ Loaded db")
            await bot.load_extension("cogs.basics")
            print("✓ Loaded basics")
            await bot.load_extension("cogs.setup")
            print("✓ Loaded setup")
            await bot.load_extension("cogs.time_manager")
            print("✓ Loaded time_manager")
            await bot.load_extension("cogs.elections")
            print("✓ Loaded elections")
            await bot.load_extension("cogs.polling")
            print("✓ Loaded polling")
            await bot.load_extension("cogs.all_signups")
            print("✓ Loaded all_signups")
            await bot.load_extension("cogs.all_winners")
            print("✓ Loaded all_winners")
            await bot.load_extension("cogs.party_management")
            print("✓ Loaded party_management")
            await bot.load_extension("cogs.presidential_signups")
            print("✓ Loaded presidential_signups_actions")
            await bot.load_extension("cogs.ideology")
            print("✓ Loaded ideology")
            await bot.load_extension("cogs.general_campaign_actions")
            print("✓ Loaded general_campaign_actions")
            await bot.load_extension("cogs.presidential_winners")
            print("✓ Loaded presidential_winners")
            await bot.load_extension("cogs.endorsements")
            print("✓ Loaded endorsements")
            await bot.load_extension("cogs.delegates")
            print("✓ Loaded delegates")
            print("All cogs loaded successfully!")
        except Exception as e:
            print(f"Error loading cogs: {e}")
            import traceback
            traceback.print_exc()
            return
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())