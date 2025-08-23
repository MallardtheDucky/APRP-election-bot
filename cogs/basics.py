from discord.ext import commands
import discord
from discord import app_commands

class Basics(commands.Cog):  # Capitalized as per style
    def __init__(self, bot):
        self.bot = bot
        print("Basics cog loaded successfully.")

    @discord.app_commands.command(name="commands", description="Lists all the commands in the bot") #commands command
    async def help_command(self, interaction: discord.Interaction):
        with open('help.txt', 'r', encoding='utf-8') as f: # opens help.txt in read mode (unicode), assigns to help_text and 
            help_text = f.read()

        embed = discord.Embed(
            title='Election bot commands:',
            description=help_text,
            color=discord.Colour.blurple()
        )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="credits", description="Lists the people that made this bot")
    async def credits_command(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title='To the people who made me possible:',
            description="""
            Mallard - original creator
            Sixteen - 16bysixteen - maintainer
            Yuri - deftvessel2.0 - maintainer
            """,
            color=discord.Colour.blurple()
        )

        await interaction.response.send_message(embed=embed)

    # Create admin command group
    admin_group = app_commands.Group(name="admin", description="Admin-only commands")

    @admin_group.command(
        name="reset_campaign_cooldowns",
        description="Reset general campaign action cooldowns for a user (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_campaign_cooldowns(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        collection_name: str = "action_cooldowns"
    ):
        target_user = user if user else interaction.user

        # Common cooldown collection names that might exist
        possible_collections = [
            "action_cooldowns",
            "campaign_cooldowns", 
            "general_action_cooldowns",
            "election_cooldowns"
        ]

        cooldowns_col = self.bot.db[collection_name]

        # Reset all cooldowns for the user in the specified collection
        result = cooldowns_col.delete_many({
            "guild_id": interaction.guild.id,
            "user_id": target_user.id
        })

        await interaction.response.send_message(
            f"✅ Reset general campaign cooldowns for {target_user.mention} in collection '{collection_name}'. "
            f"Removed {result.deleted_count} cooldown record(s).",
            ephemeral=True
        )

    @admin_reset_campaign_cooldowns.autocomplete("collection_name")
    async def collection_autocomplete(self, interaction: discord.Interaction, current: str):
        collections = ["action_cooldowns", "campaign_cooldowns", "general_action_cooldowns", "election_cooldowns"]
        return [app_commands.Choice(name=col, value=col)
                for col in collections if current.lower() in col.lower()][:25]

async def setup(bot):
    await bot.add_cog(Basics(bot))