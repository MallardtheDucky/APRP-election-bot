import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, List
from .presidential_winners import PRESIDENTIAL_STATE_DATA
from cogs.ideology import STATE_DATA



class GeneralCampaignActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("General Campaign Actions cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information from all signups"""
        signups_col = self.bot.db["all_signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        if not signups_config:
            return signups_col, None

        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        for candidate in signups_config.get("candidates", []):
            if (candidate["user_id"] == user_id and 
                candidate["year"] == current_year):
                return signups_col, candidate

        return signups_col, None

    def _apply_buff_debuff_multiplier_enhanced(self, base_points: float, user_id: int, guild_id: int, action_type: str) -> float:
        """Apply any active buffs or debuffs to the points gained with announcements"""
        buffs_col, buffs_config = self._get_buffs_debuffs_config(guild_id)

        active_effects = buffs_config.get("active_effects", {})
        multiplier = 1.0
        current_time = datetime.utcnow()

        # Clean up expired effects
        expired_effects = []
        for effect_id, effect in active_effects.items():
            if effect.get("expires_at", current_time) <= current_time:
                expired_effects.append(effect_id)

        if expired_effects:
            for effect_id in expired_effects:
                buffs_col.update_one(
                    {"guild_id": guild_id},
                    {"$unset": {f"active_effects.{effect_id}": ""}}
                )

        for effect_id, effect in active_effects.items():
            # Check if effect applies to this user and action
            if (effect.get("target_user_id") == user_id and 
                effect.get("expires_at") > current_time and
                (not effect.get("action_types") or action_type in effect.get("action_types", []))):

                effect_multiplier = effect.get("multiplier", 1.0)
                if effect.get("effect_type") == "buff":
                    multiplier += (effect_multiplier - 1.0)
                elif effect.get("effect_type") == "debuff":
                    multiplier *= effect_multiplier

        return base_points * max(0.1, multiplier)  # Minimum 10% effectiveness




    @app_commands.command(
        name="speech",
        description="Give a speech in a specific state with ideology alignment bonus"
    )
    @app_commands.describe(
        state="The state where you're giving the speech",
        ideology="Your campaign's ideological stance"
    )
    async def speech(
        self,
        interaction: discord.Interaction,
        state: str,
        ideology: str
    ):
        """Give a speech with potential state and ideology bonus"""
        state_key = state.upper()

        # Check if state exists in STATE_DATA
        if state_key not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ State '{state}' not found. Please enter a valid US state name.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to give speeches. Use `/signup` to register for an election first.",
                ephemeral=True
            )
            return

        state_data = STATE_DATA[state_key]

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{candidate['name']}**, please reply to this message with your campaign speech!\n\n"
            f"**State:** {state.title()}\n"
            f"**Your Ideology:** {ideology}\n"
            f"**State Ideology:** {state_data.get('ideology', 'Unknown')}\n"
            f"**Requirements:**\n"
            f"• Speech content (700-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Potential Bonus:** {'✅ Ideology match (+0.5%)' if state_data.get('ideology', '').lower() == ideology.lower() else '⚠️ No ideology match (+0.0%)'}"
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with speech
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            speech_content = reply_message.content
            char_count = len(speech_content)

            # Check character limits
            if char_count < 700 or char_count > 3000:
                await reply_message.reply(f"❌ Speech must be 700-3000 characters. You wrote {char_count} characters.")
                return

            # Check for ideology match
            ideology_match = False
            if state_data.get("ideology", "").lower() == ideology.lower():
                ideology_match = True

            # Calculate bonus based on character count and ideology match
            base_bonus = (char_count / 1000) * 0.5  # 0.5% per 1000 characters
            ideology_bonus = 0.5 if ideology_match else 0.0
            total_bonus = base_bonus + ideology_bonus

            # Create response embed
            embed = discord.Embed(
                title=f"🎤 Campaign Speech in {state.title()}",
                description=f"**{candidate['name']}** delivers a compelling speech!",
                color=discord.Color.green() if ideology_match else discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Truncate speech for display if too long
            display_speech = speech_content
            if len(display_speech) > 1000:
                display_speech = display_speech[:997] + "..."

            embed.add_field(
                name="📜 Speech Content",
                value=display_speech,
                inline=False
            )

            embed.add_field(
                name="🎯 Campaign Impact",
                value=f"**State:** {state.title()}\n"
                      f"**Your Ideology:** {ideology}\n"
                      f"**State Ideology:** {state_data.get('ideology', 'Unknown')}\n"
                      f"**Ideology Match:** {'✅ Yes (+0.5%)' if ideology_match else '❌ No (+0.0%)'}",
                inline=True
            )

            embed.add_field(
                name="📊 Speech Metrics",
                value=f"**Characters:** {char_count:,}\n"
                      f"**Base Bonus:** +{base_bonus:.2f}%\n"
                      f"**Ideology Bonus:** +{ideology_bonus:.2f}%\n"
                      f"**Total Bonus:** +{total_bonus:.2f}%",
                inline=True
            )

            if ideology_match:
                embed.add_field(
                    name="🌟 Special Bonus",
                    value="Your ideology perfectly aligns with this state's political climate!",
                    inline=False
                )

            embed.set_footer(text="Campaign Action: Speech")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your speech timed out. Please use `/speech` again and reply with your speech within 5 minutes."
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ An error occurred while processing your speech. Please try again."
            )

    @speech.autocomplete("state")
    async def state_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @speech.autocomplete("ideology")
    async def ideology_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        """Provide autocomplete options for ideologies"""
        # Get all unique ideologies from STATE_DATA
        ideologies = set()
        for state_data in STATE_DATA.values():
            if "ideology" in state_data:
                ideologies.add(state_data["ideology"])

        ideology_list = sorted(list(ideologies))
        return [app_commands.Choice(name=ideology, value=ideology)
                for ideology in ideology_list if current.lower() in ideology.lower()][:25]

    @app_commands.command(
        name="donor",
        description="General campaign donor appeal in a U.S. state (400-3000 characters, +1% per 1000 chars)"
    )
    @app_commands.describe(
        state="U.S. state for donor appeal",
        target="The candidate who will receive benefits (optional)"
    )
    async def donor(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to make donor appeals. Use `/signup` to register for an election first.",
                ephemeral=True
            )
            return

        candidate_name = candidate["name"]

        # Check cooldown (24 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "donor", 24):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "donor", 24)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before making another donor appeal.",
                    ephemeral=True
                )
                return

        # If no target specified, default to self
        if target is None:
            target = candidate_name

        # Send initial message asking for donor appeal
        await interaction.response.send_message(
            f"💰 **{candidate_name}**, please reply to this message with your donor appeal!\n\n"
            f"**Target:** {target}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Donor appeal content (400-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** Up to 3% boost based on length, +5 corruption, -1.5 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with donor appeal
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            donor_appeal = reply_message.content
            char_count = len(donor_appeal)

            # Check character limits
            if char_count < 400:
                await reply_message.reply(f"❌ Donor appeal must be at least 400 characters. You wrote {char_count} characters.")
                return

            if char_count > 3000:
                await reply_message.reply(f"❌ Donor appeal must be no more than 3000 characters. You wrote {char_count} characters.")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "donor")

            # Calculate boost - 1% per 1000 characters  
            boost = (char_count / 1000) * 1.0
            boost = min(boost, 3.0)

            # Check for state ideology match (if applicable)
            state_data = STATE_DATA.get(state_upper, {})
            state_ideology = state_data.get("ideology", "Unknown")

            # Create response embed
            embed = discord.Embed(
                title="💰 General Campaign Donor Appeal",
                description=f"**{candidate_name}** makes a donor appeal for **{target}** in {state_upper}!",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )

            # Truncate appeal for display if too long
            display_appeal = donor_appeal
            if len(display_appeal) > 800:
                display_appeal = display_appeal[:797] + "..."

            embed.add_field(
                name="📝 Donor Appeal",
                value=display_appeal,
                inline=False
            )

            embed.add_field(
                name="📊 Campaign Impact",
                value=f"**Target:** {target}\n"
                      f"**State:** {state_upper}\n"
                      f"**State Ideology:** {state_ideology}\n"
                      f"**Boost:** +{boost:.2f}%\n"
                      f"**Corruption:** +5\n"
                      f"**Characters:** {char_count:,}",
                inline=True
            )

            embed.add_field(
                name="⚠️ Warning",
                value="High corruption may lead to scandals!\nDonor appeals are high-risk, high-reward.",
                inline=True
            )

            embed.set_footer(text="Next donor appeal available in 24 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your donor appeal timed out. Please use `/donor` again and reply with your appeal within 5 minutes."
            )

    @donor.autocomplete("state")
    async def state_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="poster",
        description="Create a campaign poster in a U.S. state (0.25-0.5% points, 1 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for campaign poster",
        target="The candidate who will receive benefits (optional)",
        image="Upload your campaign poster image"
    )
    async def poster(
        self, 
        interaction: discord.Interaction, 
        state: str,
        image: discord.Attachment,
        target: Optional[str] = None
    ):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to create posters. Use `/signup` to register for an election first.",
                ephemeral=True
            )
            return

        candidate_name = candidate["name"]

        # Check cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "poster", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "poster", 6)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another poster.",
                    ephemeral=True
                )
                return

        # If no target specified, default to self
        if target is None:
            target = candidate_name

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        self._set_cooldown(interaction.guild.id, interaction.user.id, "poster")

        # Random polling boost between 0.25% and 0.5%
        polling_boost = random.uniform(0.25, 0.5)

        # Apply buff/debuff multipliers
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, candidate.get("user_id"), interaction.guild.id, "poster")

        embed = discord.Embed(
            title="🖼️ Campaign Poster",
            description=f"**{candidate_name}** creates campaign materials for **{target}** in {state_upper}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # Check for state ideology match (if applicable)
        state_data = STATE_DATA.get(state_upper, {})
        state_ideology = state_data.get("ideology", "Unknown")

        embed.add_field(
            name="📊 Campaign Impact",
            value=f"**Target:** {target}\n"
                  f"**State:** {state_upper}\n"
                  f"**State Ideology:** {state_ideology}\n"
                  f"**Boost:** +{polling_boost:.2f}%\n"
                  f"**Stamina Cost:** -1",
            inline=True
        )

        embed.add_field(
            name="📍 Distribution",
            value=f"Posted throughout {state_upper}\nsocial media and community events",
            inline=True
        )

        embed.add_field(
            name="⚡ Current Stamina",
            value=f"{candidate.get('stamina', 200) - 1}/200",
            inline=True
        )

        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 6 hours")

        await interaction.response.send_message(embed=embed)

    @poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="ad",
        description="Create a campaign video ad in a U.S. state (0.5-1% points, 1.5 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for video ad",
        target="The candidate who will receive benefits (optional)"
    )
    async def ad(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from valid US state names.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to create ads. Use `/signup` to register for an election first.",
                ephemeral=True
            )
            return

        candidate_name = candidate["name"]

        # Check cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "ad", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "ad", 6)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another ad.",
                    ephemeral=True
                )
                return

        # If no target specified, default to self
        if target is None:
            target = candidate_name

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{candidate_name}**, please reply to this message with your campaign video!\n\n"
            f"**Target:** {target}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 0.5-1% polling boost, -1.5 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id and
                    len(message.attachments) > 0)

        try:
            # Wait for user to reply with attachment
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            video = reply_message.attachments[0]

            # Check if attachment is a video
            if not video.content_type or not video.content_type.startswith('video/'):
                await reply_message.reply("❌ Please upload a video file (MP4 format preferred).")
                return

            # Check file size
            if video.size > 25 * 1024 * 1024:
                await reply_message.reply("❌ Video file too large! Maximum size is 25MB.")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "ad")

            # Random polling boost between 0.5% and 1%
            polling_boost = random.uniform(0.5, 1.0)

            # Apply buff/debuff multipliers
            polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, candidate.get("user_id"), interaction.guild.id, "ad")

            embed = discord.Embed(
                title="📺 Campaign Video Ad",
                description=f"**{candidate_name}** creates a campaign advertisement for **{target}** in {state_upper}!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            # Check for state ideology match (if applicable)
            state_data = STATE_DATA.get(state_upper, {})
            state_ideology = state_data.get("ideology", "Unknown")

            embed.add_field(
                name="📊 Ad Performance",
                value=f"**Target:** {target}\n"
                      f"**State:** {state_upper}\n"
                      f"**State Ideology:** {state_ideology}\n"
                      f"**Boost:** +{polling_boost:.2f}%\n"
                      f"**Stamina Cost:** -1.5",
                inline=True
            )

            embed.add_field(
                name="📱 Reach",
                value=f"Broadcast across {state_upper}\nsocial media and local TV",
                inline=True
            )

            embed.add_field(
                name="⚡ Current Stamina",
                value=f"{candidate.get('stamina', 200) - 1.5:.1f}/200",
                inline=True
            )

            embed.set_footer(text="Next ad available in 6 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your ad creation timed out. Please use `/ad` again and reply with your video within 5 minutes."
            )

    @poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]



    # --- Buff/Debuff Management Functions ---

    def _get_buffs_debuffs_config(self, guild_id: int):
        """Get or create campaign buffs/debuffs configuration"""
        col = self.bot.db["campaign_buffs_debuffs"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "active_effects": {}  # effect_id -> {effect_type, target_user_id, effect_name, multiplier, expires_at}
            }
            col.insert_one(config)
        return col, config



    def _check_cooldown(self, guild_id: int, user_id: int, action_type: str, hours: int):
        """Check if user is on cooldown for an action"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return True

        last_used = cooldown_record.get("last_used")
        if not last_used:
            return True

        time_since = datetime.utcnow() - last_used
        return time_since >= timedelta(hours=hours)

    def _get_cooldown_remaining(self, guild_id: int, user_id: int, action_type: str, hours: int):
        """Get remaining cooldown time"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return timedelta(0)

        last_used = cooldown_record.get("last_used")
        if not last_used:
            return timedelta(0)

        time_since = datetime.utcnow() - last_used
        cooldown_duration = timedelta(hours=hours)

        if time_since >= cooldown_duration:
            return timedelta(0)

        return cooldown_duration - time_since

    def _set_cooldown(self, guild_id: int, user_id: int, action_type: str):
        """Set cooldown for an action"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldowns_col.update_one(
            {"guild_id": guild_id, "user_id": user_id, "action_type": action_type},
            {"$set": {"last_used": datetime.utcnow()}},
            upsert=True
        )





async def setup(bot):
    await bot.add_cog(GeneralCampaignActions(bot))