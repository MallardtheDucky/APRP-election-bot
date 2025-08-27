import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Presidential election state data
# Data shows Republican/Democrat/Other percentages for each state
# Numbers copied from STATE_DATA in ideology.py

PRESIDENTIAL_STATE_DATA = {
    "ALABAMA": {"republican": 57, "democrat": 32, "other": 11},
    "ALASKA": {"republican": 52, "democrat": 34, "other": 14},
    "ARIZONA": {"republican": 44, "democrat": 42, "other": 14},
    "ARKANSAS": {"republican": 52, "democrat": 39, "other": 9},
    "CALIFORNIA": {"republican": 36, "democrat": 56, "other": 8},
    "COLORADO": {"republican": 45, "democrat": 47, "other": 8},
    "CONNECTICUT": {"republican": 40, "democrat": 50, "other": 10},
    "DELAWARE": {"republican": 37, "democrat": 55, "other": 8},
    "DISTRICT OF COLUMBIA": {"republican": 12, "democrat": 78, "other": 10},
    "FLORIDA": {"republican": 48, "democrat": 43, "other": 9},
    "GEORGIA": {"republican": 47, "democrat": 44, "other": 9},
    "HAWAII": {"republican": 33, "democrat": 58, "other": 9},
    "IDAHO": {"republican": 60, "democrat": 29, "other": 11},
    "ILLINOIS": {"republican": 39, "democrat": 52, "other": 9},
    "INDIANA": {"republican": 53, "democrat": 38, "other": 9},
    "IOWA": {"republican": 47, "democrat": 44, "other": 9},
    "KANSAS": {"republican": 54, "democrat": 37, "other": 9},
    "KENTUCKY": {"republican": 56, "democrat": 35, "other": 9},
    "LOUISIANA": {"republican": 52, "democrat": 39, "other": 9},
    "MAINE": {"republican": 42, "democrat": 49, "other": 9},
    "MARYLAND": {"republican": 34, "democrat": 57, "other": 9},
    "MASSACHUSETTS": {"republican": 32, "democrat": 59, "other": 9},
    "MICHIGAN": {"republican": 44, "democrat": 47, "other": 9},
    "MINNESOTA": {"republican": 42, "democrat": 49, "other": 9},
    "MISSISSIPPI": {"republican": 55, "democrat": 36, "other": 9},
    "MISSOURI": {"republican": 51, "democrat": 40, "other": 9},
    "MONTANA": {"republican": 54, "democrat": 37, "other": 9},
    "NEBRASKA": {"republican": 56, "democrat": 35, "other": 9},
    "NEVADA": {"republican": 43, "democrat": 46, "other": 11},
    "NEW HAMPSHIRE": {"republican": 46, "democrat": 45, "other": 9},
    "NEW JERSEY": {"republican": 38, "democrat": 53, "other": 9},
    "NEW MEXICO": {"republican": 40, "democrat": 48, "other": 12},
    "NEW YORK": {"republican": 35, "democrat": 56, "other": 9},
    "NORTH CAROLINA": {"republican": 47, "democrat": 44, "other": 9},
    "NORTH DAKOTA": {"republican": 62, "democrat": 29, "other": 9},
    "OHIO": {"republican": 46, "democrat": 45, "other": 9},
    "OKLAHOMA": {"republican": 59, "democrat": 32, "other": 9},
    "OREGON": {"republican": 38, "democrat": 51, "other": 11},
    "PENNSYLVANIA": {"republican": 44, "democrat": 47, "other": 9},
    "RHODE ISLAND": {"republican": 33, "democrat": 58, "other": 9},
    "SOUTH CAROLINA": {"republican": 51, "democrat": 40, "other": 9},
    "SOUTH DAKOTA": {"republican": 58, "democrat": 33, "other": 9},
    "TENNESSEE": {"republican": 55, "democrat": 36, "other": 9},
    "TEXAS": {"republican": 48, "democrat": 43, "other": 9},
    "UTAH": {"republican": 58, "democrat": 33, "other": 9},
    "VERMONT": {"republican": 35, "democrat": 56, "other": 9},
    "VIRGINIA": {"republican": 44, "democrat": 47, "other": 9},
    "WASHINGTON": {"republican": 37, "democrat": 53, "other": 10},
    "WEST VIRGINIA": {"republican": 64, "democrat": 27, "other": 9},
    "WISCONSIN": {"republican": 45, "democrat": 46, "other": 9},
    "WYOMING": {"republican": 66, "democrat": 25, "other": 9}
}

def _calculate_ideology_bonus_standalone(candidate_ideology: dict, state_ideology_data: dict) -> int:
    """Calculate ideology bonus for a candidate in a state, standalone for testing."""
    if not candidate_ideology or not state_ideology_data:
        return 0

    # Simplified bonus calculation: more ideological alignment = higher bonus
    bonus = 0
    if "conservative" in candidate_ideology and "conservative" in state_ideology_data:
        bonus += min(candidate_ideology["conservative"], state_ideology_data["conservative"])
    if "liberal" in candidate_ideology and "liberal" in state_ideology_data:
        bonus += min(candidate_ideology["liberal"], state_ideology_data["liberal"])
    if "moderate" in candidate_ideology and "moderate" in state_ideology_data:
        bonus += min(candidate_ideology["moderate"], state_ideology_data["moderate"])

    # Add a small bonus for general alignment if specific ideological matches are low
    if bonus < 5:
        if candidate_ideology.get("leaning") and state_ideology_data.get("leaning"):
            if candidate_ideology["leaning"] == state_ideology_data["leaning"]:
                bonus += 2

    return bonus

def get_state_percentages(state_name: str, candidate_ideologies=None) -> dict:
        """Get the Republican/Democrat/Other percentages for a specific state with ideology bonuses"""
        state_key = state_name.upper()
        base_data = PRESIDENTIAL_STATE_DATA.get(state_key, {"republican": 0, "democrat": 0, "other": 0})

        if not candidate_ideologies:
            return base_data

        # Import ideology data
        try:
            from cogs.ideology import STATE_DATA
            state_ideology_data = STATE_DATA.get(state_key, {})
        except ImportError:
            return base_data

        # Calculate bonuses for each party
        result = base_data.copy()

        for party, candidate_ideology in candidate_ideologies.items():
            bonus = _calculate_ideology_bonus_standalone(candidate_ideology, state_ideology_data)

            # Apply bonus to appropriate party
            if party.lower() in ["democrats", "democratic party"]:
                result["democrat"] += bonus
            elif party.lower() in ["republicans", "republican party"]:
                result["republican"] += bonus
            else:
                result["other"] += bonus

        # Normalize to ensure percentages don't exceed realistic bounds
        total = sum(result.values())
        if total > 120:  # If total exceeds 120%, normalize proportionally
            factor = 120 / total
            for key in result:
                result[key] *= factor

        return result

def get_all_states() -> list:
    """Get a list of all available states"""
    return list(PRESIDENTIAL_STATE_DATA.keys())

def print_state_data():
    """Print all state data in a formatted way"""
    print("STATE LEANS\tRepublican\tDemocrat\tOther")
    for state, data in PRESIDENTIAL_STATE_DATA.items():
        print(f"{state}\t{data['republican']}\t{data['democrat']}\t{data['other']}")

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class PresidentialWinners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_presidential_winners_config(self, guild_id: int):
        """Get or create presidential winners configuration for a guild"""
        col = self.bot.db["presidential_winners"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "winners": {}
            }
            col.insert_one(config)
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration for a guild"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    @commands.Cog.listener()
    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: int, current_year: int):
        """Handle phase changes and process presidential primary winners"""
        if old_phase == "Primary Campaign" and new_phase == "Primary Election":
            # Process presidential signups for primary elections
            # Handle year logic consistently with regular elections
            if current_year % 2 == 1:  # Odd year (1999)
                signup_year = current_year
            else:  # Even year (2000)
                signup_year = current_year - 1

            await self._process_presidential_primary_winners(guild_id, signup_year)

        elif old_phase == "Primary Election" and new_phase == "General Campaign":
            # Reset presidential primary winners for general campaign
            await self._reset_presidential_candidates_for_general_campaign(guild_id, current_year)

    async def _process_presidential_primary_winners(self, guild_id: int, signup_year: int):
        """Process presidential primary winners from signups to winners"""
        # Get presidential signups
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

        if not pres_signups_config:
            return

        # Get candidates from signup year
        candidates = [c for c in pres_signups_config.get("candidates", []) if c["year"] == signup_year]

        if not candidates:
            return

        # Get or create presidential winners config
        pres_winners_col, pres_winners_config = self._get_presidential_winners_config(guild_id)

        # Group candidates by party for primary winners
        party_candidates = {}
        for candidate in candidates:
            party = candidate["party"]
            if party not in party_candidates:
                party_candidates[party] = []
            party_candidates[party].append(candidate)

        # Determine winner for each party (highest points)
        winners = {}
        presidential_primary_winners = []
        for party, party_cands in party_candidates.items():
            if len(party_cands) == 1:
                winner = party_cands[0]
            else:
                winner = max(party_cands, key=lambda x: x.get("points", 0))
            winners[party] = winner["name"]
            presidential_primary_winners.append(winner)

        # Update presidential winners with election year (signup_year + 1)
        election_year = signup_year + 1
        pres_winners_config["winners"] = winners
        pres_winners_config["election_year"] = election_year

        pres_winners_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"winners": winners, "election_year": election_year}}
        )

        # Transfer presidential primary winners to all_winners system
        await self._transfer_to_all_winners(guild_id, presidential_primary_winners, election_year)

        print(f"Processed {len(winners)} presidential primary winners for guild {guild_id}, election year {election_year}")

    @app_commands.command(
        name="show_primary_winners",
        description="Show current presidential primary winners"
    )
    async def show_primary_winners(
        self,
        interaction: discord.Interaction,
        year: int = None
    ):
        """Show the current primary winners"""
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)

        winners = winners_config.get("winners", {})

        if not winners:
            await interaction.response.send_message(
                "📊 No primary winners declared yet.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🏆 Presidential Primary Winners",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Show winners by party
        party_colors = {
            "Democrats": "🔵",
            "Republican": "🔴", 
            "Others": "🟣"
        }

        for party, winner_name in winners.items():
            emoji = party_colors.get(party, "⚪")
            embed.add_field(
                name=f"{emoji} {party}",
                value=f"**{winner_name}**",
                inline=True
            )

        if len(winners) < 3:
            embed.add_field(
                name="📋 Status",
                value="Some primaries are still ongoing...",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="view_general_election_candidates",
        description="View the final candidates for the general election"
    )
    async def view_general_election_candidates(
        self,
        interaction: discord.Interaction,
        year: int = None
    ):
        """Show candidates in the general election"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        target_year = year if year else current_year

        if current_phase not in ["General Campaign", "General Election"]:
            await interaction.response.send_message(
                "❌ This command can only be used during General Campaign or General Election phases.",
                ephemeral=True
            )
            return

        # Get primary winners who advanced to general election
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
        
        if not winners_config:
            await interaction.response.send_message("❌ No presidential winners data found.", ephemeral=True)
            return

        # For general election, look for primary winners from the signup year
        primary_year = target_year - 1 if target_year % 2 == 0 else target_year
        
        general_candidates = []
        
        # Get major party nominees from primary winners
        party_winners = winners_config.get("winners", {})
        if party_winners:
            # Find full candidate data
            pres_signups_col = self.bot.db["presidential_signups"]
            pres_signups_config = pres_signups_col.find_one({"guild_id": interaction.guild.id})
            
            if pres_signups_config:
                for party, winner_name in party_winners.items():
                    for candidate in pres_signups_config.get("candidates", []):
                        if (candidate["name"] == winner_name and 
                            candidate["year"] == primary_year and 
                            candidate["office"] == "President"):
                            general_candidates.append(candidate)
                            break

        # Also check for independents who qualified through delegates
        delegates_col = self.bot.db["delegates_config"]
        delegates_config = delegates_col.find_one({"guild_id": interaction.guild.id})
        
        if delegates_config:
            delegate_threshold = delegates_config.get("delegate_threshold", 100)
            
            # Get independent candidates who reached delegate threshold
            for candidate in delegates_config.get("candidates", []):
                if (candidate.get("year") == primary_year and 
                    candidate.get("party", "").lower() not in ["democrats", "democratic party", "republicans", "republican party"] and
                    candidate.get("delegates", 0) >= delegate_threshold):
                    
                    # Find full candidate data
                    if pres_signups_config:
                        for pres_candidate in pres_signups_config.get("candidates", []):
                            if (pres_candidate["name"] == candidate["name"] and 
                                pres_candidate["year"] == primary_year and 
                                pres_candidate["office"] == "President"):
                                general_candidates.append(pres_candidate)
                                break

        if not general_candidates:
            await interaction.response.send_message(
                f"❌ No general election candidates found for {target_year}.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🗳️ {target_year} General Election Candidates",
            description=f"Final candidates advancing to the general election",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Calculate general election percentages
        general_percentages = self._calculate_general_election_percentages(interaction.guild.id, "President")

        for candidate in general_candidates:
            vp_name = candidate.get("vp_candidate", "No VP selected")
            polling_percentage = general_percentages.get(candidate["name"], 0.0)

            # Party color
            party_emoji = "🔴" if "republican" in candidate["party"].lower() else "🔵" if "democrat" in candidate["party"].lower() else "🟣"

            ticket_info = f"{party_emoji} **Party:** {candidate['party']}\n"
            ticket_info += f"**Running Mate:** {vp_name}\n"
            ticket_info += f"**Current Polling:** {polling_percentage:.1f}%\n\n"
            ticket_info += f"**Ideology:** {candidate['ideology']} ({candidate['axis']})\n"
            ticket_info += f"**Economic:** {candidate['economic']}\n"
            ticket_info += f"**Social:** {candidate['social']}\n"
            ticket_info += f"**Government:** {candidate['government']}"

            embed.add_field(
                name=f"🇺🇸 {candidate['name']}",
                value=ticket_info,
                inline=False
            )

        embed.add_field(
            name="📊 Election Status",
            value=f"**Phase:** {current_phase}\n**Year:** {target_year}\n**Candidates:** {len(general_candidates)}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    def _calculate_general_election_percentages(self, guild_id: int, office: str):
        """Calculate general election percentages using state-by-state analysis with complete proportional redistribution"""
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Get presidential winners (general election candidates)
        winners_col, winners_config = self._get_presidential_winners_config(guild_id)

        if not winners_config:
            return {}

        # For general campaign, look for primary winners from the previous year if we're in an even year
        # Or current year if odd year
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year

        winners_data = winners_config.get("winners", [])
        candidates = []

        # Handle both list and dict formats for winners
        if isinstance(winners_data, list):
            # New list format
            candidates = [
                w for w in winners_data 
                if (isinstance(w, dict) and 
                    w.get("primary_winner", False) and 
                    w.get("year") == primary_year and 
                    w.get("office") == office)
            ]
        elif isinstance(winners_data, dict):
            # Old dict format: {party: candidate_name}
            # Need to get full candidate data from presidential signups
            signups_col = self.bot.db["presidential_signups"]
            signups_config = signups_col.find_one({"guild_id": guild_id})
            if signups_config:
                election_year = winners_config.get("election_year", primary_year + 1)
                signup_year = election_year - 1 if election_year % 2 == 0 else election_year

                candidates_list = signups_config.get("candidates", [])
                if isinstance(candidates_list, list):
                    for candidate in candidates_list:
                        if (isinstance(candidate, dict) and
                            candidate.get("year") == signup_year and
                            candidate.get("office") == office):
                            # Check if this candidate won their primary
                            candidate_name = candidate.get("name")
                            for party, winner_name in winners_data.items():
                                if isinstance(winner_name, str) and winner_name.lower() == candidate_name.lower():
                                    # Create a general campaign candidate object
                                    general_candidate = candidate.copy()
                                    general_candidate["primary_winner"] = True
                                    general_candidate["total_points"] = general_candidate.get("points", 0.0)
                                    general_candidate["state_points"] = general_candidate.get("state_points", {})
                                    candidates.append(general_candidate)

        if not candidates:
            return {}

        # State population weights for national polling calculation
        STATE_POPULATION_WEIGHTS = {
            "CALIFORNIA": 12.07, "TEXAS": 8.16, "NEW YORK": 6.27, "FLORIDA": 6.09,
            "PENNSYLVANIA": 4.11, "ILLINOIS": 4.15, "OHIO": 3.73, "MICHIGAN": 3.19,
            "GEORGIA": 3.14, "NORTH CAROLINA": 3.10, "NEW JERSEY": 2.85, "VIRGINIA": 2.59,
            "WASHINGTON": 2.18, "MASSACHUSETTS": 2.12, "INDIANA": 2.10, "ARIZONA": 2.07,
            "TENNESSEE": 2.06, "MISSOURI": 1.94, "MARYLAND": 1.87, "WISCONSIN": 1.84,
            "MINNESOTA": 1.72, "COLORADO": 1.63, "ALABAMA": 1.55, "SOUTH CAROLINA": 1.50,
            "LOUISIANA": 1.47, "KENTUCKY": 1.41, "OREGON": 1.24, "OKLAHOMA": 1.22,
            "CONNECTICUT": 1.16, "IOWA": 0.99, "ARKANSAS": 0.95, "UTAH": 0.90,
            "NEVADA": 0.87, "NEW MEXICO": 0.67, "NEBRASKA": 0.59, "WEST VIRGINIA": 0.60,
            "NEW HAMPSHIRE": 0.43, "MAINE": 0.43, "HAWAII": 0.44, "IDAHO": 0.51,
            "MONTANA": 0.32, "RHODE ISLAND": 0.34, "DELAWARE": 0.29, "SOUTH DAKOTA": 0.26,
            "NORTH DAKOTA": 0.22, "ALASKA": 0.23, "DISTRICT OF COLUMBIA": 0.20,
            "VERMONT": 0.20, "WYOMING": 0.18, "KANSAS": 0.94, "MISSISSIPPI": 0.96
        }

        # Calculate state-by-state percentages for each candidate
        candidate_percentages = {}

        for candidate in candidates:
            candidate_name = candidate.get("name")
            candidate_party = candidate.get("party", "").lower()
            state_points = candidate.get("state_points", {})

            # Determine party alignment for baseline calculations
            if "republican" in candidate_party:
                party_alignment = "republican"
            elif "democrat" in candidate_party:
                party_alignment = "democrat"
            else:
                party_alignment = "other"

            total_weighted_percentage = 0.0
            total_population_weight = 0.0

            # Calculate weighted polling across all states
            for state_name, population_weight in STATE_POPULATION_WEIGHTS.items():
                # Get base party support for this state
                state_data = PRESIDENTIAL_STATE_DATA.get(state_name, {
                    "republican": 33.0, "democrat": 33.0, "other": 34.0
                })

                # Start with party baseline
                base_support = state_data.get(party_alignment, 33.0)

                # Add campaign points gained in this state
                campaign_boost = state_points.get(state_name, 0.0)

                # Calculate state polling (base + campaign effects)
                state_polling = base_support + campaign_boost

                # Apply realistic bounds (15% minimum, 85% maximum per state)
                state_polling = max(15.0, min(85.0, state_polling))

                # Weight by population
                weighted_contribution = (state_polling / 100.0) * population_weight
                total_weighted_percentage += weighted_contribution
                total_population_weight += population_weight

            # Calculate final national percentage for this candidate
            if total_population_weight > 0:
                national_percentage = (total_weighted_percentage / total_population_weight) * 100.0
            else:
                national_percentage = 50.0

            # Ensure reasonable bounds for national polling
            candidate_percentages[candidate_name] = max(20.0, min(80.0, national_percentage))

        # Normalize percentages to sum to 100%
        total_percentage = sum(candidate_percentages.values())
        if total_percentage > 0:
            for candidate_name in candidate_percentages:
                candidate_percentages[candidate_name] = (candidate_percentages[candidate_name] / total_percentage) * 100.0

        return candidate_percentages

    def _get_presidential_candidates(self, guild_id: int, party: str, year: int):
        """Get presidential candidates for a specific party and year"""
        col = self.bot.db["presidential_signups"]
        config = col.find_one({"guild_id": guild_id})

        if not config:
            return []

        candidates = []
        for candidate in config.get("candidates", []):
            if (candidate.get("party", "").lower() == party.lower() and 
                candidate.get("year", 0) == year):
                candidates.append(candidate)

        return candidates

    def _apply_post_election_ideology_shift(self, guild_id: int):
        """Apply permanent ideology shift after presidential election ends"""
        global PRESIDENTIAL_STATE_DATA

        try:
            # Import STATE_DATA from ideology module
            from cogs.ideology import STATE_DATA

            # Track changes for logging
            changes_made = []

            # Update PRESIDENTIAL_STATE_DATA with values from STATE_DATA
            for state_name, state_ideology_data in STATE_DATA.items():
                if state_name in PRESIDENTIAL_STATE_DATA:
                    old_data = PRESIDENTIAL_STATE_DATA[state_name].copy()

                    # Update with new ideology-based percentages
                    PRESIDENTIAL_STATE_DATA[state_name] = {
                        "republican": state_ideology_data.get("republican", old_data["republican"]),
                        "democrat": state_ideology_data.get("democrat", old_data["democrat"]),
                        "other": state_ideology_data.get("other", old_data["other"])
                    }

                    # Check if values actually changed
                    new_data = PRESIDENTIAL_STATE_DATA[state_name]
                    if (old_data["republican"] != new_data["republican"] or 
                        old_data["democrat"] != new_data["democrat"] or 
                        old_data["other"] != new_data["other"]):
                        changes_made.append({
                            "state": state_name,
                            "old": old_data,
                            "new": new_data
                        })

            # Log the ideology shift in database for tracking
            ideology_shift_col = self.bot.db["ideology_shifts"]
            shift_record = {
                "guild_id": guild_id,
                "shift_type": "post_presidential_election",
                "timestamp": datetime.utcnow(),
                "changes": changes_made,
                "total_states_affected": len(changes_made)
            }
            ideology_shift_col.insert_one(shift_record)

            return changes_made

        except ImportError:
            print("Warning: Could not import STATE_DATA from ideology module")
            return []
        except Exception as e:
            print(f"Error applying post-election ideology shift: {e}")
            return []

    def _reset_all_candidate_points(self, guild_id: int):
        """Reset all presidential candidate points to 0 for new election cycle"""
        try:
            # Reset presidential signups points
            pres_signups_col = self.bot.db["presidential_signups"]
            pres_signups_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"candidates.$[].points": 0, "candidates.$[].total_points": 0}}
            )

            # Reset presidential winners points
            pres_winners_col = self.bot.db["presidential_winners"]
            pres_winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners.$[].total_points": 0, "winners.$[].state_points": {}}}
            )

            # Reset delegates points if they exist
            delegates_col = self.bot.db["delegates_config"]
            delegates_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"candidates.$[].points": 0}}
            )

            return True

        except Exception as e:
            print(f"Error resetting candidate points: {e}")
            return False

    def _reset_presidential_candidates_for_general_campaign(self, guild_id: int, current_year: int):
        """Reset presidential candidates for the general campaign phase."""
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

        if pres_signups_config:
            # Filter out candidates from the previous election year and reset points
            updated_candidates = []
            for candidate in pres_signups_config.get("candidates", []):
                if candidate.get("year", 0) == current_year:  # Keep candidates from the current year
                    candidate["points"] = 0
                    candidate["total_points"] = 0
                updated_candidates.append(candidate)

            pres_signups_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"candidates": updated_candidates}}
            )

        # Also reset presidential candidates in all_winners system
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})

        if winners_config:
            updated_count = 0
            for i, winner in enumerate(winners_config.get("winners", [])):
                if (winner.get("year") == current_year and 
                    winner.get("office") == "President" and
                    winner.get("primary_winner", False) and
                    winner.get("phase") != "General Campaign"):

                    winners_config["winners"][i]["points"] = 0.0
                    winners_config["winners"][i]["stamina"] = 200  # Presidential candidates get higher stamina
                    winners_config["winners"][i]["phase"] = "General Campaign"
                    updated_count += 1

            if updated_count > 0:
                winners_col.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"winners": winners_config["winners"]}}
                )
                print(f"Reset {updated_count} presidential winners in all_winners system for general campaign")

        print(f"Reset presidential candidates for general campaign in guild {guild_id}, year {current_year}")

    @app_commands.command(
        name="admin_process_pres_primaries",
        description="Manually process presidential primary winners (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_process_pres_primaries(
        self,
        interaction: discord.Interaction,
        signup_year: int = None,
        confirm: bool = False
    ):
        """Manually process presidential primary winners from signups"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        # If signup_year is not provided, determine it based on the current year.
        # If current_year is even (e.g., 2000), signups were in the previous odd year (1999).
        # If current_year is odd (e.g., 2001), signups were in the previous even year (2000).
        # This assumes elections happen every two years, and signups precede the election year.
        target_signup_year = signup_year if signup_year else current_year - 1

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will process presidential signups from {target_signup_year} and declare primary winners for {current_year}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        await self._process_presidential_primary_winners(interaction.guild.id, target_signup_year)

        await interaction.response.send_message(
            f"✅ Successfully processed presidential primary winners from {target_signup_year} signups!",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_transition_pres_candidates",
        description="Manually transition presidential candidates between years (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_transition_pres_candidates(
        self,
        interaction: discord.Interaction,
        from_year: int,
        to_year: int,
        confirm: bool = False
    ):
        """Manually transition presidential candidates between years"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will transition presidential candidates from {from_year} to {to_year}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Get presidential signups from from_year
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": interaction.guild.id})

        if not pres_signups_config:
            await interaction.response.send_message("❌ No presidential signups found.", ephemeral=True)
            return

        candidates = [c for c in pres_signups_config.get("candidates", []) if c["year"] == from_year]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for {from_year}.",
                ephemeral=True
            )
            return

        # Process them as primary winners for to_year
        await self._process_presidential_primary_winners(interaction.guild.id, from_year)

        await interaction.response.send_message(
            f"✅ Successfully transitioned {len(candidates)} presidential candidates from {from_year} to {to_year}!",
            ephemeral=True
        )

    async def _transfer_to_all_winners(self, guild_id: int, presidential_winners: list, election_year: int):
        """Transfer presidential primary winners to the all_winners system"""
        # Get or create all_winners configuration
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})
        if not winners_config:
            winners_config = {
                "guild_id": guild_id,
                "winners": []
            }
            winners_col.insert_one(winners_config)

        # Create winner entries for all_winners system
        all_winners_entries = []
        for candidate in presidential_winners:
            # Create presidential seat_id based on party
            party_seat_mapping = {
                "Democrats": "US-PRES-DEM",
                "Democratic Party": "US-PRES-DEM", 
                "Republicans": "US-PRES-REP",
                "Republican Party": "US-PRES-REP",
                "Others": "US-PRES-IND",
                "Independent": "US-PRES-IND"
            }

            seat_id = party_seat_mapping.get(candidate["party"], "US-PRES-OTHER")

            # Calculate baseline percentage based on party
            baseline_percentages = {
                "Democrats": 45.0,
                "Democratic Party": 45.0,
                "Republicans": 45.0, 
                "Republican Party": 45.0,
                "Others": 10.0,
                "Independent": 10.0
            }
            baseline_percentage = baseline_percentages.get(candidate["party"], 10.0)

            winner_entry = {
                "year": election_year,
                "user_id": candidate["user_id"],
                "office": "President",
                "state": "United States",
                "seat_id": seat_id,
                "candidate": candidate["name"],
                "party": candidate["party"],
                "points": 0.0,  # Reset for general campaign
                "baseline_percentage": baseline_percentage,
                "votes": 0,
                "corruption": candidate.get("corruption", 0),
                "final_score": 0,
                "stamina": candidate.get("stamina", 200),  # Presidential candidates get higher stamina
                "winner": False,
                "phase": "Primary Winner",
                "primary_winner": True,
                "general_winner": False,
                "created_date": datetime.utcnow()
            }
            all_winners_entries.append(winner_entry)

        # Add presidential winners to all_winners system
        if all_winners_entries:
            if "winners" not in winners_config:
                winners_config["winners"] = []
            winners_config["winners"].extend(all_winners_entries)

            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )

            print(f"Transferred {len(all_winners_entries)} presidential primary winners to all_winners system for guild {guild_id}")


    @app_commands.command(
        name="admin_view_all_winners",
        description="View all winners across different offices and years (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_all_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        office: str = None,
        state: str = None
    ):
        """Admin command to view all winners"""
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

        if not winners_config or not winners_config.get("winners"):
            await interaction.response.send_message("No winners found in the system.", ephemeral=True)
            return

        filtered_winners = winners_config.get("winners", [])

        if year:
            filtered_winners = [w for w in filtered_winners if w.get("year") == year]
        if office:
            filtered_winners = [w for w in filtered_winners if w.get("office", "").lower() == office.lower()]
        if state:
            filtered_winners = [w for w in filtered_winners if w.get("state", "").lower() == state.lower()]

        if not filtered_winners:
            await interaction.response.send_message("No winners found matching your criteria.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏆 All Election Winners",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        winner_details = []
        for winner in filtered_winners:
            winner_details.append(
                f"**{winner.get('year')} {winner.get('state')} {winner.get('office')}**\n"
                f"  - Candidate: {winner.get('candidate')}\n"
                f"  - Party: {winner.get('party')}\n"
                f"  - Status: {winner.get('phase')}"
            )

        # Split into multiple embeds if too long
        max_fields = 10
        for i in range(0, len(winner_details), max_fields):
            chunk = winner_details[i:i + max_fields]
            for detail in chunk:
                embed.add_field(name="\u200b", value=detail, inline=False)
            
            if i + max_fields < len(winner_details):
                await interaction.response.send_message(embed=embed)
                embed = discord.Embed(title="🏆 All Election Winners (Continued)", color=discord.Color.blue(), timestamp=datetime.utcnow())
            else:
                await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_set_state_base",
        description="Set the base party percentages for a state (Admin only)"
    )
    @app_commands.describe(
        state="State name (e.g., California, Texas)",
        republican="Republican base percentage (0-100)",
        democrat="Democrat base percentage (0-100)", 
        other="Other/Independent base percentage (0-100)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_state_base(
        self,
        interaction: discord.Interaction,
        state: str,
        republican: float,
        democrat: float,
        other: float
    ):
        """Set the base party percentages for a state"""
        global PRESIDENTIAL_STATE_DATA

        state_upper = state.upper()

        # Validate state exists
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            available_states = list(PRESIDENTIAL_STATE_DATA.keys())[:10]  # Show first 10 for brevity
            await interaction.response.send_message(
                f"❌ State '{state}' not found. Available states include: {', '.join(available_states)}...",
                ephemeral=True
            )
            return

        # Validate percentages
        if not (0 <= republican <= 100 and 0 <= democrat <= 100 and 0 <= other <= 100):
            await interaction.response.send_message(
                "❌ All percentages must be between 0 and 100.",
                ephemeral=True
            )
            return

        # Store old values for display
        old_values = PRESIDENTIAL_STATE_DATA[state_upper].copy()
        total = republican + democrat + other

        # Update the state data
        PRESIDENTIAL_STATE_DATA[state_upper]["republican"] = round(republican, 1)
        PRESIDENTIAL_STATE_DATA[state_upper]["democrat"] = round(democrat, 1)
        PRESIDENTIAL_STATE_DATA[state_upper]["other"] = round(other, 1)

        # Create response embed
        embed = discord.Embed(
            title="📊 State Base Percentages Updated",
            description=f"**{state_upper}** base party percentages have been updated.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Previous Values",
            value=f"Republican: {old_values['republican']:.1f}%\n"
                  f"Democrat: {old_values['democrat']:.1f}%\n"
                  f"Other: {old_values['other']:.1f}%\n"
                  f"Total: {sum(old_values.values()):.1f}%",
            inline=True
        )

        embed.add_field(
            name="New Values", 
            value=f"Republican: {republican:.1f}%\n"
                  f"Democrat: {democrat:.1f}%\n"
                  f"Other: {other:.1f}%\n"
                  f"Total: {total:.1f}%",
            inline=True
        )

        embed.add_field(
            name="💡 Note",
            value="These changes affect presidential election calculations and state polling data.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_set_state_base.autocomplete("state")
    async def state_autocomplete_admin_set_base(self, interaction: discord.Interaction, current: str):
        """Autocomplete for state parameter in admin_set_state_base"""
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

async def setup(bot):
    await bot.add_cog(PresidentialWinners(bot))

# Main execution for testing
if __name__ == "__main__":
    print_state_data()