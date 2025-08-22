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
            bonus = self._calculate_ideology_bonus(candidate_ideology, state_ideology_data)

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

    @app_commands.command(
        name="admin_view_pres_state_data",
        description="View PRESIDENTIAL_STATE_DATA as a formatted table (Admin only)"
    )
    @app_commands.describe(
        state_name="View specific state data (optional - shows all if not specified)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_pres_state_data(
        self,
        interaction: discord.Interaction,
        state_name: str = None
    ):
        """View PRESIDENTIAL_STATE_DATA for a specific state or all states in table format"""
        if state_name:
            state_name = state_name.upper()
            if state_name not in PRESIDENTIAL_STATE_DATA:
                await interaction.response.send_message(
                    f"❌ State '{state_name}' not found in PRESIDENTIAL_STATE_DATA.",
                    ephemeral=True
                )
                return

            data = PRESIDENTIAL_STATE_DATA[state_name]
            embed = discord.Embed(
                title=f"📊 Presidential State Data: {state_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="🗳️ Party Support Percentages",
                value=f"**Republican:** {data['republican']}%\n"
                      f"**Democrat:** {data['democrat']}%\n"
                      f"**Other:** {data['other']}%",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show all states in a formatted table
            embed = discord.Embed(
                title="📊 All Presidential State Data",
                description="Republican/Democrat/Other percentages by state",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Create table header
            table_header = "```\nSTATE                    REP  DEM  OTH\n" + "="*40 + "\n"
            table_rows = []
            
            for state, data in sorted(PRESIDENTIAL_STATE_DATA.items()):
                # Format state name to be consistent width
                state_formatted = state[:20].ljust(20)
                rep = str(data['republican']).rjust(3)
                dem = str(data['democrat']).rjust(3)
                other = str(data['other']).rjust(3)
                
                table_rows.append(f"{state_formatted} {rep}  {dem}  {other}")

            # Split into chunks to avoid Discord message limits
            chunk_size = 25
            for i in range(0, len(table_rows), chunk_size):
                chunk = table_rows[i:i + chunk_size]
                field_name = f"States ({i+1}-{min(i+chunk_size, len(table_rows))})"
                
                table_content = table_header + "\n".join(chunk) + "\n```"
                
                embed.add_field(
                    name=field_name,
                    value=table_content,
                    inline=False
                )

            embed.add_field(
                name="📈 Summary",
                value=f"**Total States:** {len(PRESIDENTIAL_STATE_DATA)}",
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

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
        name="admin_update_winner",
        description="Manually update a primary winner (Admin only)"
    )
    @app_commands.describe(
        party="Party (Democrats, Republican, or Others)",
        winner_name="Name of the winning candidate"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_update_winner(
        self,
        interaction: discord.Interaction,
        party: str,
        winner_name: str
    ):
        """Manually set a primary winner"""
        valid_parties = ["Democrats", "Republican", "Others"]
        
        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return
            
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
        
        # Update winner
        winners_config["winners"][party] = winner_name
        
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )
        
        await interaction.response.send_message(
            f"✅ **{winner_name}** has been set as the {party} primary winner.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_reset_winners",
        description="Reset all primary winners (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_winners(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """Reset all primary winners"""
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will reset all primary winners.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return
            
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
        
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": {}}}
        )
        
        # Also reset delegate primary winners
        delegates_col = self.bot.db["delegates_config"]
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"primary_winners": {}}}
        )
        
        await interaction.response.send_message(
            "✅ All primary winners have been reset.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_view_state_percentages",
        description="View state-by-state voting percentages for general election (Admin only)"
    )
    @app_commands.describe(
        state_name="View specific state data (optional - shows all if not specified)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_state_percentages(
        self,
        interaction: discord.Interaction,
        state_name: str = None
    ):
        """View how primary winners would perform in each state based on PRESIDENTIAL_STATE_DATA"""
        winners_col, winners_config = self._get_presidential_winners_config(interaction.guild.id)
        winners = winners_config.get("winners", {})
        
        if not winners:
            await interaction.response.send_message(
                "❌ No primary winners declared yet.",
                ephemeral=True
            )
            return
            
        if state_name:
            state_name = state_name.upper()
            if state_name not in PRESIDENTIAL_STATE_DATA:
                await interaction.response.send_message(
                    f"❌ State '{state_name}' not found in PRESIDENTIAL_STATE_DATA.",
                    ephemeral=True
                )
                return

            # Get candidate ideologies for bonus calculation
            candidate_ideologies = {}
            signups_col = self.bot.db["presidential_signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            if signups_config:
                for party, winner_name in winners.items():
                    for candidate in signups_config.get("candidates", []):
                        if candidate.get("name") == winner_name and candidate.get("office") == "President":
                            candidate_ideologies[party] = {
                                "ideology": candidate.get("ideology"),
                                "economic": candidate.get("economic"),
                                "social": candidate.get("social"),
                                "government": candidate.get("government"),
                                "axis": candidate.get("axis")
                            }
                            break

            data = get_state_percentages(state_name, candidate_ideologies)
            embed = discord.Embed(
                title=f"📊 {state_name} General Election Projection",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Map winners to percentages (with ideology bonuses applied)
            projection_text = ""
            if "Democrats" in winners:
                projection_text += f"**{winners['Democrats']} (D):** {data['democrat']:.1f}%\n"
            if "Republican" in winners:
                projection_text += f"**{winners['Republican']} (R):** {data['republican']:.1f}%\n"
            if "Others" in winners:
                projection_text += f"**{winners['Others']} (I):** {data['other']:.1f}%\n"

            embed.add_field(
                name="🗳️ Projected Results",
                value=projection_text,
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show all states summary
            embed = discord.Embed(
                title="📊 National General Election Projection",
                description="Based on current primary winners and state data",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Get candidate ideologies for bonus calculation
            candidate_ideologies = {}
            signups_col = self.bot.db["presidential_signups"]
            signups_config = signups_col.find_one({"guild_id": interaction.guild.id})

            if signups_config:
                for party, winner_name in winners.items():
                    for candidate in signups_config.get("candidates", []):
                        if candidate.get("name") == winner_name and candidate.get("office") == "President":
                            candidate_ideologies[party] = {
                                "ideology": candidate.get("ideology"),
                                "economic": candidate.get("economic"),
                                "social": candidate.get("social"),
                                "government": candidate.get("government"),
                                "axis": candidate.get("axis")
                            }
                            break

            # Calculate national averages with ideology bonuses
            total_dem = 0
            total_rep = 0 
            total_other = 0
            state_count = len(PRESIDENTIAL_STATE_DATA)

            for state_name in PRESIDENTIAL_STATE_DATA.keys():
                state_data = get_state_percentages(state_name, candidate_ideologies)
                total_dem += state_data['democrat']
                total_rep += state_data['republican']
                total_other += state_data['other']

            avg_dem = total_dem / state_count
            avg_rep = total_rep / state_count
            avg_other = total_other / state_count

            projection_text = ""
            if "Democrats" in winners:
                projection_text += f"**{winners['Democrats']} (D):** {avg_dem:.1f}% avg\n"
            if "Republican" in winners:
                projection_text += f"**{winners['Republican']} (R):** {avg_rep:.1f}% avg\n"
            if "Others" in winners:
                projection_text += f"**{winners['Others']} (I):** {avg_other:.1f}% avg\n"

            embed.add_field(
                name="📈 National Averages",
                value=projection_text,
                inline=False
            )

            embed.add_field(
                name="📍 Coverage",
                value=f"Based on {state_count} states",
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

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

    def _calculate_ideology_bonus(self, candidate_ideology, state_data):
        """Calculate ideology-based bonus (1-3%) when candidate ideology aligns with state"""
        bonus = 0.0

        if not candidate_ideology or not state_data:
            return bonus

        # Check ideology alignment
        if candidate_ideology.get("ideology") == state_data.get("ideology"):
            bonus += 1.0

        if candidate_ideology.get("economic") == state_data.get("economic"):
            bonus += 0.5

        if candidate_ideology.get("social") == state_data.get("social"):
            bonus += 0.5

        if candidate_ideology.get("government") == state_data.get("government"):
            bonus += 0.5

        if candidate_ideology.get("axis") == state_data.get("axis"):
            bonus += 0.5

        # Cap bonus at 3%
        return min(bonus, 3.0)

async def setup(bot):
    await bot.add_cog(PresidentialWinners(bot))

# Main execution for testing
if __name__ == "__main__":
    print_state_data()