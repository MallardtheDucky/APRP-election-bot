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
    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Handle phase changes and process presidential primary winners"""
        if old_phase == "Primary Campaign" and new_phase == "Primary Election":
            # Transition from primary campaign to primary election in the same year
            # Process signups from the previous year (1999) for the current election year (2000)
            signup_year = current_year - 1  # 1999 signups for 2000 election
            await self._process_presidential_primary_winners(guild_id, signup_year)

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
        for party, party_cands in party_candidates.items():
            if len(party_cands) == 1:
                winner = party_cands[0]
            else:
                winner = max(party_cands, key=lambda x: x.get("points", 0))
            winners[party] = winner["name"]

        # Update presidential winners with election year (signup_year + 1)
        election_year = signup_year + 1
        pres_winners_config["winners"] = winners
        pres_winners_config["election_year"] = election_year

        pres_winners_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"winners": winners, "election_year": election_year}}
        )

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


async def setup(bot):
    await bot.add_cog(PresidentialWinners(bot))

# Main execution for testing
if __name__ == "__main__":
    print_state_data()