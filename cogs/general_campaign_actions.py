import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, List

class GeneralCampaignActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("General Campaign Actions cog loaded successfully")

    def _get_signups_config(self, guild_id: int):
        """Get signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information"""
        # Check if we're in general campaign phase
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in winners collection for general campaign
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config["winners"]:
                if (winner["user_id"] == user_id and 
                    winner.get("primary_winner", False) and 
                    winner["year"] == primary_year):
                    return winners_col, winner

            return winners_col, None
        else:
            # Look in signups collection for primary campaign
            signups_col, signups_config = self._get_signups_config(guild_id)

            if not signups_config:
                return None, None

            for candidate in signups_config["candidates"]:
                if candidate["user_id"] == user_id and candidate["year"] == current_year:
                    return signups_col, candidate

            return signups_col, None

    def _get_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get candidate by name"""
        # Check if we're in general campaign phase
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in winners collection for general campaign
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": guild_id})

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config["winners"]:
                if (winner["candidate"].lower() == candidate_name.lower() and 
                    winner.get("primary_winner", False) and
                    winner["year"] == primary_year):
                    return winners_col, winner

            return winners_col, None
        else:
            # Look in signups collection for primary campaign
            signups_col, signups_config = self._get_signups_config(guild_id)

            if not signups_config:
                return None, None

            for candidate in signups_config["candidates"]:
                if candidate["name"].lower() == candidate_name.lower() and candidate["year"] == current_year:
                    return signups_col, candidate

            return signups_col, None

    def _update_candidate_stats(self, signups_col, guild_id: int, user_id: int, 
                               polling_boost: float = 0, stamina_cost: int = 0, 
                               corruption_increase: int = 0):
        """Update candidate's polling, stamina, and corruption"""
        # Check if we're in general campaign phase
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        if current_phase == "General Campaign":
            # For general campaign, update in winners collection
            winners_col = self.bot.db["winners"]
            winners_col.update_one(
                {"guild_id": guild_id, "winners.user_id": user_id},
                {
                    "$inc": {
                        "winners.$.points": polling_boost,
                        "winners.$.stamina": -stamina_cost,
                        "winners.$.corruption": corruption_increase
                    }
                }
            )
        else:
            # For primary campaign, update in signups collection
            signups_col.update_one(
                {"guild_id": guild_id, "candidates.user_id": user_id},
                {
                    "$inc": {
                        "candidates.$.points": polling_boost,
                        "candidates.$.stamina": -stamina_cost,
                        "candidates.$.corruption": corruption_increase
                    }
                }
            )

    def _check_cooldown(self, guild_id: int, user_id: int, action_type: str, cooldown_hours: int):
        """Check if user is on cooldown for a specific action"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return True  # No cooldown record, user can proceed

        last_action = cooldown_record["last_action"]
        cooldown_end = last_action + timedelta(hours=cooldown_hours)

        return datetime.utcnow() >= cooldown_end

    def _set_cooldown(self, guild_id: int, user_id: int, action_type: str):
        """Set cooldown for a specific action"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldowns_col.update_one(
            {"guild_id": guild_id, "user_id": user_id, "action_type": action_type},
            {
                "$set": {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "action_type": action_type,
                    "last_action": datetime.utcnow()
                }
            },
            upsert=True
        )

    def _get_cooldown_remaining(self, guild_id: int, user_id: int, action_type: str, cooldown_hours: int):
        """Get remaining cooldown time"""
        cooldowns_col = self.bot.db["action_cooldowns"]
        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action_type": action_type
        })

        if not cooldown_record:
            return None

        last_action = cooldown_record["last_action"]
        cooldown_end = last_action + timedelta(hours=cooldown_hours)
        remaining = cooldown_end - datetime.utcnow()

        if remaining.total_seconds() <= 0:
            return None

        return remaining

    def _calculate_baseline_percentage(self, guild_id: int, seat_id: str, candidate_party: str = None):
        """Calculate baseline starting percentage based on party distribution for a seat"""
        # Get general election candidates (primary winners) for this seat
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})

        if not winners_config:
            return 50.0  # Default fallback

        # Get current year
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Find all primary winners (general election candidates) for this seat
        seat_candidates = [
            w for w in winners_config["winners"] 
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        if not seat_candidates:
            return 50.0  # Default if no candidates

        # Count unique parties
        parties = set(candidate["party"] for candidate in seat_candidates)
        num_parties = len(parties)
        major_parties = {"Democratic Party", "Republican Party"}

        # Check how many major parties are present
        major_parties_present = major_parties.intersection(parties)
        num_major_parties = len(major_parties_present)

        # Calculate baseline percentages based on exact specifications
        if num_parties == 1:
            return 100.0  # Uncontested
        elif num_parties == 2:
            # 50-50 split (Democrat + Republican)
            return 50.0
        elif num_parties == 3:
            # 40-40-20 split (Democrat + Republican + Independent)
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 20.0  # Independent gets 20%
            else:
                # If not standard Dem-Rep-Ind, split evenly
                return 100.0 / 3
        elif num_parties == 4:
            # 40-40-10-10 split (Democrat + Republican + Independent + Independent)
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 10.0  # Each Independent gets 10%
            else:
                # If not standard setup, split evenly
                return 25.0
        else:
            # For 5+ parties, split evenly
            return 100.0 / num_parties


    class SpeechModal(discord.ui.Modal, title='Campaign Speech'):
        def __init__(self, target_candidate: str):
            super().__init__()
            self.target_candidate = target_candidate

        speech_text = discord.ui.TextInput(
            label='Speech Content',
            style=discord.TextStyle.long,
            placeholder='Enter your campaign speech (600-3000 characters)...',
            min_length=600,
            max_length=3000
        )

        async def on_submit(self, interaction: discord.Interaction):
            # Get the cog instance
            cog = interaction.client.get_cog('GeneralCampaignActions')

            # Process the speech
            await cog._process_speech(interaction, str(self.speech_text), self.target_candidate)

    class DonorModal(discord.ui.Modal, title='Donor Appeal'):
        def __init__(self, target_candidate: str):
            super().__init__()
            self.target_candidate = target_candidate

        donor_appeal = discord.ui.TextInput(
            label='Donor Appeal',
            style=discord.TextStyle.long,
            placeholder='Enter your fundraising appeal (400+ characters)...',
            min_length=400,
            max_length=2000
        )

        async def on_submit(self, interaction: discord.Interaction):
            # Get the cog instance
            cog = interaction.client.get_cog('GeneralCampaignActions')

            # Process the donor appeal
            await cog._process_donor(interaction, str(self.donor_appeal), self.target_candidate)

    async def _process_speech(self, interaction: discord.Interaction, speech_text: str, target_name: str):
        """Process speech submission"""
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to give speeches. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Speeches can only be given during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target_name is None:
            target_name = candidate['name']

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target_name)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (12 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "speech", 12):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "speech", 12)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before giving another speech.",
                ephemeral=True
            )
            return

        # Estimate stamina cost for speech (assuming average 1500 characters)
        estimated_stamina = 2.25  # 1500 chars = 2.25 stamina
        if target_candidate["stamina"] < estimated_stamina:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a speech! They need at least {estimated_stamina} stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Calculate polling boost - 1% per 1200 characters
        char_count = len(speech_text)
        polling_boost = (char_count / 1200) * 1.0  # 1% per 1200 characters
        polling_boost = min(polling_boost, 2.5)  # Cap at 2.5%

        # Update target candidate stats
        self._update_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                   polling_boost=polling_boost, stamina_cost=estimated_stamina)

        # Set cooldown for speaker
        self._set_cooldown(interaction.guild.id, interaction.user.id, "speech")

        # Create public speech announcement
        embed = discord.Embed(
            title="🎤 Campaign Speech",
            description=f"**{candidate['name']}** ({candidate['party']}) gives a speech supporting **{target_candidate['name']}**!",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Truncate speech for display if too long
        display_speech = speech_text
        if len(display_speech) > 1000:
            display_speech = display_speech[:997] + "..."

        embed.add_field(
            name="📜 Speech Content",
            value=display_speech,
            inline=False
        )

        embed.add_field(
            name="📊 Impact",
            value=f"**Target:** {target_candidate['name']}\n**Polling Boost:** +{polling_boost:.2f}%\n**Characters:** {char_count:,}",
            inline=True
        )

        embed.add_field(
            name="🗳️ Target Running For",
            value=f"{target_candidate['seat_id']} ({target_candidate['region']})",
            inline=True
        )

        embed.set_footer(text=f"Next speech available in 12 hours")

        # Check if interaction has already been responded to
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    async def _process_donor(self, interaction: discord.Interaction, donor_appeal: str, target_name: str):
        """Process donor appeal submission"""
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to make donor appeals. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Donor appeals can only be made during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target_name is None:
            target_name = candidate['name']

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target_name)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (24 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "donor", 24):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "donor", 24)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before making another donor appeal.",
                ephemeral=True
            )
            return

        # Estimate stamina cost for donor appeal (assuming average 1000 characters)
        estimated_stamina = 1.5  # 1000 chars = 1.5 stamina
        if target_candidate["stamina"] < estimated_stamina:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a donor appeal! They need at least {estimated_stamina} stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Calculate polling boost - 1% per 1000 characters  
        char_count = len(donor_appeal)
        polling_boost = (char_count / 1000) * 1.0
        polling_boost = min(polling_boost, 2.0)

        # Update target candidate stats
        self._update_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                   polling_boost=polling_boost, corruption_increase=5, stamina_cost=estimated_stamina)

        # Set cooldown for appealer
        self._set_cooldown(interaction.guild.id, interaction.user.id, "donor")

        embed = discord.Embed(
            title="💰 Donor Fundraising",
            description=f"**{candidate['name']}** makes a donor appeal for **{target_candidate['name']}**!",
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
            name="📊 Impact",
            value=f"**Target:** {target_candidate['name']}\n**Polling Boost:** +{polling_boost:.2f}%\n**Corruption:** +5\n**Characters:** {char_count:,}",
            inline=True
        )

        embed.add_field(
            name="⚠️ Warning",
            value="High corruption may lead to scandals!",
            inline=True
        )

        embed.set_footer(text=f"Next donor appeal available in 24 hours")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="speech",
        description="Give a campaign speech to boost polling (600-3000 characters, +1% per 1200 chars)"
    )
    @app_commands.describe(target="The candidate who will receive the speech benefits (optional)")
    async def speech(self, interaction: discord.Interaction, target: Optional[str] = None):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to give speeches. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Speeches can only be given during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate['name']

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (12 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "speech", 12):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "speech", 12)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before giving another speech.",
                ephemeral=True
            )
            return

        # Estimate stamina cost for speech (assuming average 1500 characters)
        estimated_stamina = 2.25  # 1500 chars = 2.25 stamina
        if target_candidate["stamina"] < estimated_stamina:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a speech! They need at least {estimated_stamina} stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{candidate['name']}**, please reply to this message with your campaign speech!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**Requirements:**\n"
            f"• 600-3000 characters\n"
            f"• Reply within 10 minutes\n"
            f"• +1% polling per 1200 characters (max 2.5%)\n\n"
            f"**Cost:** -2.25 stamina (estimated)",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with speech
            reply_message = await self.bot.wait_for('message', timeout=600.0, check=check)  # 10 minute timeout

            speech_text = reply_message.content

            # Check character limits
            char_count = len(speech_text)
            if char_count < 600 or char_count > 3000:
                await reply_message.reply(
                    f"❌ Speech must be 600-3000 characters. You wrote {char_count:,} characters."
                )
                return

            # Process the speech
            await self._process_speech(interaction, speech_text, target)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your speech timed out. Please use `/speech` again and reply with your speech within 10 minutes."
            )

    @app_commands.command(
        name="canvassing",
        description="Go door-to-door campaigning (100-300 characters, +0.1% polling, costs 1 stamina)"
    )
    @app_commands.describe(target="The candidate who will receive the canvassing benefits (optional)")
    async def canvassing(self, interaction: discord.Interaction, target: Optional[str] = None, canvassing_message: str = None):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to go canvassing. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Canvassing can only be done during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate['name']

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check character limits
        char_count = len(canvassing_message)
        if char_count < 100 or char_count > 300:
            await interaction.response.send_message(
                f"❌ Canvassing message must be 100-300 characters. You wrote {char_count} characters.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 1:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 1 stamina for canvassing.",
                ephemeral=True
            )
            return

        # Update target candidate stats
        self._update_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                   polling_boost=0.1, stamina_cost=1)

        embed = discord.Embed(
            title="🚪 Door-to-Door Canvassing",
            description=f"**{candidate['name']}** goes canvassing for **{target_candidate['name']}** in {target_candidate['region']}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="💬 Canvassing Message",
            value=canvassing_message,
            inline=False
        )

        embed.add_field(
            name="📊 Results",
            value=f"**Target:** {target_candidate['name']}\n**Polling Boost:** +0.1%\n**Stamina Cost:** -1",
            inline=True
        )

        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{target_candidate['stamina'] - 1}/100",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="donor",
        description="Accept donor funds (400+ characters, +1% per 1000 chars, +5 corruption, 24h cooldown)"
    )
    @app_commands.describe(target="The candidate who will receive the donor benefits (optional)")
    async def donor(self, interaction: discord.Interaction, target: Optional[str] = None):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to make donor appeals. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Donor appeals can only be made during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate['name']

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (24 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "donor", 24):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "donor", 24)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before making another donor appeal.",
                ephemeral=True
            )
            return

        # Estimate stamina cost for donor appeal (assuming average 1000 characters)
        estimated_stamina = 1.5  # 1000 chars = 1.5 stamina
        if target_candidate["stamina"] < estimated_stamina:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a donor appeal! They need at least {estimated_stamina} stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Show modal for donor appeal input
        modal = self.DonorModal(target)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="ad",
        description="Create a campaign video ad (0.3-0.6% boost, costs 1.5 stamina, 6h cooldown)"
    )
    @app_commands.describe(target="The candidate who will receive the ad benefits (optional)")
    async def ad(self, interaction: discord.Interaction, target: Optional[str] = None):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to create ads. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Campaign ads can only be created during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate['name']

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 1.5:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 1.5 stamina to create an ad.",
                ephemeral=True
            )
            return

        # Check cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "ad", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "ad", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another ad.",
                ephemeral=True
            )
            return

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{candidate['name']}**, please reply to this message with your campaign video!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 0.3-0.6% polling boost, -1.5 stamina",
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
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)  # 5 minute timeout

            video = reply_message.attachments[0]

            # Check if attachment is a video
            if not video.content_type or not video.content_type.startswith('video/'):
                await reply_message.reply(
                    "❌ Please upload a video file (MP4 format preferred)."
                )
                return

            # Check file size (Discord limit is 25MB for most servers)
            if video.size > 25 * 1024 * 1024:  # 25MB in bytes
                await reply_message.reply(
                    "❌ Video file too large! Maximum size is 25MB."
                )
                return

            # Random polling boost between 0.3% and 0.6%
            polling_boost = random.uniform(0.3, 0.6)

            # Update target candidate stats
            self._update_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                       polling_boost=polling_boost, stamina_cost=1.5)

            # Set cooldown
            self._set_cooldown(interaction.guild.id, interaction.user.id, "ad")

            embed = discord.Embed(
                title="📺 Campaign Video Ad",
                description=f"**{candidate['name']}** creates a campaign advertisement for **{target_candidate['name']}**!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 Ad Performance",
                value=f"**Target:** {target_candidate['name']}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1.5",
                inline=True
            )

            embed.add_field(
                name="📱 Reach",
                value="Broadcast across social media\nand local TV stations",
                inline=True
            )

            embed.add_field(
                name="⚡ Target's Current Stamina",
                value=f"{target_candidate['stamina'] - 1.5:.1f}/100",
                inline=True
            )

            embed.set_footer(text="Next ad available in 6 hours")

            # Reply to the user's video message with the results
            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your ad creation timed out. Please use `/ad` again and reply with your video within 5 minutes."
            )

    @app_commands.command(
        name="poster",
        description="Create a campaign poster (upload image, 0.2-0.5% boost, costs 1 stamina, 6h cooldown)"
    )
    @app_commands.describe(target="The candidate who will receive the poster benefits (optional)")
    async def poster(self, interaction: discord.Interaction, target: Optional[str] = None, image: discord.Attachment = None):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to create posters. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Campaign posters can only be created during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate['name']

        # Get target candidate
        target_signups_col, target_candidate = self._get_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 1:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 1 stamina to create a poster.",
                ephemeral=True
            )
            return

        # Check cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "poster", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "poster", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another poster.",
                ephemeral=True
            )
            return

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:  # 10MB in bytes
            await interaction.response.send_message(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Random polling boost between 0.2% and 0.5%
        polling_boost = random.uniform(0.2, 0.5)

        # Update target candidate stats
        self._update_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                   polling_boost=polling_boost, stamina_cost=1)

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "poster")

        embed = discord.Embed(
            title="🖼️ Campaign Poster",
            description=f"**{candidate['name']}** creates campaign materials for **{target_candidate['name']}** around {target_candidate['region']}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Poster Impact",
            value=f"**Target:** {target_candidate['name']}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1",
            inline=True
        )

        embed.add_field(
            name="📍 Distribution",
            value="Posted on bulletin boards,\nstreet corners, and community centers",
            inline=True
        )

        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{target_candidate['stamina'] - 1}/100",
            inline=True
        )

        # Set the image in the embed
        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 6 hours")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="polling_standings",
        description="View current polling standings for your seat"
    )
    async def polling_standings(self, interaction: discord.Interaction):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to view standings. Use `/signup` first.",
                ephemeral=True
            )
            return

        # Get current year and phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        current_phase = time_config.get("current_phase", "") if time_config else ""

        embed = discord.Embed(
            title=f"📊 Polling Standings - {candidate['seat_id']}",
            description=f"{candidate.get('office', 'Office')} • {candidate.get('region', candidate.get('state', 'Region'))} • Phase: {current_phase}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        standings = []

        if current_phase == "General Campaign":
            # Get all general election candidates for same seat
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config:
                seat_candidates = [
                    w for w in winners_config["winners"] 
                    if w["seat_id"] == candidate["seat_id"] and w["year"] == current_year and w.get("primary_winner", False)
                ]

                # Calculate current polling with baseline + campaign adjustments
                for c in seat_candidates:
                    baseline = self._calculate_baseline_percentage(interaction.guild.id, candidate["seat_id"], c["party"])
                    campaign_points = c.get("points", 0.0)

                    standings.append({
                        "name": c["candidate"],
                        "party": c["party"],
                        "baseline": baseline,
                        "campaign_points": campaign_points,
                        "stamina": c.get("stamina", 100),
                        "corruption": c.get("corruption", 0)
                    })

                # Calculate adjusted percentages maintaining 100% total
                if standings:
                    total_adjustment = sum(s["campaign_points"] for s in standings)
                    total_baseline = sum(s["baseline"] for s in standings)

                    for s in standings:
                        # Calculate adjusted percentage
                        raw_percentage = s["baseline"] + s["campaign_points"]
                        s["total"] = max(0.1, raw_percentage)  # Minimum 0.1%

                    # Normalize to 100%
                    current_total = sum(s["total"] for s in standings)
                    if current_total > 0:
                        for s in standings:
                            s["total"] = (s["total"] / current_total) * 100.0

        else:
            # Primary phase - use existing logic
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)
            if signups_config:
                seat_candidates = [
                    c for c in signups_config["candidates"] 
                    if c["seat_id"] == candidate["seat_id"] and c["year"] == current_year
                ]

                for c in seat_candidates:
                    standings.append({
                        "name": c["name"],
                        "party": c["party"],
                        "baseline": None,  # No baseline in primary
                        "campaign_points": c.get("points", 0.0),
                        "total": c.get("points", 0.0),
                        "stamina": c.get("stamina", 100),
                        "corruption": c.get("corruption", 0)
                    })

        # Sort by total percentage
        standings.sort(key=lambda x: x["total"], reverse=True)

        standings_text = ""
        for i, s in enumerate(standings, 1):
            if current_phase == "General Campaign":
                standings_text += (
                    f"**{i}. {s['name']}** ({s['party']})\n"
                    f"   └ {s['baseline']:.1f}% (baseline) + {s['campaign_points']:.1f}% (campaign) = **{s['total']:.1f}%**\n"
                    f"   └ Stamina: {s['stamina']} • Corruption: {s['corruption']}\n\n"
                )
            else:
                standings_text += (
                    f"**{i}. {s['name']}** ({s['party']})\n"
                    f"   └ Campaign Points: **{s['total']:.1f}**\n"
                    f"   └ Stamina: {s['stamina']} • Corruption: {s['corruption']}\n\n"
                )

        embed.add_field(
            name="🏆 Current Standings",
            value=standings_text,
            inline=False
        )

        if current_phase == "General Campaign":
            embed.add_field(
                name="ℹ️ General Election Info",
                value="Baseline percentages determined by party distribution. Campaign points adjust these percentages while maintaining 100% total.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="campaign_status",
        description="View your campaign statistics and available actions"
    )
    async def campaign_status(self, interaction: discord.Interaction):
        # Check if user is a candidate
        signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered candidate to view campaign status. Use `/signup` first.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Campaign Status",
            description=f"**{candidate['name']}** ({candidate['party']})",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🗳️ Campaign Info",
            value=f"**Running For:** {candidate['seat_id']}\n"
                  f"**Region:** {candidate['region']}\n"
                  f"**Office:** {candidate['office']}",
            inline=True
        )

        baseline = candidate.get("baseline_percentage", 50.0)
        total_percentage = baseline + candidate['points']

        embed.add_field(
            name="📈 Current Stats",
            value=f"**Baseline:** {baseline:.1f}%\n"
                  f"**Campaign Points:** +{candidate['points']:.2f}%\n"
                  f"**Total Polling:** {total_percentage:.1f}%\n"
                  f"**Stamina:** {candidate['stamina']}/100\n"
                  f"**Corruption:** {candidate['corruption']}",
            inline=True
        )

        # Check cooldowns for all actions
        cooldown_info = ""
        actions = [
            ("speech", 12),
            ("donor", 24),
            ("ad", 6),
            ("poster", 6)
        ]

        for action, hours in actions:
            if self._check_cooldown(interaction.guild.id, interaction.user.id, action, hours):
                cooldown_info += f"✅ **{action.title()}:** Available\n"
            else:
                remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, action, hours)
                hours_left = int(remaining.total_seconds() // 3600)
                minutes_left = int((remaining.total_seconds() % 3600) // 60)
                cooldown_info += f"⏰ **{action.title()}:** {hours_left}h {minutes_left}m\n"

        # Canvassing has no cooldown, just note it's available
        cooldown_info += "✅ **Canvassing:** Always available\n"

        embed.add_field(
            name="⏱️ Action Availability",
            value=cooldown_info,
            inline=False
        )

        # Add tips for improving campaign
        tips = []
        if candidate['stamina'] < 50:
            tips.append("• Consider resting to restore stamina")
        if candidate['corruption'] > 20:
            tips.append("• High corruption may lead to scandals")
        if candidate['points'] < 5:
            tips.append("• Use speech and donor commands for the biggest polling boost")

        if tips:
            embed.add_field(
                name="💡 Campaign Tips",
                value="\n".join(tips),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="reset_cooldowns",
        description="Reset action cooldowns for a specific user"
    )
    @app_commands.describe(
        user="The user whose cooldowns to reset",
        action="Specific action to reset (optional - leave blank to reset all)"
    )
    async def reset_cooldowns(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        action: Optional[str] = None
    ):
        cooldowns_col = self.bot.db["action_cooldowns"]

        if action:
            # Reset specific action cooldown
            valid_actions = ["speech", "donor", "ad", "poster"]
            if action.lower() not in valid_actions:
                await interaction.response.send_message(
                    f"❌ Invalid action. Valid actions: {', '.join(valid_actions)}",
                    ephemeral=True
                )
                return

            result = cooldowns_col.delete_many({
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "action_type": action.lower()
            })

            await interaction.response.send_message(
                f"✅ Reset **{action}** cooldown for {user.mention}. ({result.deleted_count} records cleared)",
                ephemeral=True
            )
        else:
            # Reset all cooldowns for user
            result = cooldowns_col.delete_many({
                "guild_id": interaction.guild.id,
                "user_id": user.id
            })

            await interaction.response.send_message(
                f"✅ Reset **all** cooldowns for {user.mention}. ({result.deleted_count} records cleared)",
                ephemeral=True
            )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="reset_command_timer",
        description="Reset specific command cooldown for a user (alias for reset_cooldowns)"
    )
    @app_commands.describe(
        user="The user whose cooldown to reset",
        command="Command to reset (speech, donor, ad, poster, or 'all')"
    )
    async def reset_command_timer(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        command: str
    ):
        cooldowns_col = self.bot.db["action_cooldowns"]

        if command.lower() == "all":
            # Reset all cooldowns for user
            result = cooldowns_col.delete_many({
                "guild_id": interaction.guild.id,
                "user_id": user.id
            })

            await interaction.response.send_message(
                f"✅ Reset **all** command timers for {user.mention}. ({result.deleted_count} records cleared)",
                ephemeral=True
            )
        else:
            # Reset specific command cooldown
            valid_commands = ["speech", "donor", "ad", "poster"]
            if command.lower() not in valid_commands:
                await interaction.response.send_message(
                    f"❌ Invalid command. Valid commands: {', '.join(valid_commands)}, all",
                    ephemeral=True
                )
                return

            result = cooldowns_col.delete_many({
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "action_type": command.lower()
            })

            await interaction.response.send_message(
                f"✅ Reset **{command}** timer for {user.mention}. ({result.deleted_count} records cleared)",
                ephemeral=True
            )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="reset_all_cooldowns",
        description="Reset ALL action cooldowns for everyone in the server"
    )
    @app_commands.describe(confirm="Type 'yes' to confirm this action")
    async def reset_all_cooldowns(
        self, 
        interaction: discord.Interaction, 
        confirm: str
    ):
        if confirm.lower() != "yes":
            await interaction.response.send_message(
                "❌ You must type 'yes' to confirm resetting all cooldowns.",
                ephemeral=True
            )
            return

        cooldowns_col = self.bot.db["action_cooldowns"]
        result = cooldowns_col.delete_many({"guild_id": interaction.guild.id})

        await interaction.response.send_message(
            f"✅ Reset **ALL** cooldowns for everyone in the server. ({result.deleted_count} records cleared)",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(GeneralCampaignActions(bot))