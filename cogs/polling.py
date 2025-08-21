import discord
from discord.ext import commands
from discord import app_commands
import random
from typing import Dict, List, Optional
from datetime import datetime


class Polling(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        print("Polling cog loaded successfully")

        # Default sample candidates (will be overridden by database parties)
        self.sample_candidates = {
            "general": [
                "Democratic Party", "Republican Party", "Independent",
            ],
            "presidential": [
                "Democratic Party", "Republican Party", "Independent",
            ]
        }

        # Default party colors (will be overridden by database parties)
        self.party_colors = {
            "D": discord.Color.blue(),
            "R": discord.Color.red(),
            "I": discord.Color.purple(),
        }

    def _get_parties_from_database(self, guild_id: int) -> Dict:
        """Get parties from database"""
        parties_col = self.bot.db["parties_config"]
        parties_config = parties_col.find_one({"guild_id": guild_id})
        
        if not parties_config:
            return {
                "parties": ["Democratic Party", "Republican Party", "Independent"],
                "colors": {
                    "Democratic Party": discord.Color.blue(),
                    "Republican Party": discord.Color.red(),
                    "Independent": discord.Color.purple()
                }
            }
        
        parties = [party["name"] for party in parties_config["parties"]]
        colors = {
            party["name"]: discord.Color(party["color"]) 
            for party in parties_config["parties"]
        }
        
        return {"parties": parties, "colors": colors}

    def _get_regions_from_elections(self, guild_id: int) -> List[str]:
        """Get available regions from the elections configuration"""
        elections_col = self.bot.db["elections_config"]
        elections_config = elections_col.find_one({"guild_id": guild_id})

        if not elections_config:
            return []

        # Get regions from region_mappings if available, otherwise fall back to seats
        if elections_config.get("region_mappings"):
            return sorted(list(elections_config["region_mappings"].keys()))
        elif elections_config.get("seats"):
            regions = set()
            for seat in elections_config["seats"]:
                if seat["state"] != "National":  # Exclude national seats for region polls
                    regions.add(seat["state"])
            return sorted(list(regions))
        else:
            return []

    def _get_states_from_elections(self, guild_id: int) -> List[str]:
        """Get available states from the elections configuration (including National for presidential)"""
        elections_col = self.bot.db["elections_config"]
        elections_config = elections_col.find_one({"guild_id": guild_id})

        if not elections_config or not elections_config.get("seats"):
            return []

        states = set()
        for seat in elections_config["seats"]:
            states.add(seat["state"])

        return sorted(list(states))

    def _get_us_states(self) -> List[str]:
        """Return a list of all U.S. states"""
        return [
            "Alabama", "Alaska", "Arizona", "Arkansas", "California",
            "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
            "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
            "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
            "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
            "Nebraska", "Nevada", "New Hampshire", "New Jersey",
            "New Mexico", "New York", "North Carolina", "North Dakota",
            "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
            "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
            "Vermont", "Virginia", "Washington", "West Virginia",
            "Wisconsin", "Wyoming", "District of Columbia"
        ]

    def _generate_poll_results(self,
                               candidates: List[str],
                               margin_of_error: float = 7.0,
                               region_name: str = None,
                               state_name: str = None) -> Dict:
        """Generate poll results based on ideology data that sum to exactly 100%"""

        # Try to get ideology data
        base_percentages = None

        if region_name:
            # Get regional ideology data by summing all states in the region
            try:
                # Import ideology data - handle different import scenarios
                try:
                    from ideology import STATE_DATA, REGIONS
                except ImportError:
                    import sys
                    import os
                    sys.path.insert(0, os.path.dirname(__file__))
                    from ideology import STATE_DATA, REGIONS

                if region_name in REGIONS:
                    states_in_region = REGIONS[region_name]

                    # Sum up all the ideological percentages from constituent states
                    total_republican = 0
                    total_democrat = 0
                    total_other = 0
                    valid_states = 0

                    for state in states_in_region:
                        state_key = state.upper()
                        if state_key in STATE_DATA:
                            state_data = STATE_DATA[state_key]
                            total_republican += state_data["republican"]
                            total_democrat += state_data["democrat"] 
                            total_other += state_data["other"]
                            valid_states += 1

                    if valid_states > 0:
                        # Calculate the regional totals
                        regional_total = total_republican + total_democrat + total_other

                        # Normalize to percentages that add up to exactly 100%
                        base_percentages = {
                            "Republican Party": (total_republican / regional_total) * 100,
                            "Democratic Party": (total_democrat / regional_total) * 100,
                            "Independent": (total_other / regional_total) * 100
                        }

                        print(f"✅ IDEOLOGY DATA LOADED - Regional sum for {region_name} ({valid_states} states): R={base_percentages['Republican Party']:.1f}%, D={base_percentages['Democratic Party']:.1f}%, I={base_percentages['Independent']:.1f}%")

            except Exception as e:
                print(f"❌ IDEOLOGY IMPORT FAILED - Could not load regional ideology data: {e}")
                print(f"Exception type: {type(e).__name__}")
                import traceback
                traceback.print_exc()

        elif state_name:
            # Get state ideology data
            try:
                # Import ideology data - handle different import scenarios
                try:
                    from ideology import STATE_DATA
                except ImportError:
                    import sys
                    import os
                    sys.path.insert(0, os.path.dirname(__file__))
                    from ideology import STATE_DATA

                state_key = state_name.upper()
                if state_key in STATE_DATA:
                    ideology_data = STATE_DATA[state_key]
                    base_percentages = {
                        "Republican Party": ideology_data["republican"],
                        "Democratic Party": ideology_data["democrat"],
                        "Independent": ideology_data["other"]
                    }
            except Exception as e:
                print(f"Could not load state ideology data: {e}")

        # If we have ideology data, use it as base but add random variation within margin of error
        if base_percentages:
            results = {}
            poll_percentages = []

            # Apply random variation within margin of error to each candidate
            for candidate in candidates:
                if candidate in base_percentages:
                    base_pct = base_percentages[candidate]

                    # Add random variation within margin of error
                    variation = random.uniform(-margin_of_error, margin_of_error)
                    poll_pct = base_pct + variation

                    # Keep within reasonable bounds
                    poll_pct = max(1.0, min(95.0, poll_pct))
                    poll_percentages.append(poll_pct)
                else:
                    # For unmapped candidates, give them small random percentage
                    poll_percentages.append(random.uniform(1.0, 5.0))

            # Normalize so all percentages sum to 100%
            total = sum(poll_percentages)
            normalized_percentages = [(pct / total) * 100 for pct in poll_percentages]

            # Build results with the varied percentages
            for i, candidate in enumerate(candidates):
                final_pct = round(normalized_percentages[i], 1)

                # Calculate the theoretical margin of error range
                low_range = max(0, final_pct - margin_of_error)
                high_range = min(100, final_pct + margin_of_error)

                results[candidate] = {
                    "percentage": final_pct,
                    "margin_low": round(low_range, 1),
                    "margin_high": round(high_range, 1)
                }

            return results
        else:
            # Fallback to random generation if no ideology data available
            num_candidates = len(candidates)
            base_votes = []

            # Generate random distribution that sums to 100%
            for i in range(num_candidates):
                if i == num_candidates - 1:
                    # Last candidate gets remaining percentage
                    base_votes.append(max(5, 100 - sum(base_votes)))
                else:
                    # Random percentage between 10-40 for realistic distribution
                    base_votes.append(random.randint(10, 40))

            # Normalize to exactly 100%
            total = sum(base_votes)
            normalized_votes = [(vote / total) * 100 for vote in base_votes]

            results = {}
            for i, candidate in enumerate(candidates):
                final_pct = round(normalized_votes[i], 1)

                # Calculate margin of error range
                low_range = max(0, final_pct - margin_of_error)
                high_range = min(100, final_pct + margin_of_error)

                results[candidate] = {
                    "percentage": final_pct,
                    "margin_low": round(low_range, 1),
                    "margin_high": round(high_range, 1)
                }

            return results

    def _get_party_from_candidate(self, candidate: str) -> str:
        """Extract party abbreviation from party name"""
        party_abbreviations = {
            "Democratic Party": "D",
            "Republican Party": "R",
            "Independent": "I",
        }
        return party_abbreviations.get(candidate, "I")

    def _get_embed_color(self, results: Dict) -> discord.Color:
        """Get embed color based on leading candidate's party"""
        leading_candidate = max(results.items(),
                                key=lambda x: x[1]["percentage"])
        party = self._get_party_from_candidate(leading_candidate[0])
        return self.party_colors.get(party, discord.Color.blue())

    @app_commands.command(
        name="region_poll",
        description="Show polling results for a specific region")
    async def region_poll(self, interaction: discord.Interaction, region: str):
        try:
            # Get available regions
            available_regions = self._get_regions_from_elections(
                interaction.guild.id)

            if not available_regions:
                await interaction.response.send_message(
                    "❌ No regions configured. Please set up elections first.",
                    ephemeral=True)
                return

            # Check if region exists
            region_match = None
            for available_region in available_regions:
                if available_region.lower() == region.lower():
                    region_match = available_region
                    break

            if not region_match:
                available_list = ", ".join(available_regions)
                await interaction.response.send_message(
                    f"❌ Region '{region}' not found.\n**Available regions:** {available_list}",
                    ephemeral=True)
                return

            # Get ideology data for this region if available
            try:
                # Import ideology data - handle different import scenarios
                try:
                    from ideology import STATE_DATA, REGIONS
                except ImportError:
                    import sys
                    import os
                    sys.path.insert(0, os.path.dirname(__file__))
                    from ideology import STATE_DATA, REGIONS

                has_ideology_data = region_match in REGIONS
                regional_data = {}

                if has_ideology_data:
                    states_in_region = REGIONS[region_match]
                    total_republican = 0
                    total_democrat = 0
                    total_other = 0
                    valid_states = 0

                    for state in states_in_region:
                        state_key = state.upper()
                        if state_key in STATE_DATA:
                            state_data = STATE_DATA[state_key]
                            total_republican += state_data["republican"]
                            total_democrat += state_data["democrat"] 
                            total_other += state_data["other"]
                            valid_states += 1

                    if valid_states > 0:
                        regional_total = total_republican + total_democrat + total_other
                        regional_data[region_match] = {
                            "republican": (total_republican / regional_total) * 100,
                            "democrat": (total_democrat / regional_total) * 100,
                            "other": (total_other / regional_total) * 100,
                            "states_count": valid_states
                        }

            except Exception:
                has_ideology_data = False
                regional_data = {}

            # Generate poll results based on regional ideology data
            poll_results = self._generate_poll_results(
                self.sample_candidates["general"], 
                region_name=region_match
            )

            embed = discord.Embed(
                title=f"📊 Regional Poll - {region_match}",
                description=f"Latest polling data for the {region_match} region",
                color=self._get_embed_color(poll_results),
                timestamp=datetime.utcnow())

            # Sort candidates by percentage for better display
            sorted_results = sorted(poll_results.items(),
                                    key=lambda x: x[1]["percentage"],
                                    reverse=True)

            poll_text = ""
            for candidate, data in sorted_results:
                party = self._get_party_from_candidate(candidate)
                percentage = data["percentage"]
                margin_low = data["margin_low"]
                margin_high = data["margin_high"]

                # Create visual bar (20 characters total, each represents 5%)
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)

                poll_text += f"**{party} - {candidate}**\n"
                poll_text += f"`{bar}` {percentage}%\n\n"

            embed.add_field(name="🗳️ Polling Results",
                            value=poll_text,
                            inline=False)

            embed.add_field(
                name="📈 Methodology",
                value="*Margin of Error: ±7%*\n*Sample includes likely voters*",
                inline=False)

            # Set footer based on whether ideology data was used
            if has_ideology_data and region_match in regional_data:
                embed.set_footer(text="Poll results based on sum of ideological leanings from all constituent states")
            else:
                embed.set_footer(text="Using simulated polling data - no regional ideology data available")

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating poll: {str(e)}", ephemeral=True)


    @app_commands.command(
        name="state_poll",
        description=
        "Show polling results for a specific state (general and presidential)")
    async def state_poll(self,
                         interaction: discord.Interaction,
                         state: str,
                         election_type: str = "general"):
        try:
            # Get available states
            available_states = self._get_us_states()

            if not available_states:
                await interaction.response.send_message(
                    "❌ No U.S. states available. This command requires U.S. state data.",
                    ephemeral=True)
                return

            # Check if state exists
            state_match = None
            for available_state in available_states:
                if available_state.lower() == state.lower():
                    state_match = available_state
                    break

            if not state_match:
                available_list = ", ".join(available_states)
                await interaction.response.send_message(
                    f"❌ State '{state}' not found.\n**Available states:** {available_list}",
                    ephemeral=True)
                return

            # Validate election type
            if election_type.lower() not in ["general", "presidential"]:
                await interaction.response.send_message(
                    "❌ Election type must be either 'general' or 'presidential'",
                    ephemeral=True)
                return

            election_type = election_type.lower()

            # For presidential, only allow actual states (not regions or National)
            if election_type == "presidential" and state_match == "National":
                await interaction.response.send_message(
                    "❌ Presidential polls are only available for specific states, not 'National'.",
                    ephemeral=True)
                return

            # Generate poll results based on state ideology data
            candidates = self.sample_candidates[election_type]
            results = self._generate_poll_results(
                candidates, 
                state_name=state_match
            )

            election_display = "Presidential Election" if election_type == "presidential" else "General Election"
            state_display = f"{state_match} State"

            embed = discord.Embed(title=f"📊 {state_display} Poll",
                                  description=f"*{election_display} Polling*",
                                  color=self._get_embed_color(results),
                                  timestamp=datetime.utcnow())

            # Sort candidates by percentage
            sorted_results = sorted(results.items(),
                                    key=lambda x: x[1]["percentage"],
                                    reverse=True)

            poll_text = ""
            for candidate, data in sorted_results:
                party = self._get_party_from_candidate(candidate)
                percentage = data["percentage"]
                margin_low = data["margin_low"]
                margin_high = data["margin_high"]

                # Create visual bar
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)

                poll_text += f"**{candidate}**\n"
                poll_text += f"`{bar}` {percentage}%\n\n"

            embed.add_field(name="🗳️ Polling Results",
                            value=poll_text,
                            inline=False)

            embed.add_field(
                name="📈 Methodology",
                value="*Margin of Error: ±7%*\n*Sample includes likely voters*",
                inline=False)

            # Add additional info for presidential vs general
            if election_type == "presidential":
                leading_candidate, leading_data = sorted_results[0]
                embed.add_field(
                    name="🏆 Electoral Projection",
                    value=
                    f"{leading_candidate} leads with {leading_data['percentage']}%\n*Based on current polling*",
                    inline=True)
            else:
                # Show multiple races for general election
                embed.add_field(
                    name="📋 Election Info",
                    value=
                    f"General election polling for {state_match}\n*Multiple races tracked*",
                    inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating poll: {str(e)}", ephemeral=True)


    @app_commands.command(
        name="poll_comparison",
        description="Compare polling between multiple regions or states")
    async def poll_comparison(self,
                              interaction: discord.Interaction,
                              locations: str,
                              election_type: str = "general"):
        """Compare polls between multiple locations (comma-separated)"""
        try:
            # Parse locations
            location_list = [loc.strip() for loc in locations.split(",")]

            if len(location_list) < 2:
                await interaction.response.send_message(
                    "❌ Please provide at least 2 locations separated by commas (e.g., 'Columbia, Cambridge, Austin')",
                    ephemeral=True)
                return

            if len(location_list) > 6:
                await interaction.response.send_message(
                    "❌ Maximum 6 locations can be compared at once",
                    ephemeral=True)
                return

            # Get available locations - use U.S. states for state polling
            available_locations = self._get_us_states()

            # Validate all locations exist
            valid_locations = []
            for location in location_list:
                location_match = None
                for available in available_locations:
                    if available.lower() == location.lower():
                        location_match = available
                        break
                if location_match:
                    valid_locations.append(location_match)
                else:
                    await interaction.response.send_message(
                        f"❌ Location '{location}' not found.", ephemeral=True)
                    return

            # Validate election type
            if election_type.lower() not in ["general", "presidential"]:
                await interaction.response.send_message(
                    "❌ Election type must be either 'general' or 'presidential'",
                    ephemeral=True)
                return

            election_type = election_type.lower()
            candidates = self.sample_candidates[election_type]

            # Generate results for each location using state ideology data
            location_results = {}
            for location in valid_locations:
                location_results[location] = self._generate_poll_results(
                    candidates, 
                    state_name=location
                )

            election_display = "Presidential" if election_type == "presidential" else "General"

            embed = discord.Embed(
                title=f"📊 {election_display} Poll Comparison",
                description=f"*Comparing {len(valid_locations)} locations*",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow())

            # For each candidate, show their performance across locations
            for candidate in candidates:
                candidate_text = ""
                for location in valid_locations:
                    result = location_results[location][candidate]
                    percentage = result["percentage"]
                    candidate_text += f"**{location}:** {percentage}%\n"

                embed.add_field(name=f"🗳️ {candidate}",
                                value=candidate_text,
                                inline=True)

            embed.add_field(name="📈 Note",
                            value="*All polls have ±7% margin of error*",
                            inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating poll comparison: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="poll_trends",
        description="Show polling trend analysis for a location")
    async def poll_trends(self,
                          interaction: discord.Interaction,
                          location: str,
                          election_type: str = "general"):
        """Show simulated polling trends over time"""
        try:
            # Validate location - use U.S. states for state polling
            available_locations = self._get_us_states()

            location_match = None
            for available in available_locations:
                if available.lower() == location.lower():
                    location_match = available
                    break

            if not location_match:
                available_list = ", ".join(available_locations)
                await interaction.response.send_message(
                    f"❌ Location '{location}' not found.\n**Available:** {available_list}",
                    ephemeral=True)
                return

            # Validate election type
            if election_type.lower() not in ["general", "presidential"]:
                await interaction.response.send_message(
                    "❌ Election type must be either 'general' or 'presidential'",
                    ephemeral=True)
                return

            election_type = election_type.lower()
            candidates = self.sample_candidates[election_type]

            # Generate "historical" polling data (simulated)
            time_periods = [
                "3 months ago", "2 months ago", "1 month ago", "Current"
            ]

            embed = discord.Embed(
                title=f"📈 Polling Trends - {location_match}",
                description=f"*{election_type.title()} Election Trends*",
                color=discord.Color.green(),
                timestamp=datetime.utcnow())

            # Get current poll results based on ideology data to use as base
            current_results = self._generate_poll_results(
                candidates, 
                state_name=location_match
            )

            # Generate trend data for each candidate
            for candidate in candidates:
                trend_text = ""
                current_pct = current_results[candidate]["percentage"]
                base_percentage = current_pct

                for i, period in enumerate(time_periods):
                    # Simulate gradual change over time from historical base
                    if i == len(time_periods) - 1:
                        # Use current actual poll result for "Current"
                        trend_text += f"**{period}:** {current_pct}%\n"
                    else:
                        # Simulate historical variation around the base
                        variation = random.randint(-8, 8)  # Historical variation
                        historical_pct = max(5, min(50, base_percentage + variation))
                        trend_text += f"{period}: {historical_pct}%\n"

                # Determine trend direction based on difference from base
                change = current_pct - base_percentage
                trend_direction = "📈" if change > 2 else "📉" if change < -2 else "➡️"

                embed.add_field(name=f"{trend_direction} {candidate}",
                                value=trend_text,
                                inline=True)

            embed.add_field(
                name="📊 Analysis",
                value=
                "*Trends based on recent polling data*\n*Current poll includes ±7% margin of error*",
                inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating poll trends: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Polling(bot))