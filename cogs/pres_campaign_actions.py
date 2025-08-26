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
        try:
            time_col, time_config = self._get_time_config(guild_id)
            current_phase = time_config.get("current_phase", "") if time_config else ""
            current_year = time_config["current_rp_date"].year if time_config else 2024

            if current_phase == "General Campaign":
                # For general campaign, check presidential winners collection first
                winners_col, winners_config = self._get_presidential_winners_config(guild_id)
                if winners_config:
                    winners_data = winners_config.get("winners", [])
                    
                    # Handle both list and dict formats for winners
                    if isinstance(winners_data, list):
                        # New list format
                        primary_year = current_year - 1 if current_year % 2 == 0 else current_year
                        
                        for winner in winners_data:
                            if (isinstance(winner, dict) and
                                winner.get("name", "").lower() == candidate_name.lower() and
                                winner.get("primary_winner", False) and
                                winner.get("year") == primary_year and
                                winner.get("office") in ["President", "Vice President"]):
                                return winners_col, winner
                    
                    elif isinstance(winners_data, dict):
                        # Old dict format: {party: candidate_name}
                        for party, winner_name in winners_data.items():
                            if isinstance(winner_name, str) and winner_name.lower() == candidate_name.lower():
                                # Get full candidate data from presidential signups
                                signups_col, signups_config = self._get_presidential_config(guild_id)
                                if signups_config:
                                    election_year = winners_config.get("election_year", current_year)
                                    signup_year = election_year - 1 if election_year % 2 == 0 else election_year
                                    
                                    candidates_list = signups_config.get("candidates", [])
                                    if isinstance(candidates_list, list):
                                        for candidate in candidates_list:
                                            if (isinstance(candidate, dict) and
                                                candidate.get("name", "").lower() == candidate_name.lower() and
                                                candidate.get("year") == signup_year and
                                                candidate.get("office") in ["President", "Vice President"]):
                                                # Create a copy and add general campaign specific fields
                                                general_candidate = candidate.copy()
                                                general_candidate["primary_winner"] = True
                                                general_candidate["total_points"] = general_candidate.get("points", 0.0)
                                                general_candidate["state_points"] = general_candidate.get("state_points", {})
                                                return signups_col, general_candidate
                                
                                # If not found in signups, create a basic candidate object
                                basic_candidate = {
                                    "name": winner_name,
                                    "user_id": 0,  # Will need to be populated
                                    "party": party,
                                    "office": "President",
                                    "year": signup_year if 'signup_year' in locals() else current_year,
                                    "stamina": 200,
                                    "corruption": 0,
                                    "total_points": 0.0,
                                    "state_points": {},
                                    "primary_winner": True
                                }
                                return winners_col, basic_candidate

                # Fallback to all_winners system
                all_winners_col = self.bot.db["winners"]
                all_winners_config = all_winners_col.find_one({"guild_id": guild_id})

                if all_winners_config:
                    primary_year = current_year - 1 if current_year % 2 == 0 else current_year
                    winners_list = all_winners_config.get("winners", [])
                    
                    if isinstance(winners_list, list):
                        for winner in winners_list:
                            if (isinstance(winner, dict) and
                                winner.get("candidate", "").lower() == candidate_name.lower() and 
                                winner.get("primary_winner", False) and
                                winner.get("year") == primary_year and
                                winner.get("office") in ["President", "Vice President"]):
                                # Convert all_winners format to expected format
                                candidate_dict = {
                                    "name": winner.get("candidate"),
                                    "user_id": winner.get("user_id"),
                                    "party": winner.get("party"),
                                    "office": winner.get("office"),
                                    "year": winner.get("year"),
                                    "stamina": winner.get("stamina", 200),
                                    "corruption": winner.get("corruption", 0),
                                    "total_points": winner.get("points", 0.0),
                                    "state_points": winner.get("state_points", {}),
                                    "primary_winner": True
                                }
                                return all_winners_col, candidate_dict

                return None, None
            else:
                # Look in presidential signups collection for primary campaign
                signups_col, signups_config = self._get_presidential_config(guild_id)

                if not signups_config:
                    return None, None

                candidates_list = signups_config.get("candidates", [])
                if isinstance(candidates_list, list):
                    for candidate in candidates_list:
                        if (isinstance(candidate, dict) and
                            candidate.get("name", "").lower() == candidate_name.lower() and 
                            candidate.get("year") == current_year and
                            candidate.get("office") in ["President", "Vice President"]):
                            return signups_col, candidate

                return signups_col, None
                
        except Exception as e:
            print(f"Error in _get_presidential_candidate_by_name: {e}")
            import traceback
            traceback.print_exc()
            return None, None

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

    def _check_cooldown(self, guild_id: int, user_id: int, action: str, hours: int) -> bool:
        """Check if user is on cooldown for a specific action"""
        cooldowns_col = self.bot.db["action_cooldowns"]

        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action": action
        })

        if not cooldown_record:
            return True

        from datetime import datetime, timedelta
        last_used = cooldown_record["last_used"]
        cooldown_duration = timedelta(hours=hours)

        return datetime.utcnow() > last_used + cooldown_duration

    def _get_cooldown_remaining(self, guild_id: int, user_id: int, action: str, hours: int):
        """Get remaining cooldown time"""
        cooldowns_col = self.bot.db["action_cooldowns"]

        cooldown_record = cooldowns_col.find_one({
            "guild_id": guild_id,
            "user_id": user_id,
            "action": action
        })

        if not cooldown_record:
            return timedelta(0)

        from datetime import datetime, timedelta
        last_used = cooldown_record["last_used"]
        cooldown_duration = timedelta(hours=hours)
        next_available = last_used + cooldown_duration

        if datetime.utcnow() >= next_available:
            return timedelta(0)

        return next_available - datetime.utcnow()

    def _set_cooldown(self, guild_id: int, user_id: int, action: str):
        """Set cooldown for a user action"""
        cooldowns_col = self.bot.db["action_cooldowns"]

        cooldowns_col.update_one(
            {
                "guild_id": guild_id,
                "user_id": user_id,
                "action": action
            },
            {
                "$set": {
                    "last_used": datetime.utcnow()
                }
            },
            upsert=True
        )

    def _apply_buff_debuff_multiplier(self, base_points: float, user_id: int, guild_id: int, action_type: str) -> float:
        """Apply any active buffs or debuffs to the points gained"""
        # For now, return base points without modification
        # This can be expanded later to include buff/debuff system
        return base_points

    def _add_momentum_from_campaign_action(self, guild_id: int, user_id: int, state_name: str, points_gained: float):
        """Adds momentum to a state based on campaign actions with auto-collapse protection."""
        # Use the momentum system from the momentum cog
        momentum_cog = self.bot.get_cog('Momentum')
        if not momentum_cog:
            return  # Momentum system not loaded

        # Get momentum config
        momentum_col, momentum_config = momentum_cog._get_momentum_config(guild_id)

        # Get user's candidate to determine party
        signups_col, candidate = self._get_user_presidential_candidate(guild_id, user_id)
        if not candidate:
            return

        # Determine party key
        party = candidate.get("party", "").lower()
        if "republican" in party:
            party_key = "Republican"
        elif "democrat" in party:
            party_key = "Democrat"
        else:
            party_key = "Independent"

        # Calculate momentum gained (reduced factor to prevent spam)
        momentum_gain_factor = 2.0  # Momentum gained per campaign point
        momentum_gained = points_gained * momentum_gain_factor

        # Get current momentum
        current_momentum = momentum_config["state_momentum"].get(state_name, {}).get(party_key, 0.0)
        new_momentum = current_momentum + momentum_gained

        # Check for auto-collapse
        final_momentum, collapsed = momentum_cog._check_and_apply_auto_collapse(
            momentum_col, guild_id, state_name, party_key, new_momentum
        )

        if not collapsed:
            # No collapse occurred, update normally
            momentum_col.update_one(
                {"guild_id": guild_id},
                {
                    "$set": {
                        f"state_momentum.{state_name}.{party_key}": final_momentum,
                        f"state_momentum.{state_name}.last_updated": datetime.utcnow()
                    }
                }
            )

            # Log the momentum gain
            if momentum_gained > 0.1:  # Only log significant gains
                momentum_cog._add_momentum_event(
                    momentum_col, guild_id, state_name, party_key,
                    momentum_gained, f"Campaign action (+{points_gained:.1f} pts)", user_id
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
        """Calculate general election percentages using complete proportional redistribution with 100% normalization"""
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

        # Define minimum percentage floors for presidential races
        def get_presidential_minimum_floor(candidate):
            party = candidate.get("party", "").lower()
            if any(keyword in party for keyword in ['democrat', 'republican']):
                return 25.0  # 25% minimum for major parties
            else:
                return 2.0   # 2% minimum for independents/third parties

        # Calculate baseline percentages based on party alignment
        baseline_percentages = {}
        num_candidates = len(candidates)

        # Count major parties
        major_parties = []
        for candidate in candidates:
            party = candidate["party"].lower()
            if "democrat" in party or "democratic" in party:
                if "Democrat" not in major_parties:
                    major_parties.append("Democrat")
            elif "republican" in party:
                if "Republican" not in major_parties:
                    major_parties.append("Republican")

        major_parties_present = len(major_parties)

        if major_parties_present == 2 and num_candidates == 2:
            # Two-way race between major parties: 50-50
            for candidate in candidates:
                baseline_percentages[candidate["name"]] = 50.0
        elif major_parties_present == 2 and num_candidates > 2:
            # Democrat + Republican + others: 40-40 for major, split remainder among others
            remaining_percentage = 20.0
            other_parties_count = num_candidates - 2
            other_party_percentage = remaining_percentage / other_parties_count if other_parties_count > 0 else 0

            for candidate in candidates:
                party = candidate["party"].lower()
                if "democrat" in party or "democratic" in party or "republican" in party:
                    baseline_percentages[candidate["name"]] = 40.0
                else:
                    baseline_percentages[candidate["name"]] = other_party_percentage
        else:
            # No standard major party setup, split evenly
            for candidate in candidates:
                baseline_percentages[candidate["name"]] = 100.0 / num_candidates

        # Start with baseline percentages
        current_percentages = baseline_percentages.copy()

        # Apply campaign effects using COMPLETE proportional redistribution
        for candidate in candidates:
            candidate_name = candidate["name"]
            total_campaign_points = candidate.get("total_points", 0.0)

            if total_campaign_points > 0:
                # Points gained equals the campaign points directly
                points_gained = total_campaign_points

                # Calculate total percentage that can be taken from other candidates
                total_available_to_take = 0.0
                for other_candidate in candidates:
                    if other_candidate != candidate:
                        other_name = other_candidate["name"]
                        other_current = current_percentages[other_name]
                        other_minimum = get_presidential_minimum_floor(other_candidate)
                        available = max(0, other_current - other_minimum)
                        total_available_to_take += available

                # Limit gains to what's actually available
                actual_gain = min(points_gained, total_available_to_take)
                current_percentages[candidate_name] += actual_gain

                # Distribute losses proportionally among other candidates
                if total_available_to_take > 0:
                    for other_candidate in candidates:
                        if other_candidate != candidate:
                            other_name = other_candidate["name"]
                            other_current = current_percentages[other_name]
                            other_minimum = get_presidential_minimum_floor(other_candidate)
                            available = max(0, other_current - other_minimum)

                            if available > 0:
                                proportional_loss = (available / total_available_to_take) * actual_gain
                                current_percentages[other_name] -= proportional_loss

        # Ensure minimum floors are respected
        for candidate in candidates:
            candidate_name = candidate["name"]
            minimum_floor = get_presidential_minimum_floor(candidate)
            current_percentages[candidate_name] = max(current_percentages[candidate_name], minimum_floor)

        # COMPLETE 100% NORMALIZATION - Force total to exactly 100%
        total_percentage = sum(current_percentages.values())
        if total_percentage > 0:
            for candidate_name in current_percentages:
                current_percentages[candidate_name] = (current_percentages[candidate_name] / total_percentage) * 100.0

        # Final verification and correction for floating point errors
        final_total = sum(current_percentages.values())
        if abs(final_total - 100.0) > 0.001:
            # Apply micro-adjustment to the largest percentage
            largest_candidate = max(current_percentages.keys(), key=lambda x: current_percentages[x])
            adjustment = 100.0 - final_total
            current_percentages[largest_candidate] += adjustment

        final_percentages = current_percentages
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

        # Ensure candidate is properly structured
        if not isinstance(candidate, dict):
            await interaction.response.send_message(
                "❌ Error retrieving candidate data. Please try again.",
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
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Estimate stamina cost
        estimated_stamina = 2.25
        if target_candidate.get("stamina", 200) < estimated_stamina:
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
            description=f"**{candidate['name']}** ({candidate['party']}) gives a speech supporting **{target_name}** in {state_name}!",
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
            target_office = target_candidate.get("office", "President")
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
            updated_percentage = general_percentages.get(target_name, 50.0)

            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_name}\n**State:** {state_name}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Characters:** {char_count:,}",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_name}\n**State:** {state_name}\n**Polling Boost:** +{polling_boost:.2f}%\n**Characters:** {char_count:,}",
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
        polling_boost = min(polling_boost, 3.0)

        # Get target candidate
        target_signups_col, target_candidate = self._get_presidential_candidate_by_name(interaction.guild.id, target_name)

        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target_name}' not found.",
                ephemeral=True
            )
            return

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate.get("user_id"), 
                                                 state_name, polling_boost=polling_boost, corruption_increase=5, stamina_cost=1.5)

        embed = discord.Embed(
            title="💰 Presidential Donor Fundraising",
            description=f"**{candidate['name']}** makes a donor appeal for **{target_name}** in {state_name}!",
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
            target_office = target_candidate.get("office", "President")
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
            updated_percentage = general_percentages.get(target_name, 50.0)

            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_name}\n**State:** {state_name}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Corruption:** +5\n**Characters:** {char_count:,}",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Impact",
                value=f"**Target:** {target_name}\n**State:** {state_name}\n**Polling Boost:** +{polling_boost:.2f}%\n**Corruption:** +5\n**Characters:** {char_count:,}",
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
        if not target_candidate or not isinstance(target_candidate, dict):
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
        if target_candidate.get("stamina", 200) < 1:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina! They need at least 1 stamina for canvassing.",
                ephemeral=True
            )
            return

        # Apply buff/debuff multipliers to canvassing points
        polling_boost = self._apply_buff_debuff_multiplier(0.1, target_candidate["user_id"], interaction.guild.id, "pres_canvassing")

        # Update target candidate stats
        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                 state_upper, polling_boost=polling_boost, stamina_cost=1)

        embed = discord.Embed(
            title="🚪 Presidential Door-to-Door Canvassing",
            description=f"**{candidate['name']}** goes canvassing for **{target}** in {state_upper}!",
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
            target_office = target_candidate.get("office", "President")
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
            updated_percentage = general_percentages.get(target, 50.0)

            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Results",
                value=f"**Target:** {target}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1",
                inline=True
            )

        # Safe access for stamina display
        current_stamina = target_candidate.get("stamina", 0) if isinstance(target_candidate, dict) else 0
        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{current_stamina - 1}/200",
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
        if not target_candidate or not isinstance(target_candidate, dict):
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
        if target_candidate.get("stamina", 200) < 1.5:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a donor appeal! They need at least 1.5 stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Send initial message asking for donor appeal
        await interaction.response.send_message(
            f"💰 **{candidate['name']}**, please reply to this message with your presidential donor appeal!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• Minimum 400 characters\n"
            f"• Maximum 3000 characters\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** Up to 3% polling boost based on length, +5 corruption, -1.5 stamina",
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
            self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_donor")

            # Calculate polling boost - 1% per 1000 characters  
            polling_boost = (char_count / 1000) * 1.0
            polling_boost = min(polling_boost, 3.0)

            # Update target candidate stats
            self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate.get("user_id"), 
                                                     state_upper, polling_boost=polling_boost, corruption_increase=5, stamina_cost=1.5)

            embed = discord.Embed(
                title="💰 Presidential Donor Fundraising",
                description=f"**{candidate['name']}** makes a donor appeal for **{target}** in {state_upper}!",
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
                target_office = target_candidate.get("office", "President")
                general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
                updated_percentage = general_percentages.get(target, 50.0)

                embed.add_field(
                    name="📊 Impact",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Corruption:** +5\n**Characters:** {char_count:,}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📊 Impact",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Corruption:** +5\n**Characters:** {char_count:,}",
                    inline=True
                )

            embed.add_field(
                name="⚠️ Warning",
                value="High corruption may lead to scandals!",
                inline=True
            )

            embed.set_footer(text=f"Next donor appeal available in 24 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate['name']}**, your donor appeal timed out. Please use `/pres_donor` again and reply with your appeal within 5 minutes."
            )

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
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Check stamina
        if target_candidate.get("stamina", 200) < 1.5:
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
                description=f"**{candidate['name']}** creates a campaign advertisement for **{target}** in {state_upper}!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            # For general campaign, show updated percentages
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            if current_phase == "General Campaign":
                target_office = target_candidate.get("office", "President")
                general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
                updated_percentage = general_percentages.get(target, 50.0)

                embed.add_field(
                    name="📊 Ad Performance",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1.5",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📊 Ad Performance",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1.5",
                    inline=True
                )

            embed.add_field(
                name="📱 Reach",
                value=f"Broadcast across {state_upper}\nsocial media and local TV",
                inline=True
            )

            # Safe access for stamina display
            current_stamina = target_candidate.get("stamina", 0) if isinstance(target_candidate, dict) else 0
            embed.add_field(
                name="⚡ Target's Current Stamina",
                value=f"{current_stamina - 1.5:.1f}/200",
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

        # Ensure candidate is properly structured
        if not isinstance(candidate, dict):
            await interaction.response.send_message(
                "❌ Error retrieving candidate data. Please try again.",
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
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Target presidential candidate '{target}' not found.",
                ephemeral=True
            )
            return

        # Ensure target candidate is properly structured
        if not target_candidate or not isinstance(target_candidate, dict):
            await interaction.response.send_message(
                f"❌ Error retrieving target candidate data. Please contact an administrator.",
                ephemeral=True
            )
            return

        # Validate required fields exist and handle missing fields gracefully
        required_fields = ["name", "user_id"]
        missing_fields = [field for field in required_fields if not target_candidate.get(field)]
        if missing_fields:
            await interaction.response.send_message(
                f"❌ Target candidate data is incomplete. Missing fields: {', '.join(missing_fields)}. Please contact an administrator.",
                ephemeral=True
            )
            return

        # Check stamina with safe access
        current_stamina = target_candidate.get("stamina", 200)
        if current_stamina < 1:
            await interaction.response.send_message(
                f"❌ {target_candidate.get('name', 'Candidate')} doesn't have enough stamina! They need at least 1 stamina to create a poster.",
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
        target_user_id = target_candidate.get("user_id")
        if not target_user_id:
            await interaction.response.send_message(
                "❌ Error: Invalid candidate data structure. Please contact an administrator.",
                ephemeral=True
            )
            return

        # Ensure target_signups_col is valid
        if not target_signups_col:
            await interaction.response.send_message(
                "❌ Error: Unable to update candidate stats. Please contact an administrator.",
                ephemeral=True
            )
            return

        self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_user_id, 
                                                 state_upper, polling_boost=polling_boost, stamina_cost=1)

        # Set cooldown
        self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_poster")

        embed = discord.Embed(
            title="🖼️ Presidential Campaign Poster",
            description=f"**{candidate['name']}** creates campaign materials for **{target}** in {state_upper}!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        # For general campaign, show updated percentages
        time_col, time_config = self._get_time_config(interaction.guild.id)
        current_phase = time_config.get("current_phase", "") if time_config else ""

        if current_phase == "General Campaign":
            target_office = target_candidate.get("office", "President")
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
            updated_percentage = general_percentages.get(target, 50.0)

            embed.add_field(
                name="📊 Poster Impact",
                value=f"**Target:** {target}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Stamina Cost:** -1",
                inline=True
            )
        else:
            embed.add_field(
                name="📊 Poster Impact",
                value=f"**Target:** {target}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Stamina Cost:** -1",
                inline=True
            )

        embed.add_field(
            name="📍 Distribution",
            value=f"Posted throughout {state_upper}\nat community centers and events",
            inline=True
        )

        # Safe access for stamina display with proper validation
        current_stamina = target_candidate.get("stamina", 200) if isinstance(target_candidate, dict) else 200
        embed.add_field(
            name="⚡ Target's Current Stamina",
            value=f"{current_stamina - 1}/200",
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

        # Ensure candidate is properly structured
        if not isinstance(candidate, dict):
            await interaction.response.send_message(
                "❌ Error retrieving candidate data. Please try again.",
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
        if not target_candidate or not isinstance(target_candidate, dict):
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
        if target_candidate.get("stamina", 200) < 2.25:
            await interaction.response.send_message(
                f"❌ {target_candidate['name']} doesn't have enough stamina for a speech! They need at least 2.25 stamina (current: {target_candidate['stamina']}).",
                ephemeral=True
            )
            return

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{candidate['name']}**, please reply to this message with your presidential campaign speech!\n\n"
            f"**Target:** {target_candidate['name']}\n"
            f"**State:** {state_upper}\n"
            f"**Requirements:**\n"
            f"• 600-3000 characters\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** Up to 2.5% polling boost based on length, -2.25 stamina",
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
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            speech_content = reply_message.content
            char_count = len(speech_content)

            # Check character limits
            if char_count < 600 or char_count > 3000:
                await reply_message.reply(f"❌ Presidential speech must be 600-3000 characters. You wrote {char_count} characters.")
                return

            # Set cooldown after successful validation
            self._set_cooldown(interaction.guild.id, interaction.user.id, "pres_speech")

            # Calculate polling boost - 1% per 1200 characters
            polling_boost = (char_count / 1200) * 1.0
            polling_boost = min(polling_boost, 2.5)

            # Update target candidate stats
            self._update_presidential_candidate_stats(target_signups_col, interaction.guild.id, target_candidate["user_id"], 
                                                     state_upper, polling_boost=polling_boost, stamina_cost=2.25)

            # Create public speech announcement
            embed = discord.Embed(
                title="🎤 Presidential Campaign Speech",
                description=f"**{candidate['name']}** ({candidate['party']}) gives a speech supporting **{target}** in {state_upper}!",
                color=discord.Color.blue(),
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

            # For general campaign, show updated percentages
            time_col, time_config = self._get_time_config(interaction.guild.id)
            current_phase = time_config.get("current_phase", "") if time_config else ""

            if current_phase == "General Campaign":
                target_office = target_candidate.get("office", "President")
                general_percentages = self._calculate_general_election_percentages(interaction.guild.id, target_office)
                updated_percentage = general_percentages.get(target, 50.0)

                embed.add_field(
                    name="📊 Impact",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**National Polling:** {updated_percentage:.1f}%\n**State Points:** +{polling_boost:.2f}\n**Characters:** {char_count:,}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📊 Impact",
                    value=f"**Target:** {target}\n**State:** {state_upper}\n**Polling Boost:** +{polling_boost:.2f}%\n**Characters:** {char_count:,}",
                    inline=True
                )

            embed.set_footer(text=f"Next speech available in 12 hours")

            await reply_message.reply(embed=embed)

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=f"⏰ **{candidate.get('name', 'User')}**, your speech timed out. Please use `/pres_speech` again and reply with your speech within 5 minutes."
            )
        except Exception as e:
            print(f"Error in pres_speech: {e}")
            await interaction.edit_original_response(
                content=f"❌ An error occurred while processing your speech. Please try again."
            )

    # State autocomplete for all commands
    @pres_canvassing.autocomplete("state")
    async def state_autocomplete_canvassing(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

    @pres_donor.autocomplete("state")
    async def state_autocomplete_donor(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

    @pres_ad.autocomplete("state")
    async def state_autocomplete_ad(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

    @pres_poster.autocomplete("state")
    async def state_autocomplete_poster(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

    @pres_speech.autocomplete("state")
    async def state_autocomplete_speech(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

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
        try:
            # Get time config for current year/phase context
            time_col, time_config = self._get_time_config(interaction.guild.id)
            
            if not time_config:
                print("No time config found")
                return []

            current_year = time_config["current_rp_date"].year
            current_phase = time_config.get("current_phase", "")
            candidate_names = []

            print(f"Debug: Current phase: {current_phase}, Current year: {current_year}")

            if current_phase == "General Campaign":
                # For general campaign, only show primary winners who advanced to general election
                print(f"General Campaign phase detected, showing only primary winners")
                
                # First, try to get from presidential winners collection
                winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
                
                print(f"Debug: winners_config type: {type(winners_config)}")
                print(f"Debug: winners_config content: {winners_config}")
                
                if winners_config and winners_config.get("winners"):
                    party_winners = winners_config.get("winners", {})
                    print(f"Debug: party_winners type: {type(party_winners)}")
                    print(f"Debug: party_winners content: {party_winners}")
                    
                    if isinstance(party_winners, dict):
                        for party, winner_name in party_winners.items():
                            print(f"Debug: Processing party: {party}, winner_name type: {type(winner_name)}, value: {winner_name}")
                            if winner_name and isinstance(winner_name, str):
                                candidate_names.append(winner_name)
                                print(f"Added general campaign candidate from presidential_winners: {winner_name}")
                    else:
                        print(f"Error: party_winners is not a dict, it's {type(party_winners)}: {party_winners}")

                # If no winners from presidential_winners, check all_winners system as fallback
                if not candidate_names:
                    all_winners_col = self.bot.db["winners"]
                    all_winners_config = all_winners_col.find_one({"guild_id": interaction.guild.id})

                    print(f"Debug: all_winners_config type: {type(all_winners_config)}")
                    
                    if all_winners_config:
                        primary_year = current_year - 1 if current_year % 2 == 0 else current_year
                        print(f"Debug: primary_year calculated as: {primary_year}")
                        
                        winners_list = all_winners_config.get("winners", [])
                        print(f"Debug: winners_list type: {type(winners_list)}, length: {len(winners_list) if isinstance(winners_list, list) else 'N/A'}")
                        
                        if isinstance(winners_list, list):
                            for i, winner in enumerate(winners_list):
                                print(f"Debug: Processing winner {i}: type: {type(winner)}, content: {winner}")
                                
                                # Ensure winner is a dictionary before accessing dict methods
                                if isinstance(winner, dict):
                                    office = winner.get("office")
                                    primary_winner = winner.get("primary_winner", False)
                                    year = winner.get("year")
                                    candidate_name = winner.get("candidate")
                                    
                                    print(f"Debug: office: {office}, primary_winner: {primary_winner}, year: {year}, candidate: {candidate_name}")
                                    
                                    if (office in ["President", "Vice President"] and 
                                        primary_winner and
                                        year == primary_year and
                                        candidate_name):
                                        candidate_names.append(candidate_name)
                                        print(f"Added general campaign candidate from all_winners: {candidate_name}")
                                else:
                                    print(f"Error: winner is not a dict, it's {type(winner)}: {winner}")
                        else:
                            print(f"Error: winners_list is not a list, it's {type(winners_list)}: {winners_list}")

            else:
                # For primary campaign or other phases, show all registered candidates
                print(f"Primary/Other phase detected ({current_phase}), showing all registered candidates")
                
                signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
                
                print(f"Debug: signups_config type: {type(signups_config)}")
                
                if signups_config:
                    target_year = current_year
                    
                    candidates_list = signups_config.get("candidates", [])
                    print(f"Debug: candidates_list type: {type(candidates_list)}, length: {len(candidates_list) if isinstance(candidates_list, list) else 'N/A'}")
                    
                    if isinstance(candidates_list, list):
                        for i, candidate in enumerate(candidates_list):
                            print(f"Debug: Processing candidate {i}: type: {type(candidate)}, content: {candidate}")
                            
                            try:
                                # Ensure candidate is a dictionary before accessing dict methods
                                if isinstance(candidate, dict):
                                    year = candidate.get("year")
                                    office = candidate.get("office")
                                    name = candidate.get("name")
                                    
                                    print(f"Debug: year: {year}, office: {office}, name: {name}")
                                    
                                    if (year == target_year and 
                                        office in ["President", "Vice President"] and
                                        name):
                                        candidate_names.append(name)
                                        print(f"Added primary campaign candidate: {name}")
                                else:
                                    print(f"Error: candidate is not a dict, it's {type(candidate)}: {candidate}")
                            except (KeyError, TypeError, AttributeError) as e:
                                print(f"Error processing candidate: {candidate}, error: {e}")
                                continue
                    else:
                        print(f"Error: candidates_list is not a list, it's {type(candidates_list)}: {candidates_list}")

            # Remove duplicates and filter by current input
            candidate_names = list(set(candidate_names))
            
            # Filter by what the user has typed
            if current:
                filtered_names = [name for name in candidate_names if current.lower() in name.lower()]
            else:
                filtered_names = candidate_names

            print(f"Final result - Phase: {current_phase}, Found {len(filtered_names)} candidates for autocomplete: {filtered_names[:5]}")
            
            return [app_commands.Choice(name=name, value=name) for name in filtered_names[:25]]
                    
        except Exception as e:
            print(f"Error in _get_presidential_candidate_choices: {e}")
            import traceback
            traceback.print_exc()
            return []

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
        name="pres_poll",
        description="Conduct an NPC poll for a presidential candidate (shows polling with 7% margin of error)"
    )
    @app_commands.describe(candidate_name="The presidential candidate to poll (leave blank to poll yourself)")
    async def pres_poll(self, interaction: discord.Interaction, candidate_name: Optional[str] = None):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Presidential polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")

        # If no candidate specified, check if user is a presidential candidate
        if not candidate_name:
            signups_col, candidate = self._get_user_presidential_candidate(interaction.guild.id, interaction.user.id)
            if not candidate:
                await interaction.response.send_message(
                    "❌ You must specify a presidential candidate name or be a registered presidential candidate yourself.",
                    ephemeral=True
                )
                return
            candidate_name = candidate.get('name')

        # Get the presidential candidate
        signups_col, candidate = self._get_presidential_candidate_by_name(interaction.guild.id, candidate_name)
        if not candidate or not isinstance(candidate, dict):
            await interaction.response.send_message(
                f"❌ Presidential candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Calculate actual polling percentage
        candidate_display_name = candidate.get('name')

        if current_phase == "General Campaign":
            # For general campaign, use presidential percentages
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, candidate["office"])
            actual_percentage = general_percentages.get(candidate_display_name, 50.0)
        else:
            # For primary campaign, calculate based on points relative to competition
            signups_col, signups_config = self._get_presidential_config(interaction.guild.id)
            if signups_config:
                current_year = time_config["current_rp_date"].year
                primary_competitors = [
                    c for c in signups_config.get("candidates", [])
                    if (c["office"] == candidate["office"] and
                        c["party"] == candidate["party"] and
                        c["year"] == current_year)
                ]

                if len(primary_competitors) == 1:
                    actual_percentage = 85.0  # Unopposed in primary
                else:
                    # Calculate relative position based on points
                    total_points = sum(c.get('points', 0) for c in primary_competitors)
                    if total_points == 0:
                        actual_percentage = 100.0 / len(primary_competitors)  # Even split
                    else:
                        candidate_points = candidate.get('points', 0)
                        actual_percentage = (candidate_points / total_points) * 100.0
                        # Ensure minimum viable percentage
                        actual_percentage = max(15.0, actual_percentage)
            else:
                actual_percentage = 50.0

        # Apply margin of error
        poll_result = self._calculate_poll_result(actual_percentage)

        # Generate random polling organization
        polling_orgs = [
            "Mason-Dixon Polling", "Quinnipiac University", "Marist Poll",
            "Suffolk University", "Emerson College", "Public Policy Polling",
            "SurveyUSA", "Ipsos/Reuters", "YouGov", "Rasmussen Reports",
            "CNN/SSRS", "Fox News Poll", "ABC News/Washington Post",
            "CBS News/YouGov", "NBC News/Wall Street Journal"
        ]

        polling_org = random.choice(polling_orgs)

        # Generate sample size and date
        sample_size = random.randint(800, 2000)
        days_ago = random.randint(1, 5)

        embed = discord.Embed(
            title="📊 Presidential Poll Results",
            description=f"Latest polling data for **{candidate_display_name}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎯 Presidential Candidate",
            value=f"**{candidate_display_name}** ({candidate['party']})\n"
                  f"Running for: {candidate['office']}\n"
                  f"Year: {candidate['year']}\n"
                  f"Phase: {current_phase}",
            inline=True
        )

        # Create visual progress bar
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        # Get party abbreviation
        party_abbrev = candidate['party'][0] if candidate['party'] else "I"

        progress_bar = create_progress_bar(poll_result)

        embed.add_field(
            name="📈 Poll Results",
            value=f"**{party_abbrev} - {candidate['party']}**\n"
                  f"{progress_bar} **{poll_result:.1f}%**\n"
                  f"Phase: {current_phase}",
            inline=True
        )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±7.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        # Add context based on phase
        if current_phase == "Primary Campaign":
            # Show primary competition context
            if signups_config:
                primary_competitors = [
                    c for c in signups_config.get("candidates", [])
                    if (c["office"] == candidate["office"] and
                        c["party"] == candidate["party"] and
                        c["year"] == current_year)
                ]

                if len(primary_competitors) > 1:
                    embed.add_field(
                        name="🔍 Primary Context",
                        value=f"Competing against {len(primary_competitors) - 1} other {candidate['party']} {candidate['office'].lower()} candidate{'s' if len(primary_competitors) > 2 else ''} in the primary",
                        inline=False
                    )
        else:
            # Show general election context
            general_percentages = self._calculate_general_election_percentages(interaction.guild.id, candidate["office"])
            if len(general_percentages) > 1:
                embed.add_field(
                    name="🔍 General Election Context",
                    value=f"Competing against {len(general_percentages) - 1} other {candidate['office'].lower()} candidate{'s' if len(general_percentages) > 2 else ''} in the general election",
                    inline=False
                )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    def _calculate_poll_result(self, actual_percentage: float, margin_of_error: float = 7.0) -> float:
        """Calculate poll result with margin of error"""
        # Apply random variation within margin of error
        variation = random.uniform(-margin_of_error, margin_of_error)
        poll_result = actual_percentage + variation

        # Ensure result stays within reasonable bounds (0-100%)
        poll_result = max(0.1, min(99.9, poll_result))

        return poll_result

    @pres_poll.autocomplete("candidate_name")
    async def candidate_autocomplete_pres_poll(self, interaction: discord.Interaction, current: str):
        return await self._get_presidential_candidate_choices(interaction, current)

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
        def calculate_poll_result_internal(actual_percentage: float, margin_of_error: float = 7.0) -> float:
            variation = random.uniform(-margin_of_error, margin_of_error)
            poll_result = actual_percentage + variation
            return max(0.1, min(99.9, poll_result))

        poll_results = {
            "Republican": calculate_poll_result_internal(republican_base),
            "Democrat": calculate_poll_result_internal(democrat_base),
            "Independent": calculate_poll_result_internal(independent_base)
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
        if not target_candidate or not isinstance(target_candidate, dict):
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
            updated_candidate_data = target_col.find_one({"guild_id": interaction.guild.id})
            updated_points = 0
            if updated_candidate_data and "candidates" in updated_candidate_data:
                for candidate_data in updated_candidate_data.get("candidates", []):
                    if candidate_data.get("user_id") == target_candidate["user_id"]:
                        updated_points = candidate_data.get("points", 0)
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
        filtered_states = [state for state in states if current.upper() in state.upper()]
        return [app_commands.Choice(name=state, value=state) for state in filtered_states[:25]]

async def setup(bot):
    await bot.add_cog(PresCampaignActions(bot))