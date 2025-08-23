import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, List
from .presidential_winners import PRESIDENTIAL_STATE_DATA

class PresCampaignActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Presidential Campaign Actions cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_config(self, guild_id: int):
        """Get presidential signups configuration"""
        col = self.bot.db["presidential_signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_winners_config(self, guild_id: int):
        """Get presidential winners configuration"""
        col = self.bot.db["presidential_winners"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_presidential_candidate(self, guild_id: int, user_id: int):
        """Get user's presidential candidate information"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in presidential winners collection for general campaign
            winners_col, winners_config = self._get_presidential_winners_config(guild_id)
            
            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config.get("winners", []):
                if (winner["user_id"] == user_id and 
                    winner.get("primary_winner", False) and 
                    winner["year"] == primary_year and
                    winner["office"] in ["President", "Vice President"]):
                    return winners_col, winner

            return winners_col, None
        else:
            # Look in presidential signups collection for primary campaign
            signups_col, signups_config = self._get_presidential_config(guild_id)

            if not signups_config:
                return None, None

            for candidate in signups_config.get("candidates", []):
                if (candidate["user_id"] == user_id and 
                    candidate["year"] == current_year and
                    candidate["office"] in ["President", "Vice President"]):
                    return signups_col, candidate

            return signups_col, None

    def _get_presidential_candidate_by_name(self, guild_id: int, candidate_name: str):
        """Get presidential candidate by name"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        if current_phase == "General Campaign":
            # Look in presidential winners collection for general campaign
            winners_col, winners_config = self._get_presidential_winners_config(guild_id)

            if not winners_config:
                return None, None

            # For general campaign, look for primary winners from the previous year if we're in an even year
            # Or current year if odd year
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year

            for winner in winners_config.get("winners", []):
                if (winner["name"].lower() == candidate_name.lower() and 
                    winner.get("primary_winner", False) and
                    winner["year"] == primary_year and
                    winner["office"] in ["President", "Vice President"]):
                    return winners_col, winner

            return winners_col, None
        else:
            # Look in presidential signups collection for primary campaign
            signups_col, signups_config = self._get_presidential_config(guild_id)

            if not signups_config:
                return None, None

            for candidate in signups_config.get("candidates", []):
                if (candidate["name"].lower() == candidate_name.lower() and 
                    candidate["year"] == current_year and
                    candidate["office"] in ["President", "Vice President"]):
                    return signups_col, candidate

            return signups_col, None

    def _update_presidential_candidate_stats(self, collection, guild_id: int, user_id: int, 
                                           state_name: str, polling_boost: float = 0, 
                                           stamina_cost: int = 0, corruption_increase: int = 0):
        """Update presidential candidate's polling, stamina, and corruption"""
        time_col, time_config = self._get_time_config(guild_id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        if current_phase == "General Campaign":
            # For general campaign, update in presidential winners collection
            collection.update_one(
                {"guild_id": guild_id, "winners.user_id": user_id},
                {
                    "$inc": {
                        f"winners.$.state_points.{state_name.upper()}": polling_boost,
                        "winners.$.stamina": -stamina_cost,
                        "winners.$.corruption": corruption_increase,
                        "winners.$.total_points": polling_boost
                    }
                }
            )
        else:
            # For primary campaign, update in presidential signups collection
            collection.update_one(
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
        cooldowns_col = self.bot.db["pres_action_cooldowns"]
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
        cooldowns_col = self.bot.db["pres_action_cooldowns"]
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
        cooldowns_col = self.bot.db["pres_action_cooldowns"]
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

    def _apply_buff_debuff_multiplier(self, base_value: float, user_id: int, guild_id: int, action_type: str) -> float:
        """Apply buff/debuff multipliers to a base value"""
        # Placeholder for buff/debuff logic. In a real scenario, you'd fetch user-specific buffs/debuffs
        # and apply them to the base_value.
        # For now, we'll use a simplified approach or return the base value.
        # Example: If user has a "Strong Speech" buff, multiplier might be 1.2
        # If user has a "Tired" debuff, multiplier might be 0.8
        
        # Fetch user's active buffs/debuffs from a database or cache
        # For demonstration, let's assume a simple lookup
        
        buffs_debuffs_col = self.bot.db["buffs_debuffs"]
        user_effects = buffs_debuffs_col.find_one({"guild_id": guild_id, "user_id": user_id})
        
        multiplier = 1.0
        
        if user_effects:
            # Example: Check for specific buffs/debuffs related to campaign actions
            # This part would need to be more robust and tailored to your game's mechanics
            if action_type == "pres_speech":
                if "eloquent_speaker" in user_effects.get("active_buffs", []):
                    multiplier *= 1.2  # 20% boost for speeches
                if "stage_fright" in user_effects.get("active_debuffs", []):
                    multiplier *= 0.8  # 20% reduction for speeches
            elif action_type == "pres_donor":
                if "generous_appeal" in user_effects.get("active_buffs", []):
                    multiplier *= 1.15 # 15% boost for donor appeals
            elif action_type == "pres_canvassing":
                if "neighborhood_expert" in user_effects.get("active_buffs", []):
                    multiplier *= 1.1 # 10% boost for canvassing
            elif action_type == "pres_ad":
                if "viral_marketing" in user_effects.get("active_buffs", []):
                    multiplier *= 1.15 # 15% boost for ads
            elif action_type == "pres_poster":
                if "eye_catching_design" in user_effects.get("active_buffs", []):
                    multiplier *= 1.1 # 10% boost for posters

        return base_value * multiplier

    def _calculate_general_election_percentages(self, guild_id: int, office: str):
        """Calculate general election percentages using state-based distribution"""
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Get presidential winners (general election candidates)
        winners_col, winners_config = self._get_presidential_winners_config(guild_id)

        if not winners_config:
            return {}

        # For general campaign, look for primary winners from the previous year if we're in an even year
        # Or current year if odd year
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        candidates = [
            w for w in winners_config.get("winners", []) 
            if w.get("primary_winner", False) and w["year"] == primary_year and w["office"] == office
        ]

        if not candidates:
            return {}

        # Initialize final percentages
        final_percentages = {}
        
        # For each candidate, calculate their total based on state performance
        for candidate in candidates:
            candidate_name = candidate["name"]
            state_points = candidate.get("state_points", {})
            total_percentage = 0.0

            # Calculate weighted percentage based on state data and campaign points
            for state_name, state_data in PRESIDENTIAL_STATE_DATA.items():
                # Get candidate's campaign points in this state
                campaign_points = state_points.get(state_name, 0.0)
                
                # Determine party alignment bonus
                party_bonus = 0.0
                candidate_party = candidate["party"].lower()
                if "democrat" in candidate_party or "democratic" in candidate_party:
                    party_bonus = state_data["democrat"] / 100.0
                elif "republican" in candidate_party:
                    party_bonus = state_data["republican"] / 100.0
                else:
                    party_bonus = state_data["other"] / 100.0

                # Each state contributes equally (1/50th of total)
                state_weight = 1.0 / len(PRESIDENTIAL_STATE_DATA)
                
                # Base percentage from party alignment + campaign point bonus
                state_contribution = (party_bonus + (campaign_points * 0.01)) * state_weight
                total_percentage += state_contribution

            final_percentages[candidate_name] = max(0.01, total_percentage * 100)

        # Normalize to 100%
        total = sum(final_percentages.values())
        if total > 0:
            for name in final_percentages:
                final_percentages[name] = (final_percentages[name] / total) * 100.0

        return final_percentages

    class PresidentialSpeechModal(discord.ui.Modal, title='Presidential Campaign Speech'):
        def __init__(self, target_candidate: str, state_name: str):
            super().__init__()
            self.target_candidate = target_candidate
            self.state_name = state_name

        speech_text = discord.ui.TextInput(
            label='Speech Content',
            style=discord.TextStyle.long,
            placeholder='Enter your presidential campaign speech (600-3000 characters)...',
            min_length=600,
            max_length=3000
        )

        async def on_submit(self, interaction: discord.Interaction):
            # Get the cog instance
            cog = interaction.client.get_cog('PresCampaignActions')

            # Process the speech
            await cog._process_pres_speech(interaction, str(self.speech_text), self.target_candidate, self.state_name)

    class PresidentialDonorModal(discord.ui.Modal, title='Presidential Donor Appeal'):
        def __init__(self, target_candidate: str, state_name: str):
            super().__init__()
            self.target_candidate = target_candidate
            self.state_name = state_name

        donor_appeal = discord.ui.TextInput(
            label='Donor Appeal',
            style=discord.TextStyle.long,
            placeholder='Enter your presidential fundraising appeal (400+ characters)...',
            min_length=400,
            max_length=2000
        )

        async def on_submit(self, interaction: discord.Interaction):
            # Get the cog instance
            cog = interaction.client.get_cog('PresCampaignActions')

            # Process the donor appeal
            await cog._process_pres_donor(interaction, str(self.donor_appeal), self.target_candidate, self.state_name)

    async def _process_pres_speech(self, interaction: discord.Interaction, speech_text: str, target_name: str, state_name: str):
        """Process presidential speech submission"""
        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to give speeches. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential speeches can only be given during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target_name is None:
            target_name = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target_name)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Estimate stamina cost
        estimated_stamina = 2.25
        if target_candidate["stamina"] < estimated_stamina:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a speech! They need at least {estimated_stamina} stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Calculate polling boost - 1% per 1200 characters
        char_count = len(speech_text)
        polling_boost = (char_count / 1200) * 1.0
        polling_boost = min(polling_boost, 2.5)

        # Apply buff/debuff multipliers
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, target_candidate["user_id"], interaction.guild.id, "pres_speech")

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_name, polling_boost=polling_boost, stamina_cost=estimated_stamina)

        # Create public speech announcement
        embed = discord.Embed(
            title="🎤 Presidential Campaign Speech",
            description=f"**{candidate['name']}** ({candidate['party']}) gives a speech supporting **{target_candidate['name']}** in {state_name}!",
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

        # For general campaign, show updated percentages
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "")
        
        if current_phase == "General Campaign":
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
            
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_name}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Characters:** {char_count:,}",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_name}\n**Polling Boost:** +{polling_boost:.2f}%\n**Characters:** {char_count:,}",
                inline=True
            )

        embed.set_footer(text=f"Next speech available in 12 hours")

        # Check if interaction has already been responded to
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    async def _process_pres_donor(self, interaction: discord.Interaction, donor_appeal: str, target_name: str, state_name: str):
        """Process presidential donor appeal submission"""
        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to make donor appeals. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Calculate polling boost - 1% per 1000 characters  
        char_count = len(donor_appeal)
        polling_boost = (char_count / 1000) * 1.0
        polling_boost = min(polling_boost, 2.0)

        # Apply buff/debuff multipliers
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, candidate["user_id"], interaction.guild.id, "pres_donor")

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target_name)
        if not target_candidate: # Ensure target_candidate is not None before accessing its attributes
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_name, polling_boost=polling_boost, corruption_increase=5, stamina_cost=1.5)

        embed = discord.Embed(
            title="💰 Presidential Donor Fundraising",
            description=f"**{candidate['name']}** makes a donor appeal for **{target_candidate['name']}** in {state_name}!",
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

        # For general campaign, show updated percentages
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "")
        
        if current_phase == "General Campaign":
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
            
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_name}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Corruption:** +5\n**Characters:** {char_count:,}",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_name}\n**Polling Boost:** +{polling_boost:.2f}%\n**Corruption:** +5\n**Characters:** {char_count:,}",
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
        name="pres_canvassing",
        description="Presidential door-to-door campaigning in a U.S. state (0.1% points, 1 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for campaigning",
        target="The presidential candidate who will receive benefits (optional)",
        canvassing_message="Your canvassing message (100-300 characters)"
    )
    async def pres_canvassing(
        self, 
        interaction: discord.Interaction, 
        state: str,
        canvassing_message: str,
        target: Optional[str] = None
    ):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to go canvassing. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential canvassing can only be done during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
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

        # Apply buff/debuff multipliers to canvassing points
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(0.1, target_candidate["user_id"], interaction.guild.id, "pres_canvassing")

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_upper, polling_boost=polling_boost, stamina_cost=1)

        embed = discord.Embed(
            title="🚪 Presidential Door-to-Door Canvassing",
            description=f"**{candidate['name']}** goes canvassing for **{target_candidate['name']}** in {state_upper}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="💬 Canvassing Message",
            value=canvassing_message,
            inline=False
        )

        # For general campaign, show updated percentages
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "")
        
        if current_phase == "General Campaign":
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
            
            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1",
                inline=True
            )

        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{target_candidate['stamina'] - 1}/200",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pres_donor",
        description="Presidential donor meeting in a U.S. state (1000 characters = 1% points, 5 corruption)"
    )
    @app_commands.describe(
        state="U.S. state for donor meeting",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def pres_donor(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to make donor appeals. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential donor appeals can only be made during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (24 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_donor", 24):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_donor", 24)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before making another presidential donor appeal.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 1.5:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a donor appeal! They need at least 1.5 stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_donor")

        # Show modal for donor appeal input
        modal = self.PresidentialDonorModal(target, state_upper)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="pres_ad",
        description="Presidential campaign video ad in a U.S. state (0.3-0.5% points, 1.5 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for video ad",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def pres_ad(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to create ads. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential campaign ads can only be created during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
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
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_ad", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_ad", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another presidential ad.",
                ephemeral=True
            )
            return

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{candidate['name']}**, please reply to this message with your presidential campaign video!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 0.3-0.5% polling boost, -1.5 stamina",
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

            # Random polling boost between 0.3% and 0.5%
            polling_boost = random.uniform(0.3, 0.5)

            # Apply buff/debuff multipliers
            polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, target_candidate["user_id"], interaction.guild.id, "pres_ad")

            # Update target candidate stats
            self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                     state_upper, polling_boost=polling_boost, stamina_cost=1.5)

            # Set cooldown
            self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_ad")

            embed = discord.Embed(
                title="📺 Presidential Campaign Video Ad",
                description=f"**{candidate['name']}** creates a campaign advertisement for **{target_candidate['name']}** in {state_upper}!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            # For general campaign, show updated percentages
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "")
            
            if current_phase == "General Campaign":
                general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
                updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
                
                embed.add_field(
                    name="📊 Ad Performance",
                    value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1.5",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📊 Ad Performance",
                    value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1.5",
                    inline=True
                )

            embed.add_field(
                name="📱 Reach",
                value=f"Broadcast across {state_upper}\nsocial media and local TV",
                inline=True
            )

            embed.add_field(
                name="⚡ Target's Current Stamina",
                value=f"{target_candidate['stamina'] - 1.5:.1f}/200",
                inline=True
            )

            embed.set_footer(text="Next ad available in 6 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your ad creation timed out. Please use `/pres_ad` again and reply with your video within 5 minutes."
            )

    @app_commands.command(
        name="pres_poster",
        description="Presidential campaign poster in a U.S. state (0.2-0.4% points, 1 stamina)"
    )
    @app_commands.describe(
        state="U.S. state for campaign poster",
        target="The presidential candidate who will receive benefits (optional)",
        image="Upload your campaign poster image"
    )
    async def pres_poster(
        self, 
        interaction: discord.Interaction, 
        state: str,
        image: discord.Attachment,
        target: Optional[str] = None
    ):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to create posters. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential campaign posters can only be created during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
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
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_poster", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_poster", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before creating another presidential poster.",
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
        if image.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Random polling boost between 0.2% and 0.4%
        polling_boost = random.uniform(0.2, 0.4)

        # Apply buff/debuff multipliers
        polling_boost = self._apply_buff_debuff_multiplier_enhanced(polling_boost, target_candidate["user_id"], interaction.guild.id, "pres_poster")

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_upper, polling_boost=polling_boost, stamina_cost=1)

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_poster")

        embed = discord.Embed(
            title="🖼️ Presidential Campaign Poster",
            description=f"**{candidate['name']}** creates campaign materials for **{target_candidate['name']}** in {state_upper}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # For general campaign, show updated percentages
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "")
        
        if current_phase == "General Campaign":
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
            
            embed.add_field(
                name="📊 Poster Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Poster Impact",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1",
                inline=True
            )

        embed.add_field(
            name="📍 Distribution",
            value=f"Posted throughout {state_upper}\nat community centers and events",
            inline=True
        )

        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{target_candidate['stamina'] - 1}/200",
            inline=True
        )

        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 6 hours")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pres_speech",
        description="Give a presidential campaign speech in a U.S. state (600-3000 characters, +1% per 1200 chars)"
    )
    @app_commands.describe(
        state="U.S. state for campaign speech",
        target="The presidential candidate who will receive benefits (optional)"
    )
    async def pres_speech(self, interaction: discord.Interaction, state: str, target: Optional[str] = None):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to give speeches. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check if in campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config["current_phase"] not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential speeches can only be given during campaign phases.",
                ephemeral=True
            )
            return

        # If no target specified, default to self
        if target is None:
            target = candidate["name"]

        # Verify target candidate exists
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check cooldown (12 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_speech", 12):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_speech", 12)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"❌ You must wait {hours}h {minutes}m before giving another presidential speech.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate["stamina"] < 2.25:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a speech! They need at least 2.25 stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_speech")

        # Show modal for speech input
        modal = self.PresidentialSpeechModal(target, state_upper)
        await interaction.response.send_modal(modal)

    # State autocomplete for all commands
    @pres_canvassing.autocomplete("state")
    async def state_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @pres_donor.autocomplete("state")
    async def state_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @pres_ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @pres_poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @pres_speech.autocomplete("state")
    async def state_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @app_commands.command(
        name="pres_polling",
        description="Conduct NPC presidential poll for a U.S. state (party support with 7% margin of error)"
    )
    @app_commands.describe(state="U.S. state to poll for presidential support")
    async def pres_polling(self, interaction: discord.Interaction, state: str):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Get base party percentages from PRESIDENTIAL_STATE_DATA
        state_data = PRESIDENTIAL_STATE_DATA[state_upper]
        republican_base = state_data["republican"]
        democrat_base = state_data["democrat"] 
        independent_base = state_data["other"]

        # Apply 7% margin of error to each party
        def calculate_poll_result(actual_percentage: float, margin_of_error: float = 7.0) -> float:
            variation = random.uniform(-margin_of_error, margin_of_error)
            poll_result = actual_percentage + variation
            return max(0.1, min(99.9, poll_result))

        poll_results = {
            "Republican": calculate_poll_result(republican_base),
            "Democrat": calculate_poll_result(democrat_base),
            "Independent": calculate_poll_result(independent_base)
        }

        # Sort results for display
        sorted_results = sorted(poll_results.items(), key=lambda item: item[1], reverse=True)

        # Generate polling details
        polling_orgs = [
            "Presidential Polling Institute", "State Political Research", "National Election Survey",
            "Presidential Analytics Group", "Democracy Polling Center", "Election Forecast Network"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(1000, 2500)
        days_ago = random.randint(1, 5)

        embed = discord.Embed(
            title=f"📊 Presidential Polling: {state_upper}",
            description=f"**Presidential Party Support** • {current_phase} ({current_year})",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Create visual progress bar function
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        # Add poll results with party colors
        results_text = ""
        party_colors = {"Republican": "🔴", "Democrat": "🔵", "Independent": "🟣"}
        
        for party, poll_percentage in sorted_results:
            color_emoji = party_colors.get(party, "⚪")
            progress_bar = create_progress_bar(poll_percentage)
            
            results_text += f"{color_emoji} **{party}**\n"
            results_text += f"{progress_bar} **{poll_percentage:.1f}%**\n\n"

        embed.add_field(
            name="🗳️ Presidential Support",
            value=results_text,
            inline=False
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±7.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated presidential poll with a ±7% margin of error based on state political leanings.",
            inline=False
        )

        embed.set_footer(text=f"Presidential poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @pres_polling.autocomplete("state")
    async def state_autocomplete_polling(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
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
        name="admin_campaign_buff",
        description="Apply a temporary buff to a candidate's campaign actions (Admin only)"
    )
    @app_commands.describe(
        target="The user to buff",
        effect_name="Name of the buff effect",
        multiplier="Multiplier for campaign points (e.g., 1.5 for +50%)",
        duration_hours="Duration in hours",
        action_types="Comma-separated action types to affect (empty = all actions)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_campaign_buff(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        effect_name: str,
        multiplier: float,
        duration_hours: int,
        action_types: str = ""
    ):
        if multiplier <= 0:
            await interaction.response.send_message(
                "❌ Multiplier must be greater than 0.",
                ephemeral=True
            )
            return

        if duration_hours <= 0 or duration_hours > 168:  # Max 1 week
            await interaction.response.send_message(
                "❌ Duration must be between 1-168 hours (1 week max).",
                ephemeral=True
            )
            return

        buffs_col, buffs_config = self._get_buffs_debuffs_config(interaction.guild.id)

        # Parse action types
        parsed_action_types = []
        if action_types.strip():
            parsed_action_types = [action.strip() for action in action_types.split(",")]

        effect_id = f"{target.id}_{effect_name}_{datetime.utcnow().timestamp()}"
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

        effect = {
            "effect_type": "buff",
            "target_user_id": target.id,
            "effect_name": effect_name,
            "multiplier": multiplier,
            "expires_at": expires_at,
            "action_types": parsed_action_types,
            "applied_by": interaction.user.id,
            "applied_at": datetime.utcnow()
        }

        buffs_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"active_effects.{effect_id}": effect}},
            upsert=True
        )

        # Create announcement embed
        embed = discord.Embed(
            title="✨ Campaign Buff Applied",
            description=f"**{effect_name}** has been applied to {target.mention}!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Effect Details",
            value=f"**Multiplier:** {multiplier:.1f}x ({(multiplier-1)*100:+.0f}%)\n"
                  f"**Duration:** {duration_hours} hours\n"
                  f"**Expires:** <t:{int(expires_at.timestamp())}:R>",
            inline=True
        )

        if parsed_action_types:
            embed.add_field(
                name="🎯 Affected Actions",
                value=", ".join(parsed_action_types),
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 Affected Actions",
                value="All campaign actions",
                inline=True
            )

        embed.add_field(
            name="👤 Applied By",
            value=interaction.user.mention,
            inline=True
        )

        # Public announcement
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_campaign_debuff",
        description="Apply a temporary debuff to a candidate's campaign actions (Admin only)"
    )
    @app_commands.describe(
        target="The user to debuff",
        effect_name="Name of the debuff effect",
        multiplier="Multiplier for campaign points (e.g., 0.5 for -50%)",
        duration_hours="Duration in hours",
        action_types="Comma-separated action types to affect (empty = all actions)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_campaign_debuff(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        effect_name: str,
        multiplier: float,
        duration_hours: int,
        action_types: str = ""
    ):
        if multiplier <= 0 or multiplier >= 1.0:
            await interaction.response.send_message(
                "❌ Debuff multiplier must be between 0 and 1.0.",
                ephemeral=True
            )
            return

        if duration_hours <= 0 or duration_hours > 168:  # Max 1 week
            await interaction.response.send_message(
                "❌ Duration must be between 1-168 hours (1 week max).",
                ephemeral=True
            )
            return

        buffs_col, buffs_config = self._get_buffs_debuffs_config(interaction.guild.id)

        # Parse action types
        parsed_action_types = []
        if action_types.strip():
            parsed_action_types = [action.strip() for action in action_types.split(",")]

        effect_id = f"{target.id}_{effect_name}_{datetime.utcnow().timestamp()}"
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

        effect = {
            "effect_type": "debuff",
            "target_user_id": target.id,
            "effect_name": effect_name,
            "multiplier": multiplier,
            "expires_at": expires_at,
            "action_types": parsed_action_types,
            "applied_by": interaction.user.id,
            "applied_at": datetime.utcnow()
        }

        buffs_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"active_effects.{effect_id}": effect}},
            upsert=True
        )

        # Create announcement embed
        embed = discord.Embed(
            title="💀 Campaign Debuff Applied",
            description=f"**{effect_name}** has been applied to {target.mention}!",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Effect Details",
            value=f"**Multiplier:** {multiplier:.1f}x ({(multiplier-1)*100:+.0f}%)\n"
                  f"**Duration:** {duration_hours} hours\n"
                  f"**Expires:** <t:{int(expires_at.timestamp())}:R>",
            inline=True
        )

        if parsed_action_types:
            embed.add_field(
                name="🎯 Affected Actions",
                value=", ".join(parsed_action_types),
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 Affected Actions",
                value="All campaign actions",
                inline=True
            )

        embed.add_field(
            name="👤 Applied By",
            value=interaction.user.mention,
            inline=True
        )

        # Public announcement
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_remove_campaign_effect",
        description="Remove a specific campaign buff or debuff (Admin only)"
    )
    @app_commands.describe(
        target="The user whose effects to remove",
        effect_name="Name of the effect to remove (empty = remove all effects for user)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_campaign_effect(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        effect_name: str = ""
    ):
        buffs_col, buffs_config = self._get_buffs_debuffs_config(interaction.guild.id)

        active_effects = buffs_config.get("active_effects", {})
        effects_to_remove = []

        for effect_id, effect in active_effects.items():
            if effect.get("target_user_id") == target.id:
                if not effect_name or effect.get("effect_name") == effect_name:
                    effects_to_remove.append(effect_id)

        if not effects_to_remove:
            await interaction.response.send_message(
                f"❌ No matching effects found for {target.mention}.",
                ephemeral=True
            )
            return

        # Remove effects
        for effect_id in effects_to_remove:
            buffs_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$unset": {f"active_effects.{effect_id}": ""}}
            )

        effect_word = "effect" if len(effects_to_remove) == 1 else "effects"
        await interaction.response.send_message(
            f"✅ Removed {len(effects_to_remove)} {effect_word} from {target.mention}.",
            ephemeral=True
        )

    @app_commands.command(
        name="view_campaign_effects",
        description="View all active campaign buffs and debuffs"
    )
    async def view_campaign_effects(self, interaction: discord.Interaction):
        buffs_col, buffs_config = self._get_buffs_debuffs_config(interaction.guild.id)

        active_effects = buffs_config.get("active_effects", {})
        current_time = datetime.utcnow()

        # Filter out expired effects
        valid_effects = {}
        for effect_id, effect in active_effects.items():
            if effect.get("expires_at", current_time) > current_time:
                valid_effects[effect_id] = effect

        if not valid_effects:
            await interaction.response.send_message(
                "📋 No active campaign effects currently.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎭 Active Campaign Effects",
            description="Current buffs and debuffs affecting candidates",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        buffs_text = ""
        debuffs_text = ""

        for effect_id, effect in valid_effects.items():
            target_user = interaction.guild.get_member(effect.get("target_user_id"))
            target_name = target_user.display_name if target_user else "Unknown User"

            effect_info = (f"**{effect.get('effect_name')}**\n"
                          f"└ Target: {target_name}\n"
                          f"└ Multiplier: {effect.get('multiplier', 1.0):.1f}x\n"
                          f"└ Expires: <t:{int(effect.get('expires_at').timestamp())}:R>\n\n")

            if effect.get("effect_type") == "buff":
                buffs_text += effect_info
            else:
                debuffs_text += effect_info

        if buffs_text:
            embed.add_field(
                name="✨ Active Buffs",
                value=buffs_text,
                inline=False
            )

        if debuffs_text:
            embed.add_field(
                name="💀 Active Debuffs",
                value=debuffs_text,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_add_pres_points",
        description="Directly add campaign points to a presidential candidate (Admin only)"
    )
    @app_commands.describe(
        candidate_name="Name of the presidential candidate",
        state="State to add points to (for General Campaign)",
        points="Points to add (can be negative to subtract)",
        reason="Reason for the point adjustment"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_add_pres_points(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        points: float,
        state: str = None,
        reason: str = "Admin adjustment"
    ):
        # Get target candidate
        target_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, candidate_name)
        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Presidential candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Check current phase to determine how to add points
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        if current_phase == "General Campaign":
            if not state:
                await interaction.response.send_message(
                    "❌ State parameter is required for General Campaign point additions.",
                    ephemeral=True
                )
                return

            state_upper = state.upper()
            if state_upper not in PRESIDENTIAL_STATE_DATA:
                await interaction.response.send_message(
                    f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                    ephemeral=True
                )
                return

            # Update state points and total points
            target_col.update_one(
                {"guild_id": interaction.guild.id, "winners.user_id": target_candidate["user_id"]},
                {
                    "$inc": {
                        f"winners.$.state_points.{state_upper}": points,
                        "winners.$.total_points": points
                    }
                }
            )

            # Calculate new percentages
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)

            embed = discord.Embed(
                title="⚙️ Presidential Points Added",
                description=f"Admin point adjustment for **{target_candidate['name']}**",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 General Campaign Adjustment",
                value=f"**Candidate:** {target_candidate['name']}\n"
                      f"**State:** {state_upper}\n"
                      f"**Points Added:** {points:+.2f}\n"
                      f"**New National Polling:** {updated_percentage:.1f}%\n"
                      f"**Reason:** {reason}",
                inline=False
            )

        else:
            # Primary campaign - add to general points
            target_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate["user_id"]},
                {"$inc": {"candidates.$.points": points}}
            )

            new_points = target_candidate.get("points", 0) + points

            embed = discord.Embed(
                title="⚙️ Presidential Points Added",
                description=f"Admin point adjustment for **{target_candidate['name']}**",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 Primary Campaign Adjustment",
                value=f"**Candidate:** {target_candidate['name']}\n"
                      f"**Points Added:** {points:+.2f}%\n"
                      f"**New Total:** {new_points:.2f}%\n"
                      f"**Reason:** {reason}",
                inline=False
            )

        embed.add_field(
            name="👤 Applied By",
            value=interaction.user.mention,
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_add_general_points",
        description="Directly add campaign points to a general election candidate (Admin only)"
    )
    @app_commands.describe(
        candidate_name="Name of the candidate",
        office="Office the candidate is running for",
        points="Points to add (can be negative to subtract)",
        reason="Reason for the point adjustment"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_add_general_points(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        office: str,
        points: float,
        reason: str = "Admin adjustment"
    ):
        # Get winners configuration
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        if not winners_config:
            await interaction.response.send_message(
                "❌ No general election configuration found.",
                ephemeral=True
            )
            return

        # Find the candidate
        candidate_found = None
        candidate_index = None
        
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        for idx, candidate in enumerate(winners_config.get("winners", [])):
            if (candidate["name"].lower() == candidate_name.lower() and 
                candidate["office"].lower() == office.lower() and
                candidate.get("primary_winner", False)): # Check if this candidate won the primary
                candidate_found = candidate
                candidate_index = idx
                break

        if not candidate_found:
            await interaction.response.send_message(
                f"❌ General election candidate '{candidate_name}' for '{office}' not found or did not win primary.",
                ephemeral=True
            )
            return

        # Update candidate points
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$inc": {
                    f"winners.{candidate_index}.points": points
                }
            }
        )

        # Calculate new polling percentage for this candidate
        # Note: _calculate_zero_sum_percentages is not defined in this cog.
        # Assuming this is meant to be a placeholder or needs to be implemented.
        # For now, we'll use a placeholder value.
        updated_percentage = 50.0 # Placeholder

        embed = discord.Embed(
            title="⚙️ General Election Points Added",
            description=f"Admin point adjustment for **{candidate_name}**",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 General Election Adjustment",
            value=f"**Candidate:** {candidate_name}\n"
                  f"**Office:** {office}\n"
                  f"**Seat:** {candidate_found.get('seat_id', 'N/A')}\n" # Use .get for safety
                  f"**Points Added:** {points:+.2f}\n"
                  f"**Updated Polling:** {updated_percentage:.1f}%\n"
                  f"**Reason:** {reason}",
            inline=False
        )

        embed.set_footer(text=f"Adjusted by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _get_winners_config(self, guild_id: int):
        """Get general election winners configuration"""
        col = self.bot.db["all_winners"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    # Target autocomplete for all commands
    @pres_canvassing.autocomplete("target")
    async def target_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @pres_donor.autocomplete("target")
    async def target_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @pres_ad.autocomplete("target")
    async def target_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @pres_poster.autocomplete("target")
    async def target_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @pres_speech.autocomplete("target")
    async def target_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    async def _get_presidential_candidate_choices(self, interaction: discord.Interaction, current: str):
        """Get presidential candidate choices for autocomplete"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")

        candidates = []

        if current_phase == "General Campaign":
            # Get from presidential winners
            winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
            if winners_config:
                primary_year = current_year - 1 if current_year % 2 == 0 else current_year
                candidates = [
                    w["name"] for w in winners_config.get("winners", [])
                    if w.get("primary_winner", False) and w["year"] == primary_year and w["office"] in ["President", "Vice President"]
                ]
        else:
            # Get from presidential signups
            signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
            if signups_config:
                candidates = [
                    c["name"] for c in signups_config.get("candidates", [])
                    if c["year"] == current_year and c["office"] in ["President", "Vice President"]
                ]

        return [app_commands.Choice(name=name, value=name)
                for name in candidates if current.lower() in name.lower()][:25]

    @app_commands.command(
        name="pres_campaign_status",
        description="View your presidential campaign statistics and available actions"
    )
    async def pres_campaign_status(self, interaction: discord.Interaction):
        # Check if user is a presidential candidate
        signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)

        if not candidate:
            await interaction.response.send_message(
                "❌ You must be a registered presidential candidate to view campaign status. Use `/pres_signup` first.",
                ephemeral=True
            )
            return

        # Check current phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "") if time_config else ""
        current_year = time_config["current_rp_date"].year if time_config else 2024

        candidate_name = candidate["name"]
        embed = discord.Embed(
            title="🎯 Presidential Campaign Status",
            description=f"**{candidate_name}** ({candidate['party']})",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🏛️ Campaign Info",
            value=f"**Office:** {candidate['office']}\n"
                  f"**Party:** {candidate['party']}\n"
                  f"**Year:** {candidate['year']}\n"
                  f"**Phase:** {current_phase}",
            inline=True
        )

        # Show different stats based on phase
        if current_phase == "General Campaign":
            # Show state points and national polling
            state_points = candidate.get("state_points", {})
            total_points = candidate.get("total_points", 0)

            # Calculate national polling percentage
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, candidate["office"])
            national_polling = general_percentages.get(candidate_name, 50.0)

            embed.add_field(
                name="📊 General Election Stats",
                value=f"**National Polling:** {national_polling:.1f}%\n"
                      f"**Total State Points:** {total_points:.2f}\n"
                      f"**States Campaigned:** {len([v for v in state_points.values() if v > 0])}",
                inline=True
            )

            # Show top 5 states by points
            top_states = sorted(state_points.items(), key=lambda x: x[1], reverse=True)[:5]
            if top_states:
                state_text = ""
                for state, points in top_states:
                    if points > 0:
                        state_text += f"**{state}:** {points:.2f}\n"
                if state_text:
                    embed.add_field(
                        name="🏆 Top Campaign States",
                        value=state_text,
                        inline=False
                    )
        else:
            # Show primary points
            primary_points = candidate.get("points", 0)
            embed.add_field(
                name="📈 Primary Campaign Stats",
                value=f"**Campaign Points:** {primary_points:.2f}%\n"
                      f"**Current Ranking:** Calculating...",
                inline=True
            )

        embed.add_field(
            name="⚡ Resources",
            value=f"**Stamina:** {candidate.get('stamina', 200)}/200\n"
                  f"**Corruption:** {candidate.get('corruption', 0)}",
            inline=True
        )

        # Check cooldowns for all actions
        cooldown_info = ""

        # Check speech cooldown (12 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_speech", 12):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_speech", 12)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            cooldown_info += f"🎤 **Speech:** {hours}h {minutes}m remaining\n"
        else:
            cooldown_info += "✅ **Speech:** Available\n"

        # Check donor cooldown (24 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_donor", 24):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_donor", 24)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            cooldown_info += f"💰 **Donor Appeal:** {hours}h {minutes}m remaining\n"
        else:
            cooldown_info += "✅ **Donor Appeal:** Available\n"

        # Check ad cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_ad", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_ad", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            cooldown_info += f"📺 **Video Ad:** {hours}h {minutes}m remaining\n"
        else:
            cooldown_info += "✅ **Video Ad:** Available\n"

        # Check poster cooldown (6 hours)
        if not self._check_cooldown(interaction.guild.id, interaction.user.id, "pres_poster", 6):
            remaining = self._get_cooldown_remaining(interaction.guild.id, interaction.user.id, "pres_poster", 6)
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            cooldown_info += f"🖼️ **Poster:** {hours}h {minutes}m remaining\n"
        else:
            cooldown_info += "✅ **Poster:** Available\n"

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
        if candidate.get('corruption', 0) > 20:
            tips.append("• High corruption may lead to scandals")
        if current_phase == "Primary Campaign" and candidate.get('points', 0) < 5:
            tips.append("• Use speech and donor commands for the biggest polling boost")
        elif current_phase == "General Campaign" and candidate.get('total_points', 0) < 10:
            tips.append("• Campaign in swing states for maximum impact")

        if tips:
            embed.add_field(
                name="💡 Campaign Tips",
                value="\n".join(tips),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_view_pres_campaign_points",
        description="View all presidential candidate points (Admin only)"
    )
    @app_commands.describe(
        filter_party="Filter by party (e.g., Republican, Democrat)",
        filter_office="Filter by office (e.g., President, Vice President)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_pres_campaign_points(
        self,
        interaction: discord.Interaction,
        filter_party: str = None,
        filter_office: str = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")

        embed = discord.Embed(
            title="🔍 Admin: Presidential Campaign Points",
            description=f"Detailed view of all presidential campaign points",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        candidates = []

        if current_phase == "General Campaign":
            # Get from presidential winners
            winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
            if winners_config:
                primary_year = current_year - 1 if current_year % 2 == 0 else current_year
                candidates = [
                    w for w in winners_config.get("winners", [])
                    if w.get("primary_winner", False) and w["year"] == primary_year and w["office"] in ["President", "Vice President"]
                ]
        else:
            # Get from presidential signups
            signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
            if signups_config:
                candidates = [
                    c for c in signups_config.get("candidates", [])
                    if c["year"] == current_year and c["office"] in ["President", "Vice President"]
                ]

        # Apply filters
        if filter_party:
            candidates = [c for c in candidates if filter_party.lower() in c.get("party", "").lower()]
        if filter_office:
            candidates = [c for c in candidates if filter_office.lower() in c.get("office", "").lower()]

        if not candidates:
            await interaction.response.send_message("❌ No presidential candidates found matching filters.", ephemeral=True)
            return

        # Group by office
        presidents = [c for c in candidates if c.get("office") == "President"]
        vice_presidents = [c for c in candidates if c.get("office") == "Vice President"]

        # Sort by points/total points
        if current_phase == "General Campaign":
            presidents.sort(key=lambda x: x.get("total_points", 0), reverse=True)
            vice_presidents.sort(key=lambda x: x.get("total_points", 0), reverse=True)
        else:
            presidents.sort(key=lambda x: x.get("points", 0), reverse=True)
            vice_presidents.sort(key=lambda x: x.get("points", 0), reverse=True)

        # Display Presidential candidates
        if presidents:
            pres_text = ""
            for candidate in presidents:
                candidate_name = candidate["name"]
                user = interaction.guild.get_member(candidate.get("user_id"))
                user_mention = user.mention if user else candidate_name

                if current_phase == "General Campaign":
                    general_percentages = self._calculate_general_election_percentages(interaction.guild.id, "President")
                    polling = general_percentages.get(candidate_name, 50.0)
                    total_points = candidate.get("total_points", 0)
                    pres_text += (
                        f"**{candidate_name}** ({candidate.get('party', 'N/A')})\n"
                        f"└ User: {user_mention}\n"
                        f"└ National Polling: **{polling:.1f}%**\n"
                        f"└ Total Points: {total_points:.2f}\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )
                else:
                    points = candidate.get("points", 0)
                    pres_text += (
                        f"**{candidate_name}** ({candidate.get('party', 'N/A')})\n"
                        f"└ User: {user_mention}\n"
                        f"└ Primary Points: **{points:.2f}%**\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )

            embed.add_field(
                name="🏛️ Presidential Candidates",
                value=pres_text,
                inline=False
            )

        # Display Vice Presidential candidates
        if vice_presidents:
            vp_text = ""
            for candidate in vice_presidents:
                candidate_name = candidate["name"]
                user = interaction.guild.get_member(candidate.get("user_id"))
                user_mention = user.mention if user else candidate_name

                if current_phase == "General Campaign":
                    general_percentages = self._calculate_general_election_percentages(interaction.guild.id, "Vice President")
                    polling = general_percentages.get(candidate_name, 50.0)
                    total_points = candidate.get("total_points", 0)
                    vp_text += (
                        f"**{candidate_name}** ({candidate.get('party', 'N/A')})\n"
                        f"└ User: {user_mention}\n"
                        f"└ National Polling: **{polling:.1f}%**\n"
                        f"└ Total Points: {total_points:.2f}\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )
                else:
                    points = candidate.get("points", 0)
                    vp_text += (
                        f"**{candidate_name}** ({candidate.get('party', 'N/A')})\n"
                        f"└ User: {user_mention}\n"
                        f"└ Primary Points: **{points:.2f}%**\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )

            embed.add_field(
                name="🎖️ Vice Presidential Candidates",
                value=vp_text,
                inline=False
            )

        # Add summary statistics
        all_candidates = presidents + vice_presidents
        if all_candidates: # Only calculate if there are candidates
            if current_phase == "General Campaign":
                total_points = sum(c.get("total_points", 0) for c in all_candidates)
                avg_points = total_points / len(all_candidates)
                max_points = max(c.get("total_points", 0) for c in all_candidates)
            else:
                total_points = sum(c.get("points", 0) for c in all_candidates)
                avg_points = total_points / len(all_candidates)
                max_points = max(c.get("points", 0) for c in all_candidates)

            embed.add_field(
                name="📈 Statistics",
                value=f"**Total Candidates:** {len(all_candidates)}\n"
                      f"**Presidents:** {len(presidents)}\n"
                      f"**Vice Presidents:** {len(vice_presidents)}\n"
                      f"**Average Points:** {avg_points:.2f}\n"
                      f"**Highest Points:** {max_points:.2f}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_reset_pres_cooldowns",
        description="Reset all presidential campaign action cooldowns for a user (Admin only)"
    )
    @app_commands.describe(
        user="The user whose cooldowns to reset (defaults to yourself)",
        action_type="The specific action cooldown to reset (defaults to all)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_pres_cooldowns(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        action_type: str = "all"
    ):
        target_user = user if user else interaction.user
        cooldowns_col = self.bot.db["pres_action_cooldowns"]
        
        if action_type == "all":
            # Reset all cooldowns for the user
            result = cooldowns_col.delete_many({
                "guild_id": interaction.guild.id,
                "user_id": target_user.id
            })
            
            await interaction.response.send_message(
                f"✅ Reset all presidential campaign cooldowns for {target_user.mention}. "
                f"Removed {result.deleted_count} cooldown record(s).",
                ephemeral=True
            )
        else:
            # Reset specific action type
            valid_actions = ["pres_speech", "pres_donor", "pres_ad", "pres_poster"]
            if action_type not in valid_actions:
                await interaction.response.send_message(
                    f"❌ Invalid action type. Valid options: {', '.join(valid_actions)}",
                    ephemeral=True
                )
                return
                
            result = cooldowns_col.delete_one({
                "guild_id": interaction.guild.id,
                "user_id": target_user.id,
                "action_type": action_type
            })
            
            if result.deleted_count > 0:
                await interaction.response.send_message(
                    f"✅ Reset {action_type} cooldown for {target_user.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"ℹ️ No {action_type} cooldown found for {target_user.mention}.",
                    ephemeral=True
                )

    @admin_reset_pres_cooldowns.autocomplete("action_type")
    async def action_type_autocomplete(self, interaction: discord.Interaction, current: str):
        actions = ["all", "pres_speech", "pres_donor", "pres_ad", "pres_poster"]
        return [app_commands.Choice(name=action, value=action)
                for action in actions if current.lower() in action.lower()][:25]

    @admin_add_pres_points.autocomplete("candidate_name")
    async def pres_points_candidate_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @admin_add_pres_points.autocomplete("state")
    async def pres_points_state_autocomplete(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @admin_add_general_points.autocomplete("candidate_name")
    async def candidate_autocomplete_admin_general(self, interaction: discord.Interaction, current: str):
        # Get general election candidates who won primaries
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        if not winners_config:
            return []

        candidates = [
            w["name"] for w in winners_config.get("winners", [])
            if w.get("primary_winner", False) # Ensure they won the primary
        ]

        return [app_commands.Choice(name=name, value=name)
                for name in candidates if current.lower() in name.lower()][:25]

    @admin_add_general_points.autocomplete("office")
    async def office_autocomplete_admin_general(self, interaction: discord.Interaction, current: str):
        # Offices relevant to general elections
        offices = ["President", "Vice President", "Senator", "Governor", "Lieutenant Governor", "Attorney General", "Secretary of State", "Representative"]
        return [app_commands.Choice(name=office, value=office)
                for office in offices if current.lower() in office.lower()][:25]

async def setup(bot):
    await bot.add_cog(PresCampaignActions(bot))