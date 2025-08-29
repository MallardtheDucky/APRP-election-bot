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

    def _get_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get candidate information by name from appropriate collection based on phase"""
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        current_phase = time_config.get("current_phase", "") if time_config else ""

        # During General Campaign, look in winners collection for primary winners
        if current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if winners_config and "winners" in winners_config:
                for winner in winners_config["winners"]:
                    if (winner.get("candidate", "").lower() == candidate_name.lower() and 
                        winner.get("year") == current_year and
                        winner.get("primary_winner", False)):
                        return winners_col, winner

        # For other phases or fallback, look in all_signups
        signups_col = self.bot.db["all_signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})

        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if (candidate.get("name", "").lower() == candidate_name.lower() and 
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
        ideology="Your campaign's ideological stance",
        target="The candidate who will receive benefits (optional)"
    )
    async def speech(
        self,
        interaction: discord.Interaction,
        state: str,
        ideology: str,
        target: Optional[str] = None
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

        state_data = STATE_DATA[state_key]

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "speech", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "speech", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before giving another speech.",
                    ephemeral=True
                )
                return

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{candidate_name}**, please reply to this message with your campaign speech!\n\n"
            f"**Target:** {target}\n"
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

            # Determine who pays stamina cost
            stamina_cost = 1.5
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                signups_col_temp, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina for this speech! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "speech")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Check for ideology match
            ideology_match = False
            if state_data.get("ideology", "").lower() == ideology.lower():
                ideology_match = True

            # Calculate bonus based on character count and ideology match
            base_bonus = (char_count / 1000) * 0.5  # 0.5% per 1000 characters
            ideology_bonus = 0.5 if ideology_match else 0.0
            total_bonus = base_bonus + ideology_bonus

            # Add momentum during General Campaign
            self._add_momentum_from_general_action(interaction.guild.id, interaction.user.id, state_key, total_bonus, candidate, target)

            # Create response embed
            embed = discord.Embed(
                title=f"🎤 Campaign Speech in {state.title()}",
                description=f"**{candidate_name}** delivers a compelling speech!",
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

            embed.set_footer(text="Next speech available in 1 hour")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your speech timed out. Please use `/speech` again and reply with your speech within 5 minutes."
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ An error occurred while processing your speech. Please try again."
            )

    @speech.autocomplete("target")
    async def target_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

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

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "donor", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "donor", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before making another donor appeal.",
                    ephemeral=True
                )
                return

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

            # Determine who pays stamina cost
            stamina_cost = 1.5
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                signups_col_temp, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina for this donor appeal! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "donor")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Calculate boost - 1% per 1000 characters  
            boost = (char_count / 1000) * 1.0
            boost = min(boost, 3.0)

            # Add momentum during General Campaign
            self._add_momentum_from_general_action(interaction.guild.id, interaction.user.id, state_upper, boost, candidate, target)

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

            # Get state ideology data
            state_data = STATE_DATA.get(state_upper, {})
            state_ideology = state_data.get("ideology", "Unknown")

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

            embed.set_footer(text="Next donor appeal available in 1 hour")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate_name}**, your donor appeal timed out. Please use `/donor` again and reply with your appeal within 5 minutes."
            )

    @donor.autocomplete("target")
    async def target_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

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
        target="The candidate who will receive benefits (optional)"
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

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "poster", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "poster", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another poster.",
                    ephemeral=True
                )
                return

        # Defer the response early to prevent timeout
        await interaction.response.defer()

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.followup.send(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:
            await interaction.followup.send(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Determine who pays stamina cost
        stamina_cost = 1
        stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

        # Check if stamina user has enough stamina
        stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
        if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
            # Get stamina user's candidate data
            signups_col_temp, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

        stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
        if stamina_amount < stamina_cost:
            stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
            await interaction.followup.send(
                f"❌ {stamina_user_name} doesn't have enough stamina to create a poster! They need at least {stamina_cost} stamina (current: {stamina_amount}).",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        self._set_cooldown(interaction.guild.id, interaction.user.id, "poster")

        # Deduct stamina from the determined user
        self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

        # Random polling boost between 0.25% and 0.5%
        polling_boost = random.uniform(0.25, 0.5)

        # Apply buff/debuff multipliers
        user_id = candidate.get("user_id") if candidate else interaction.user.id
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "poster")

        # Add momentum during General Campaign
        self._add_momentum_from_general_action(interaction.guild.id, interaction.user.id, state_upper, polling_boost, candidate, target)

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

        current_stamina = candidate.get('stamina', 200) if candidate and isinstance(candidate, dict) else 200
        embed.add_field(
            name="⚡ Current Stamina",
            value=f"{current_stamina - 1}/200",
            inline=True
        )

        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 1 hour")

        await interaction.followup.send(embed=embed)

    @poster.autocomplete("target")
    async def target_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

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

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "ad", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "ad", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before creating another ad.",
                    ephemeral=True
                )
                return

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

            # Determine who pays stamina cost
            stamina_cost = 1.5
            stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

            # Check if stamina user has enough stamina
            stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
            if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
                # Get stamina user's candidate data
                signups_col_temp, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

            stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
            if stamina_amount < stamina_cost:
                stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
                await reply_message.reply(f"❌ {stamina_user_name} doesn't have enough stamina to create an ad! They need at least {stamina_cost} stamina (current: {stamina_amount}).")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "ad")

            # Deduct stamina from the determined user
            self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

            # Random polling boost between 0.5% and 1%
            polling_boost = random.uniform(0.5, 1.0)

            # Apply buff/debuff multipliers
            user_id = candidate.get("user_id") if candidate else interaction.user.id
            polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "ad")

            # Add momentum during General Campaign
            self._add_momentum_from_general_action(interaction.guild.id, interaction.user.id, state_upper, polling_boost, candidate, target)

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

            current_stamina = candidate.get('stamina', 200) if candidate and isinstance(candidate, dict) else 200
            embed.add_field(
                name="⚡ Current Stamina",
                value=f"{current_stamina - 1.5:.1f}/200",
                inline=True
            )

            embed.set_footer(text="Next ad available in 1 hour")

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

    @ad.autocomplete("target")
    async def target_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="canvassing",
        description="Door-to-door canvassing in a U.S. state (0.1% points, 1 stamina, message required)"
    )
    @app_commands.describe(
        state="U.S. state for canvassing",
        canvassing_message="Your canvassing message (100-300 characters)",
        target="The candidate who will receive benefits (optional)"
    )
    async def canvassing(
        self,
        interaction: discord.Interaction,
        state: str,
        canvassing_message: str,
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

        # Check if user has a registered candidate (optional)
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        # Use candidate name if registered, otherwise use display name
        candidate_name = candidate["name"] if candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if candidate:
                target = candidate_name
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (1 hour)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "canvassing", 1):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "canvassing", 1)
            if remaining:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before canvassing again.",
                    ephemeral=True
                )
                return

        # Check character limits for canvassing message
        char_count = len(canvassing_message)
        if char_count < 100 or char_count > 300:
            await interaction.response.send_message(
                f"❌ Canvassing message must be 100-300 characters. You wrote {char_count} characters.",
                ephemeral=True
            )
            return

        # Determine who pays stamina cost
        stamina_cost = 1
        stamina_user_id = self._determine_stamina_user(interaction.guild.id, interaction.user.id, target_candidate, stamina_cost)

        # Check if stamina user has enough stamina
        stamina_user_candidate = target_candidate if stamina_user_id == target_candidate.get("user_id") else None
        if not stamina_user_candidate and stamina_user_id != target_candidate.get("user_id"):
            # Get stamina user's candidate data
            signups_col_temp, stamina_user_candidate = self._get_user_candidate(interaction.guild.id, stamina_user_id)

        stamina_amount = stamina_user_candidate.get("stamina", 0) if stamina_user_candidate else 0
        if stamina_amount < stamina_cost:
            stamina_user_name = stamina_user_candidate.get("name", "Unknown") if stamina_user_candidate else "Unknown"
            await interaction.response.send_message(
                f"❌ {stamina_user_name} doesn't have enough stamina for canvassing! They need at least {stamina_cost} stamina (current: {stamina_amount}).",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        self._set_cooldown(interaction.guild.id, interaction.user.id, "canvassing")

        # Deduct stamina from the determined user
        self._deduct_stamina_from_user(interaction.guild.id, stamina_user_id, stamina_cost)

        # Fixed polling boost of 0.1%
        polling_boost = 0.1

        # Apply buff/debuff multipliers
        user_id = candidate.get("user_id") if candidate else interaction.user.id
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, user_id, interaction.guild.id, "canvassing")

        # Add momentum during General Campaign
        self._add_momentum_from_general_action(interaction.guild.id, interaction.user.id, state_upper, polling_boost, candidate, target)

        embed = discord.Embed(
            title="🚪 Door-to-Door Canvassing",
            description=f"**{candidate_name}** goes canvassing for **{target}** in {state_upper}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="💬 Canvassing Message",
            value=canvassing_message,
            inline=False
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
            name="🏘️ Ground Game",
            value=f"Door-to-door outreach in {state_upper}\nBuilding grassroots support",
            inline=True
        )

        current_stamina = candidate.get('stamina', 200) if candidate and isinstance(candidate, dict) else 200
        embed.add_field(
            name="⚡ Current Stamina",
            value=f"{current_stamina - 1}/200",
            inline=True
        )

        embed.set_footer(text="Next canvassing available in 1 hour")

        await interaction.response.send_message(embed=embed)

    @canvassing.autocomplete("target")
    async def target_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        return await self._get_candidate_choices_autocomplete(interaction, current)

    @canvassing.autocomplete("state")
    async def state_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state.title(), value=state)
                for state in states if current.upper() in state][:25]

    async def _get_candidate_choices_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice]:
        """Helper to get candidate choices for autocompletion"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year if time_config else 2024
        current_phase = time_config.get("current_phase", "")

        candidate_choices = []

        # During General Campaign, get primary winners from all_winners
        if current_phase == "General Campaign":
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config and "winners" in winners_config:
                for winner in winners_config["winners"]:
                    if (winner.get("year") == current_year and 
                        winner.get("primary_winner", False)):
                        candidate_name = winner.get("candidate")
                        if candidate_name and current.lower() in candidate_name.lower():
                            if len(candidate_choices) < 25:
                                candidate_choices.append(app_commands.Choice(name=candidate_name, value=candidate_name))
                            else:
                                break

        # During other phases, get from signups
        else:
            signups_col = self.bot.db["all_signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            if signups_config and "candidates" in signups_config:
                for candidate in signups_config["candidates"]:
                    if candidate.get("year") == current_year:
                        candidate_name = candidate.get("name")
                        if candidate_name and current.lower() in candidate_name.lower():
                            if len(candidate_choices) < 25:
                                candidate_choices.append(app_commands.Choice(name=candidate_name, value=candidate_name))
                            else:
                                break

        return candidate_choices


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

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate zero-sum redistribution percentages for general election candidates"""
        # Get general election candidates (primary winners) for this seat
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})

        if not winners_config:
            return {}

        # Get current year
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        current_phase = time_config.get("current_phase", "") if time_config else ""

        # Find all primary winners (general election candidates) for this seat
        # For general campaign, look for primary winners from the previous year if we're in an even year
        # Or current year if odd year
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        seat_candidates = [
            w for w in winners_config["winners"]
            if w["seat_id"] == seat_id and w["year"] == primary_year and w.get("primary_winner", False)
        ]

        # If no primary winners found, fall back to all candidates for this seat in the current year
        if not seat_candidates:
            seat_candidates = [
                w for w in winners_config["winners"]
                if w["seat_id"] == seat_id and w["year"] == current_year
            ]

        if not seat_candidates:
            return {}

        # Calculate baseline percentages based on party alignment
        baseline_percentages = {}
        num_candidates = len(seat_candidates)

        # Count major parties
        major_parties = ["Democratic", "Republican"]
        parties_present = set(candidate.get("party", "") for candidate in seat_candidates)
        major_parties_present = [party for party in major_parties if party in parties_present]

        if len(major_parties_present) == 2:
            # Standard two-party setup
            num_parties = len(parties_present)
            if num_parties == 2:
                # Pure two-party race
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 50.0
            else:
                # Two major parties + others
                remaining_percentage = 20.0  # 100 - 40 - 40
                other_parties_count = num_parties - 2
                other_party_percentage = remaining_percentage / other_parties_count if other_parties_count > 0 else 0

                for candidate in seat_candidates:
                    if candidate["party"] in major_parties:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                    else:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = other_party_percentage
        else:
            # No standard major party setup, split evenly
            for candidate in seat_candidates:
                baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 100.0 / num_candidates

        # Apply proportional redistribution with minimum floors
        final_percentages = {}

        # Define minimum percentage floors
        def get_minimum_floor(candidate):
            party = candidate.get('party', '').lower()
            if any(keyword in party for keyword in ['democrat', 'republican']):
                return 25.0  # 25% minimum for major parties
            else:
                return 2.0   # 2% minimum for independents/third parties

        # Calculate total campaign points across all candidates in this seat
        total_campaign_points = sum(candidate.get('points', 0.0) for candidate in seat_candidates)

        # Start with baseline percentages
        current_percentages = baseline_percentages.copy()

        # Apply campaign effects using proportional redistribution
        if total_campaign_points > 0:
            for candidate in seat_candidates:
                candidate_name = candidate.get('candidate', candidate.get('name', ''))
                candidate_points = candidate.get('points', 0.0)

                if candidate_points > 0:
                    # This candidate gains points
                    points_gained = candidate_points

                    # Calculate total percentage that can be taken from other candidates
                    total_available_to_take = 0.0
                    for other_candidate in seat_candidates:
                        if other_candidate != candidate:
                            other_name = other_candidate.get('candidate', other_candidate.get('name', ''))
                            other_current = current_percentages[other_name]
                            other_minimum = get_minimum_floor(other_candidate)
                            available = max(0, other_current - other_minimum)
                            total_available_to_take += available

                    # Limit gains to what's actually available
                    actual_gain = min(points_gained, total_available_to_take)
                    current_percentages[candidate_name] += actual_gain

                    # Distribute losses proportionally among other candidates
                    if total_available_to_take > 0 and actual_gain > 0:
                        for other_candidate in seat_candidates:
                            if other_candidate != candidate:
                                other_name = other_candidate.get('candidate', other_candidate.get('name', ''))
                                other_current = current_percentages[other_name]
                                other_minimum = get_minimum_floor(other_candidate)
                                available = max(0, other_current - other_minimum)
                                
                                if available > 0:
                                    loss_proportion = available / total_available_to_take
                                    loss = actual_gain * loss_proportion
                                    current_percentages[other_name] -= loss

        # Ensure percentages sum to 100% and respect minimums
        total_percentage = sum(current_percentages.values())
        if total_percentage > 0:
            for candidate_name in current_percentages:
                current_percentages[candidate_name] = (current_percentages[candidate_name] / total_percentage) * 100.0

        # Final verification and correction for floating point errors
        final_total = sum(current_percentages.values())
        if abs(final_total - 100.0) > 0.001:
            # Apply micro-adjustment to the largest percentage instead of equal distribution
            largest_candidate = max(current_percentages.keys(), key=lambda x: current_percentages[x])
            adjustment = 100.0 - final_total
            current_percentages[largest_candidate] += adjustment

        final_percentages = current_percentages
        return final_percentages

    def _add_momentum_from_general_action(self, guild_id: int, user_id: int, state_name: str, points_gained: float, candidate_data: dict = None, target_name: str = None):
        """Adds momentum to a state based on general campaign actions."""
        try:
            # Check if we're in General Campaign phase
            time_col, time_config = self._get_time_config(guild_id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            if current_phase != "General Campaign":
                return

            # Use the momentum system from the momentum cog
            momentum_cog = self.bot.get_cog('Momentum')
            if not momentum_cog:
                return

            # Get momentum config
            momentum_col, momentum_config = momentum_cog._get_momentum_config(guild_id)

            # Determine which candidate's party to use for momentum
            target_candidate = candidate_data
            if target_name and (not candidate_data or target_name != candidate_data.get("name")):
                # Look for the target candidate in all signups
                signups_col = self.bot.db["all_signups"]
                signups_config = signups_col.find_one({"guild_id": guild_id})

                if signups_config:
                    current_year = time_config["current_rp_date"].year if time_config else 2024
                    for candidate in signups_config.get("candidates", []):
                        if (candidate.get("name", "").lower() == target_name.lower() and 
                            candidate["year"] == current_year):
                            target_candidate = candidate
                            break

            # If we still don't have a target candidate, try to find them in winners (for General Campaign)
            if not target_candidate and target_name:
                winners_col = self.bot.db["winners"]
                winners_config = winners_col.find_one({"guild_id": guild_id})

                if winners_config and "winners" in winners_config:
                    current_year = time_config["current_rp_date"].year if time_config else 2024
                    for winner in winners_config["winners"]:
                        if (winner.get("candidate", "").lower() == target_name.lower() and 
                            winner.get("year") == current_year and
                            winner.get("primary_winner", False)):
                            # Create a temporary candidate dict with party info
                            target_candidate = {
                                "name": winner.get("candidate"),
                                "party": winner.get("party", "Independent")
                            }
                            break

            if not target_candidate or not isinstance(target_candidate, dict) or not target_candidate.get("party"):
                return

            # Determine party key
            party = target_candidate.get("party", "").lower()

            if "republican" in party or "gop" in party:
                party_key = "Republican"
            elif "democrat" in party or "democratic" in party:
                party_key = "Democrat"
            else:
                party_key = "Independent"

            # Validate state name exists in momentum config
            if state_name not in momentum_config["state_momentum"]:
                return

            # Calculate campaign effectiveness multiplier based on current momentum
            current_momentum = momentum_config["state_momentum"].get(state_name, {}).get(party_key, 0.0)
            campaign_multiplier = momentum_cog._calculate_momentum_campaign_multiplier(state_name, party_key, momentum_config)
            
            # Apply momentum multiplier to the original campaign points
            boosted_points = points_gained * campaign_multiplier
            
            print(f"DEBUG: General campaign - Original points: {points_gained:.2f}, Momentum multiplier: {campaign_multiplier:.2f}x, Boosted points: {boosted_points:.2f}")

            # Calculate momentum gained
            momentum_gain_factor = 1.5  # Slightly less than presidential actions
            momentum_gained = boosted_points * momentum_gain_factor

            new_momentum = current_momentum + momentum_gained

            # Check for auto-collapse and apply if needed
            final_momentum, collapsed = momentum_cog._check_and_apply_auto_collapse(
                momentum_col, guild_id, state_name, party_key, new_momentum
            )

            if not collapsed:
                # Update momentum in database
                momentum_col.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            f"state_momentum.{state_name}.{party_key}": final_momentum,
                            f"state_momentum.{state_name}.last_updated": datetime.utcnow()
                        }
                    }
                )

                # Log the momentum gain event
                if momentum_gained > 0.1:
                    action_desc = f"General campaign action for {target_candidate.get('name', 'Unknown')} (+{points_gained:.1f} pts)"
                    momentum_cog._add_momentum_event(
                        momentum_col, guild_id, state_name, party_key,
                        momentum_gained, action_desc, user_id
                    )

        except Exception as e:
            print(f"Error in _add_momentum_from_general_action: {e}")

    def _determine_stamina_user(self, guild_id: int, user_id: int, target_candidate_data: dict, stamina_cost: float):
        """Determines whether the user or the target candidate pays the stamina cost."""
        # Get the user's candidate data
        _, user_candidate_data = self._get_user_candidate(guild_id, user_id)

        # If the user is a candidate and has enough stamina, they pay.
        if user_candidate_data and user_candidate_data.get("stamina", 0) >= stamina_cost:
            return user_id

        # Otherwise, the target candidate pays if they exist and have enough stamina.
        if target_candidate_data and target_candidate_data.get("stamina", 0) >= stamina_cost:
            return target_candidate_data.get("user_id")

        # If neither can pay, return the target's user ID as a fallback (though the action will likely fail).
        return target_candidate_data.get("user_id") if target_candidate_data else user_id

    def _deduct_stamina_from_user(self, guild_id: int, user_id: int, cost: float):
        """Deducts stamina from a user's candidate profile."""
        signups_col = self.bot.db["all_signups"]
        signups_col.update_one(
            {"guild_id": guild_id, "candidates.user_id": user_id},
            {"$inc": {"candidates.$[elem].stamina": -cost}},
            array_filters=[{"elem.user_id": user_id}]
        )


async def setup(bot):
    await bot.add_cog(GeneralCampaignActions(bot))