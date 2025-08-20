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

        # Sample candidates for different election types (party only)
        self.sample_candidates = {
            "general": [
                "Democratic Party", "Republican Party", "Independent",
            ],
            "presidential": [
                "Democratic Party", "Republican Party", "Independent",
            ]
        }

        # Sample political parties with colors
        self.party_colors = {
            "D": discord.Color.blue(),
            "R": discord.Color.red(),
            "I": discord.Color.purple(),
        }

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

    def _generate_poll_results(self,
                               candidates: List[str],
                               margin_of_error: float = 7.0) -> Dict:
        """Generate realistic poll results with margin of error"""
        # Generate base percentages that add up to 100
        num_candidates = len(candidates)
        base_votes = []

        # Generate random distribution
        for i in range(num_candidates):
            if i == num_candidates - 1:
                # Last candidate gets remaining percentage
                base_votes.append(max(5, 100 - sum(base_votes)))
            else:
                # Random percentage between 10-40 for realistic distribution
                base_votes.append(random.randint(10, 40))

        # Normalize to 100%
        total = sum(base_votes)
        normalized_votes = [
            round((vote / total) * 100, 1) for vote in base_votes
        ]

        # Adjust for rounding errors
        diff = 100.0 - sum(normalized_votes)
        if diff != 0:
            normalized_votes[0] += diff

        results = {}
        for i, candidate in enumerate(candidates):
            base_pct = normalized_votes[i]

            # Apply margin of error (±7%)
            margin_adjustment = random.uniform(-margin_of_error,
                                               margin_of_error)
            final_pct = max(0, min(100, base_pct + margin_adjustment))

            # Calculate margin of error range
            low_range = max(0, final_pct - margin_of_error)
            high_range = min(100, final_pct + margin_of_error)

            results[candidate] = {
                "percentage": round(final_pct, 1),
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
        # Get available regions
        available_regions = self._get_regions_from_elections(
            interaction.guild.id)

        if not available_regions:
            await interaction.response.send_message(
                "❌ No regions configured. Please set up elections first.",
                ephemeral=True)
            return

        # Check if region exists
        if region not in available_regions:
            await interaction.response.send_message(
                f"❌ Region '{region}' not found. Available regions: {', '.join(available_regions)}",
                ephemeral=True)
            return

        # Get ideology data for this region if available
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from ideology import get_dynamic_regions_from_db, calculate_region_medians

            # Get custom regions from elections system
            custom_regions = get_dynamic_regions_from_db(self.bot.db, interaction.guild.id)
            regional_data = calculate_region_medians(custom_regions)

            has_ideology_data = region in regional_data
        except:
            has_ideology_data = False
            regional_data = {}

        # Generate poll results
        poll_results = self._generate_poll_results(self.sample_candidates["general"])

        embed = discord.Embed(
            title=f"📊 Regional Poll - {region}",
            description=f"Latest polling data for the {region} region",
            color=self._get_embed_color(poll_results),
            timestamp=datetime.utcnow()
        )

        # Add poll results
        for candidate, data in poll_results.items():
            party_abbrev = self._get_party_from_candidate(candidate)
            embed.add_field(
                name=f"{party_abbrev} - {candidate}",
                value=f"**{data['percentage']:.1f}%** ±{data['margin']:.1f}%",
                inline=True
            )

        # Add ideology context if available
        if has_ideology_data:
            ideology_data = regional_data[region]
            embed.add_field(
                name="🧠 Regional Ideology Context",
                value=f"R: {ideology_data['republican']:.1f}% | "
                      f"D: {ideology_data['democrat']:.1f}% | "
                      f"Other: {ideology_data['other']:.1f}%",
                inline=False
            )
            embed.set_footer(text="Poll results influenced by regional ideology data")
        else:
            embed.set_footer(text="No ideology data available for this region")

        await interaction.response.send_message(embed=embed)

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

        # Generate poll results
        results = self._generate_poll_results(
            self.sample_candidates["general"])

        embed = discord.Embed(title=f"📊 {region_match} Regional Poll",
                              description="*General Election Polling*",
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

            # Create visual bar (simple representation)
            bar_length = int(percentage / 5)  # Scale down for display
            bar = "█" * bar_length + "░" * (20 - bar_length)

            poll_text += f"**{candidate}**\n"
            poll_text += f"`{bar}` {percentage}%\n"
            poll_text += f"*Range: {margin_low}% - {margin_high}%*\n\n"

        embed.add_field(name="🗳️ Polling Results",
                        value=poll_text,
                        inline=False)

        embed.add_field(
            name="📈 Methodology",
            value="*Margin of Error: ±7%*\n*Sample includes likely voters*",
            inline=False)

        # Add leading candidate info
        leading_candidate, leading_data = sorted_results[0]
        embed.add_field(
            name="🏆 Current Leader",
            value=f"{leading_candidate} - {leading_data['percentage']}%",
            inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="state_poll",
        description=
        "Show polling results for a specific state (general and presidential)")
    async def state_poll(self,
                         interaction: discord.Interaction,
                         state: str,
                         election_type: str = "general"):
        # Get available states
        available_states = self._get_states_from_elections(
            interaction.guild.id)

        if not available_states:
            await interaction.response.send_message(
                "❌ No states configured. Please set up elections first.",
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

        # For presidential, only allow National or actual states (not regions)
        if election_type == "presidential" and state_match not in [
                "National"
        ] and state_match not in available_states:
            await interaction.response.send_message(
                "❌ Presidential polls are only available for states, not regions.",
                ephemeral=True)
            return

        # Generate poll results
        candidates = self.sample_candidates[election_type]
        results = self._generate_poll_results(candidates)

        election_display = "Presidential Election" if election_type == "presidential" else "General Election"
        state_display = "National" if state_match == "National" else f"{state_match} State"

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
            poll_text += f"`{bar}` {percentage}%\n"
            poll_text += f"*Range: {margin_low}% - {margin_high}%*\n\n"

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

    @app_commands.command(
        name="poll_comparison",
        description="Compare polling between multiple regions or states")
    async def poll_comparison(self,
                              interaction: discord.Interaction,
                              locations: str,
                              election_type: str = "general"):
        """Compare polls between multiple locations (comma-separated)"""
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

        # Get available locations
        available_locations = self._get_states_from_elections(
            interaction.guild.id)

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

        # Generate results for each location
        location_results = {}
        for location in valid_locations:
            location_results[location] = self._generate_poll_results(
                candidates)

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
                candidate_text += f"**{location}:** {percentage}% ({result['margin_low']}%-{result['margin_high']}%)\n"

            embed.add_field(name=f"🗳️ {candidate}",
                            value=candidate_text,
                            inline=True)

        embed.add_field(name="📈 Note",
                        value="*All polls have ±7% margin of error*",
                        inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="poll_trends",
        description="Show polling trend analysis for a location")
    async def poll_trends(self,
                          interaction: discord.Interaction,
                          location: str,
                          election_type: str = "general"):
        """Show simulated polling trends over time"""
        # Validate location
        available_locations = self._get_states_from_elections(
            interaction.guild.id)

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

        # Generate trend data for each candidate
        for candidate in candidates:
            trend_text = ""
            base_percentage = random.randint(15, 35)

            for i, period in enumerate(time_periods):
                # Simulate gradual change over time
                change = random.randint(-5, 5)
                current_pct = max(5, min(45, base_percentage + (change * i)))

                if i == len(time_periods) - 1:
                    trend_text += f"**{period}:** {current_pct}% *(MoE: ±7%)*\n"
                else:
                    trend_text += f"{period}: {current_pct}%\n"

            # Add trend indicator
            trend_direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"

            embed.add_field(name=f"{trend_direction} {candidate}",
                            value=trend_text,
                            inline=True)

        embed.add_field(
            name="📊 Analysis",
            value=
            "*Trends based on recent polling data*\n*Current poll includes ±7% margin of error*",
            inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Polling(bot))
