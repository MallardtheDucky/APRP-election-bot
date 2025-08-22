import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import pytz

class TimeManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.time_loop.start()  # Start the time loop
        print("Time Manager cog loaded successfully")

    # Create command groups
    time_group = app_commands.Group(name="time", description="Time management commands")
    schedule_group = app_commands.Group(name="schedule", description="Schedule management commands")

    def cog_unload(self):
        self.time_loop.cancel()

    def _get_time_config(self, guild_id: int):
        """Get or create time configuration for a guild"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "minutes_per_rp_day": 28,  # Default: 28 minutes = 1 RP day
                "current_rp_date": datetime(1999, 2, 1),  # Start at signups phase
                "current_phase": "Signups",
                "cycle_year": 1999,
                "last_real_update": datetime.utcnow(),
                "voice_channel_id": None,  # Specific voice channel to update
                "update_voice_channels": True,  # Enable voice updates by default
                "phases": [
                    {"name": "Signups", "start_month": 2, "end_month": 7},
                    {"name": "Primary Campaign", "start_month": 8, "end_month": 12},
                    {"name": "Primary Election", "start_month": 1, "end_month": 2},
                    {"name": "General Campaign", "start_month": 3, "end_month": 10},
                    {"name": "General Election", "start_month": 11, "end_month": 12}
                ],
                "regions": [
                    "Columbia", "Cambridge", "Superior", "Austin", 
                    "Heartland", "Yellowstone", "Phoenix"
                ]
            }
            col.insert_one(config)
        return config

    def _calculate_current_rp_time(self, config):
        """Calculate current RP time based on real time elapsed"""
        last_update = config["last_real_update"]
        current_real_time = datetime.utcnow()
        real_minutes_elapsed = (current_real_time - last_update).total_seconds() / 60

        minutes_per_rp_day = config["minutes_per_rp_day"]
        rp_days_elapsed = real_minutes_elapsed / minutes_per_rp_day

        current_rp_date = config["current_rp_date"] + timedelta(days=rp_days_elapsed)

        # Determine current phase
        current_phase = self._get_current_phase(current_rp_date, config)

        return current_rp_date, current_phase

    def _get_current_phase(self, rp_date, config):
        """Determine which phase we're currently in"""
        month = rp_date.month
        year = rp_date.year

        # Determine if this is a primary year (odd) or general year (even)
        is_primary_year = year % 2 == 1  # Odd years are primary years
        is_general_year = year % 2 == 0  # Even years are general years

        for phase in config["phases"]:
            if phase["name"] in ["Signups", "Primary Campaign", "Primary Election"] and is_primary_year:
                # Primary phases occur in odd years
                if month >= phase["start_month"] and month <= phase["end_month"]:
                    return phase["name"]
            elif phase["name"] in ["General Campaign", "General Election"] and is_general_year:
                # General phases occur in even years  
                if month >= phase["start_month"] and month <= phase["end_month"]:
                    return phase["name"]

        return "Between Phases"

    @tasks.loop(minutes=1)
    async def time_loop(self):
        """Update RP time every minute"""
        try:
            col = self.bot.db["time_configs"]
            configs = col.find({})

            for config in configs:
                current_rp_date, current_phase = self._calculate_current_rp_time(config)
                guild = self.bot.get_guild(config["guild_id"])

                if not guild:
                    continue

                # Check if phase changed
                if current_phase != config["current_phase"]:
                    # Phase transition occurred
                    old_phase = config["current_phase"]

                    # Dispatch event to elections cog for automatic handling
                    elections_cog = self.bot.get_cog("Elections")
                    if elections_cog:
                        await elections_cog.on_phase_change(
                            config["guild_id"], 
                            old_phase, 
                            current_phase, 
                            current_rp_date.year
                        )

                    # Find a general channel to announce phase change
                    channel = discord.utils.get(guild.channels, name="general") or guild.system_channel
                    if channel:
                        embed = discord.Embed(
                            title="🗳️ Election Phase Change",
                            description=f"We have entered the **{current_phase}** phase!",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(
                            name="Current RP Date", 
                            value=current_rp_date.strftime("%B %d, %Y"), 
                            inline=True
                        )
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass  # Ignore if can't send message

                # Update database
                col.update_one(
                    {"guild_id": config["guild_id"]},
                    {
                        "$set": {
                            "current_rp_date": current_rp_date,
                            "current_phase": current_phase,
                            "last_real_update": datetime.utcnow()
                        }
                    }
                )

                # Check if we need to auto-reset cycle (after General Election ends)
                if (current_phase == "General Election" and 
                    current_rp_date.month == 12 and current_rp_date.day >= 31):
                    # Auto-reset to next cycle (next odd year for signups)
                    next_year = current_rp_date.year + 1
                    new_rp_date = datetime(next_year, 2, 1)

                    col.update_one(
                        {"guild_id": config["guild_id"]},
                        {
                            "$set": {
                                "current_rp_date": new_rp_date,
                                "current_phase": "Signups",
                                "last_real_update": datetime.utcnow()
                            }
                        }
                    )

                    # Dispatch event to elections cog for new cycle automation
                    elections_cog = self.bot.get_cog("Elections")
                    if elections_cog:
                        await elections_cog.on_phase_change(
                            config["guild_id"], 
                            "General Election", 
                            "Signups", 
                            next_year
                        )

                    # Announce new cycle
                    channel = discord.utils.get(guild.channels, name="general") or guild.system_channel
                    if channel:
                        embed = discord.Embed(
                            title="🔄 New Election Cycle Started!",
                            description=f"The {next_year} election cycle has begun! We are now in the **Signups** phase.",
                            color=discord.Color.gold(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(
                            name="New RP Date", 
                            value=new_rp_date.strftime("%B %d, %Y"), 
                            inline=True
                        )
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass

                # Update voice channel if enabled and configured
                if (config.get("update_voice_channels", True) and 
                    config.get("voice_channel_id")):
                    date_string = current_rp_date.strftime("%B %d, %Y")
                    channel = guild.get_channel(config["voice_channel_id"])
                    if channel and hasattr(channel, 'edit'):  # Check if it's a voice channel
                        try:
                            new_name = f"📅 {date_string}"
                            if channel.name != new_name:
                                await channel.edit(name=new_name)
                                print(f"Updated voice channel to: {new_name}")
                        except Exception as e:
                            print(f"Failed to update voice channel: {e}")
                            pass  # Ignore if can't edit channel

        except Exception as e:
            print(f"Error in time loop: {e}")

    @time_loop.before_loop
    async def before_time_loop(self):
        await self.bot.wait_until_ready()

    @time_group.command(
        name="current_time",
        description="Show the current RP date and election phase"
    )
    async def current_time(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        current_rp_date, current_phase = self._calculate_current_rp_time(config)

        embed = discord.Embed(
            title="🕒 Current Election Time",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="RP Date", 
            value=current_rp_date.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(name="Current Phase", value=current_phase, inline=True)
        embed.add_field(
            name="Cycle Year", 
            value=str(config["cycle_year"]), 
            inline=True
        )
        embed.add_field(
            name="Time Scale", 
            value=f"{config['minutes_per_rp_day']} real minutes = 1 RP day", 
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="set_current_time",
        description="Set the current RP date and time"
    )
    async def set_current_time(
        self, 
        interaction: discord.Interaction, 
        year: int, 
        month: int, 
        day: int = 1
    ):
        # Validate input
        if month < 1 or month > 12:
            await interaction.response.send_message(
                "❌ Month must be between 1 and 12.", 
                ephemeral=True
            )
            return

        if day < 1 or day > 31:
            await interaction.response.send_message(
                "❌ Day must be between 1 and 31.", 
                ephemeral=True
            )
            return

        try:
            new_date = datetime(year, month, day)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date provided.", 
                ephemeral=True
            )
            return

        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        # Determine the new phase
        new_phase = self._get_current_phase(new_date, config)

        # Update the configuration
        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "current_rp_date": new_date,
                    "current_phase": new_phase,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        embed = discord.Embed(
            title="🕒 RP Time Updated",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="New RP Date", 
            value=new_date.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(name="Current Phase", value=new_phase, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="set_time_scale",
        description="Set how many real minutes equal one RP day"
    )
    async def set_time_scale(
        self, 
        interaction: discord.Interaction, 
        minutes_per_day: int
    ):
        if minutes_per_day < 1 or minutes_per_day > 1440:
            await interaction.response.send_message(
                "❌ Minutes per day must be between 1 and 1440.", 
                ephemeral=True
            )
            return

        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        # Update current time before changing scale
        current_rp_date, current_phase = self._calculate_current_rp_time(config)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "minutes_per_rp_day": minutes_per_day,
                    "current_rp_date": current_rp_date,
                    "current_phase": current_phase,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        await interaction.response.send_message(
            f"✅ Time scale updated: {minutes_per_day} real minutes = 1 RP day",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="reset_cycle",
        description="Reset the election cycle to the beginning (Signups phase)"
    )
    async def reset_cycle(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        current_year = config["current_rp_date"].year
        # Find next odd year for signups
        next_signup_year = current_year + 1 if current_year % 2 == 0 else current_year + 2

        col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "current_rp_date": datetime(next_signup_year, 2, 1),
                    "current_phase": "Signups",
                    "cycle_year": next_signup_year,
                    "last_real_update": datetime.utcnow()
                }
            }
        )

        await interaction.response.send_message(
            f"✅ Election cycle reset! Now in Signups phase for {next_signup_year} cycle.",
            ephemeral=True
        )

    @app_commands.command(
        name="show_regions",
        description="Show all available election regions"
    )
    async def show_regions(self, interaction: discord.Interaction):
        # Get regions from election configuration instead of time config
        elections_col = self.bot.db["elections_config"]
        elections_config = elections_col.find_one({"guild_id": interaction.guild.id})

        if not elections_config or not elections_config.get("seats"):
            await interaction.response.send_message("❌ No election regions configured yet.", ephemeral=True)
            return

        # Extract unique states/regions from election seats
        regions = set()
        for seat in elections_config["seats"]:
            regions.add(seat["state"])

        regions = sorted(list(regions))

        embed = discord.Embed(
            title="🗺️ Election Regions",
            description="\n".join([f"• {region}" for region in regions]),
            color=discord.Color.blue()
        )

        # Add seat count for each region
        region_counts = {}
        for seat in elections_config["seats"]:
            state = seat["state"]
            region_counts[state] = region_counts.get(state, 0) + 1

        details = ""
        for region in regions:
            details += f"**{region}**: {region_counts[region]} seats\n"

        embed.add_field(
            name="📊 Seat Distribution",
            value=details,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="show_phases",
        description="Show all election phases and their timing"
    )
    async def show_phases(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]
        current_rp_date, current_phase = self._calculate_current_rp_time(config)

        embed = discord.Embed(
            title="🗓️ Current Election Phase",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Add current date and phase
        embed.add_field(
            name="Current Date", 
            value=current_rp_date.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(
            name="Current Phase", 
            value=current_phase, 
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing

        # Add cycle schedule
        current_year = current_rp_date.year
        schedule_text = "📋 **Annual Election Cycle**\n\n"

        # Show current and next year phases
        for year_offset in [0, 1]:
            year = current_year + year_offset
            is_primary_year = year % 2 == 1
            is_general_year = year % 2 == 0

            if is_primary_year:
                year_phases = [p for p in config["phases"] if p["name"] in ["Signups", "Primary Campaign", "Primary Election"]]
                schedule_text += f"**{year} (Primary Year)**\n"
            else:
                year_phases = [p for p in config["phases"] if p["name"] in ["General Campaign", "General Election"]]
                schedule_text += f"**{year} (General Year)**\n"

            for phase in year_phases:
                if phase["name"] == current_phase and year == current_year:
                    phase_line = f"📍 {phase['name']} ⬅️ Current\n"
                else:
                    phase_line = f"{phase['name']}\n"
                phase_line += f"Months {phase['start_month']}-{phase['end_month']}\n"
                schedule_text += phase_line
            schedule_text += "\n"

        embed.add_field(name="\u200b", value=schedule_text, inline=False)

        # Add cycle info
        cycle_info = f"ℹ️ **Cycle Info**\n"
        cycle_info += f"Cycle Start Year: {config['cycle_year']}\n"
        cycle_info += f"Status: ▶️ Running"

        embed.add_field(name="\u200b", value=cycle_info, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="set_voice_channel",
        description="Set which voice channel to update with RP date"
    )
    async def set_voice_channel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.VoiceChannel
    ):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"voice_channel_id": channel.id}}
        )

        await interaction.response.send_message(
            f"✅ Voice channel set to {channel.mention}. It will be updated with the current RP date.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="toggle_voice_updates",
        description="Toggle automatic voice channel name updates with current RP date"
    )
    async def toggle_voice_updates(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        current_setting = config.get("update_voice_channels", True)
        new_setting = not current_setting

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"update_voice_channels": new_setting}}
        )

        status = "enabled" if new_setting else "disabled"
        await interaction.response.send_message(
            f"✅ Voice channel date updates have been **{status}**.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @time_group.command(
        name="update_voice_channel",
        description="Manually update the configured voice channel with current RP date"
    )
    async def update_voice_channel(self, interaction: discord.Interaction):
        config = self._get_time_config(interaction.guild.id)
        col = self.bot.db["time_configs"]

        if not config.get("voice_channel_id"):
            await interaction.response.send_message(
                "❌ No voice channel configured. Use `/set_voice_channel` first.",
                ephemeral=True
            )
            return

        current_rp_date, current_phase = self._calculate_current_rp_time(config)
        date_string = current_rp_date.strftime("%B %d, %Y")

        channel = interaction.guild.get_channel(config["voice_channel_id"])
        if not channel:
            await interaction.response.send_message(
                "❌ Configured voice channel not found.",
                ephemeral=True
            )
            return

        try:
            new_name = f"📅 {date_string}"
            await channel.edit(name=new_name)
            await interaction.response.send_message(
                f"✅ Updated {channel.mention} with date: **{date_string}**",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to update voice channel: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(TimeManager(bot))