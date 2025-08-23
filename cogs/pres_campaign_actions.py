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

            # Add momentum effects during General Campaign
            self._add_momentum_from_campaign_action(guild_id, user_id, state_name.upper(), polling_boost)
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

    def _add_momentum_from_campaign_action(self, guild_id: int, user_id: int, state_name: str, points_gained: float):
        """Adds momentum to a state based on campaign actions."""
        momentum_col = self.bot.db["presidential_momentum"]
        
        # Define momentum parameters
        momentum_gain_factor = 0.1  # How much momentum is gained per point
        max_momentum = 100.0
        
        # Calculate momentum gained
        momentum_gained = points_gained * momentum_gain_factor
        
        # Update or insert momentum for the state
        momentum_col.update_one(
            {"guild_id": guild_id, "state": state_name},
            {
                "$inc": {"momentum": momentum_gained},
                "$set": {"last_updated": datetime.utcnow()}
            },
            upsert=True
        )
        
        # Ensure momentum does not exceed max
        momentum_col.update_one(
            {"guild_id": guild_id, "state": state_name},
            {"$min": {"momentum": max_momentum}}
        )

    def _get_state_lean_and_momentum(self, guild_id: int, state_name: str):
        """Retrieves the lean and current momentum for a given state."""
        state_data = PRESIDENTIAL_STATE_DATA.get(state_name.upper())
        if not state_data:
            return None, None, None # State not found

        # Default lean based on party alignment
        lean_percentage = 0.0
        if state_data["democrat"] > state_data["republican"]:
            lean_percentage = state_data["democrat"] - 50
        elif state_data["republican"] > state_data["democrat"]:
            lean_percentage = state_data["republican"] - 50
        
        # Get momentum from database
        momentum_col = self.bot.db["presidential_momentum"]
        momentum_record = momentum_col.find_one({"guild_id": guild_id, "state": state_name.upper()})
        current_momentum = momentum_record.get("momentum", 0.0) if momentum_record else 0.0

        return lean_percentage, current_momentum, state_data

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
                
                # Get state lean and momentum
                lean_percentage, current_momentum, _ = self._get_state_lean_and_momentum(guild_id, state_name)

                # Determine party alignment bonus
                party_bonus = 0.0
                candidate_party = candidate["party"].lower()
                if "democrat" in candidate_party or "democratic" in candidate_party:
                    party_bonus = state_data["democrat"] / 100.0
                elif "republican" in candidate_party:
                    party_bonus = state_data["republican"] / 100.0
                else:
                    party_bonus = state_data["other"] / 100.0
                
                # Calculate effective percentage considering lean and momentum
                # Lean adds a base advantage, momentum amplifies it (exponentially)
                # The formula here is a simplified representation: base advantage + momentum effect
                # A more complex formula could involve exponential growth of momentum's impact.
                
                # Example: lean_percentage + (current_momentum * 0.1) + (campaign_points * 0.01)
                # For now, let's use a simpler approach where momentum boosts the base advantage.
                
                effective_state_advantage = (party_bonus * 100) + lean_percentage + current_momentum # Simplified: adding momentum directly
                
                # Add the campaign points bonus to the effective advantage
                effective_state_advantage += (campaign_points * 0.01) * 100 # Convert campaign points to percentage

                # Each state contributes equally (1/50th of total)
                state_weight = 1.0 / len(PRESIDENTIAL_STATE_DATA)
                
                state_contribution = effective_state_advantage * state_weight
                total_percentage += state_contribution

            final_percentages[candidate_name] = max(0.01, total_percentage) # Ensure at least 0.01%

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
        current_phase = time_config.get("current_phase", "") if time_config else ""
        
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

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target_name)

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
        current_phase = time_config.get("current_phase", "") if time_config else ""
        
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

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_upper, polling_boost=0.1, stamina_cost=1)

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
        current_phase = time_config.get("current_phase", "") if time_config else ""
        
        if current_phase == "General Campaign":
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_candidate["office"])
            updated_percentage = general_percentages.get(target_candidate["name"], 50.0)
            
            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +0.1\n**Stamina Cost:** -1",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target_candidate['name']}\n**State:** {state_upper}\n**Polling Boost:** +0.1%\n**Stamina Cost:** -1",
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
            current_phase = time_config.get("current_phase", "") if time_config else ""
            
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
        current_phase = time_config.get("current_phase", "") if time_config else ""
        
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
            candidates = [c for c in candidates if filter_party.lower() in c["party"].lower()]
        if filter_office:
            candidates = [c for c in candidates if filter_office.lower() in c["office"].lower()]

        if not candidates:
            await interaction.response.send_message("❌ No presidential candidates found.", ephemeral=True)
            return

        # Group by office
        presidents = [c for c in candidates if c["office"] == "President"]
        vice_presidents = [c for c in candidates if c["office"] == "Vice President"]

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
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else candidate_name

                if current_phase == "General Campaign":
                    general_percentages = self._calculate_general_election_percentages(interaction.guild.id, "President")
                    polling = general_percentages.get(candidate_name, 50.0)
                    total_points = candidate.get("total_points", 0)
                    pres_text += (
                        f"**{candidate_name}** ({candidate['party']})\n"
                        f"└ User: {user_mention}\n"
                        f"└ National Polling: **{polling:.1f}%**\n"
                        f"└ Total Points: {total_points:.2f}\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )
                else:
                    points = candidate.get("points", 0)
                    pres_text += (
                        f"**{candidate_name}** ({candidate['party']})\n"
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
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else candidate_name

                if current_phase == "General Campaign":
                    general_percentages = self._calculate_general_election_percentages(interaction.guild.id, "Vice President")
                    polling = general_percentages.get(candidate_name, 50.0)
                    total_points = candidate.get("total_points", 0)
                    vp_text += (
                        f"**{candidate_name}** ({candidate['party']})\n"
                        f"└ User: {user_mention}\n"
                        f"└ National Polling: **{polling:.1f}%**\n"
                        f"└ Total Points: {total_points:.2f}\n"
                        f"└ Stamina: {candidate.get('stamina', 200)}/200\n"
                        f"└ Corruption: {candidate.get('corruption', 0)}\n\n"
                    )
                else:
                    points = candidate.get("points", 0)
                    vp_text += (
                        f"**{candidate_name}** ({candidate['party']})\n"
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
        if current_phase == "General Campaign":
            total_points = sum(c.get("total_points", 0) for c in all_candidates)
            avg_points = total_points / len(all_candidates) if all_candidates else 0
            max_points = max(c.get("total_points", 0) for c in all_candidates) if all_candidates else 0
        else:
            total_points = sum(c.get("points", 0) for c in all_candidates)
            avg_points = total_points / len(all_candidates) if all_candidates else 0
            max_points = max(c.get("points", 0) for c in all_candidates) if all_candidates else 0

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
        name="admin_add_pres_points",
        description="Directly add campaign points to a presidential candidate (Admin only)"
    )
    @app_commands.describe(
        candidate_name="Name of the presidential candidate",
        points="Points to add (can be negative to subtract)",
        state="State to add points to (required for General Campaign)",
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
                    "❌ State parameter is required for General Campaign phase.",
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

            # Update state points and total points for general campaign
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
                title="⚙️ Presidential Points Added (General Campaign)",
                description=f"Admin point adjustment for **{target_candidate['name']}**",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 General Campaign Adjustment",
                value=f"**Candidate:** {target_candidate['name']}\n"
                      f"**State:** {state_upper}\n"
                      f"**Points Added:** {points:+.2f}\n"
                      f"**National Polling:** {updated_percentage:.1f}%\n"
                      f"**Reason:** {reason}",
                inline=False
            )

        else:
            # For primary campaign, add to general points
            target_col.update_one(
                {"guild_id": interaction.guild.id, "candidates.user_id": target_candidate["user_id"]},
                {
                    "$inc": {
                        "candidates.$.points": points
                    }
                }
            )

            # Get updated points
            updated_candidate = target_col.find_one({"guild_id": interaction.guild.id})
            updated_points = 0
            for candidate in updated_candidate.get("candidates", []):
                if candidate["user_id"] == target_candidate["user_id"]:
                    updated_points = candidate.get("points", 0)
                    break

            embed = discord.Embed(
                title="⚙️ Presidential Points Added (Primary Campaign)",
                description=f"Admin point adjustment for **{target_candidate['name']}**",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 Primary Campaign Adjustment",
                value=f"**Candidate:** {target_candidate['name']}\n"
                      f"**Points Added:** {points:+.2f}\n"
                      f"**Total Points:** {updated_points:.2f}%\n"
                      f"**Reason:** {reason}",
                inline=False
            )

        embed.set_footer(text=f"Adjusted by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Autocomplete for admin commands
    @admin_add_pres_points.autocomplete("candidate_name")
    async def candidate_autocomplete_admin(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

    @admin_add_pres_points.autocomplete("state")
    async def state_autocomplete_admin(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

async def setup(bot):
    await bot.add_cog(PresCampaignActions(bot))