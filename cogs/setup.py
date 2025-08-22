from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Setup cog loaded successfully")

    def _get_config(self, guild_id: int):
        """
        Returns (or creates) the config document for this guild.
        """
        col = self.bot.db["guild_configs"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "regions": [],       # list of state codes
                "start_datetime": None,
                "announcement_channel_id": None
            }
            col.insert_one(config)
        return col, config

    # Create a command group
    setup_group = app_commands.Group(
        name="setup", 
        description="Setup commands for election configuration"
    )

    @setup_group.command(
        name="add_region",
        description="Add a US state (by abbreviation) to this guild's election regions"
    )
    async def add_region(
        self,
        interaction: discord.Interaction,
        state: str  # e.g. "NY" or "California"
    ):
        col, config = self._get_config(interaction.guild.id)
        state = state.upper()
        if state in config["regions"]:
            await interaction.response.send_message(f"🔸 `{state}` is already a region.", ephemeral=True)
            return

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$push": {"regions": state}}
        )
        await interaction.response.send_message(f"✅ Added region `{state}`.", ephemeral=True)

    @setup_group.command(
        name="remove_region",
        description="Remove a US state from this guild's regions"
    )
    async def remove_region(
        self,
        interaction: discord.Interaction,
        state: str
    ):
        col, config = self._get_config(interaction.guild.id)
        state = state.upper()
        if state not in config["regions"]:
            await interaction.response.send_message(f"🔸 `{state}` isn't in the regions list.", ephemeral=True)
            return

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$pull": {"regions": state}}
        )
        await interaction.response.send_message(f"✅ Removed region `{state}`.", ephemeral=True)

    @setup_group.command(
        name="show_config",
        description="Show current election configuration"
    )
    async def show_config(self, interaction: discord.Interaction):
        _, config = self._get_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="🗳️ Election Configuration",
            color=discord.Colour.blue()
        )
        
        regions_text = ", ".join(config["regions"]) if config["regions"] else "None set"
        embed.add_field(name="Regions", value=regions_text, inline=False)
        
        start_text = config["start_datetime"] if config["start_datetime"] else "Not set"
        embed.add_field(name="Start DateTime", value=start_text, inline=False)
        
        # Show announcement channel
        channel_id = config.get("announcement_channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            channel_text = channel.mention if channel else f"Channel not found (ID: {channel_id})"
        else:
            channel_text = "Not set"
        embed.add_field(name="Announcement Channel", value=channel_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setup_group.command(
        name="list_regions",
        description="List all the US states you've added as regions"
    )
    async def list_regions(self, interaction: discord.Interaction):
        _, config = self._get_config(interaction.guild.id)
        regions = config["regions"]
        if not regions:
            await interaction.response.send_message("⚠️ No regions set yet.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "📋 **Regions:**\n" + ", ".join(regions),
                ephemeral=True
            )

    @setup_group.command(
        name="set_start",
        description="Set the start date & time for your election (format: YYYY-MM-DD HH:MM)"
    )
    async def set_start(
        self,
        interaction: discord.Interaction,
        datetime_str: str  # user inputs: "2025-08-15 14:30"
    ):
        # parse string
        try:
            start_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid format. Use `YYYY-MM-DD HH:MM`, e.g. `2025-08-15 14:30`.",
                ephemeral=True
            )
            return

        col, config = self._get_config(interaction.guild.id)
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"start_datetime": start_dt.isoformat()}}
        )
        await interaction.response.send_message(
            f"✅ Election start set to: {start_dt.strftime('%Y-%m-%d %H:%M')}",
            ephemeral=True
        )

    @setup_group.command(
        name="set_announcement_channel",
        description="Set the channel for election announcements"
    )
    async def set_announcement_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        col, config = self._get_config(interaction.guild.id)
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"announcement_channel_id": channel.id}}
        )
        await interaction.response.send_message(
            f"✅ Announcement channel set to {channel.mention}",
            ephemeral=True
        )

    @setup_group.command(
        name="remove_announcement_channel",
        description="Remove the announcement channel setting"
    )
    async def remove_announcement_channel(
        self,
        interaction: discord.Interaction
    ):
        col, config = self._get_config(interaction.guild.id)
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$unset": {"announcement_channel_id": ""}}
        )
        await interaction.response.send_message(
            "✅ Announcement channel setting removed",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Setup(bot))