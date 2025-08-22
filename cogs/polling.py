import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
from typing import Optional, List

class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Polling cog loaded successfully")

    def _get_signups_config(self, guild_id: int):
        """Get signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_winners_config(self, guild_id: int):
        """Get winners configuration"""
        col = self.bot.db["winners"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_user_candidate(self, guild_id: int, user_id: int):
        """Get user's candidate information based on current phase"""
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
        """Get candidate by name based on current phase"""
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

        # Special case: if only one candidate, they get 100%
        if len(seat_candidates) == 1:
            candidate_name = seat_candidates[0].get('candidate', seat_candidates[0].get('name', ''))
            return {candidate_name: 100.0}

        # Determine baseline percentages based on number of candidates and parties
        num_candidates = len(seat_candidates)
        parties = set(candidate["party"] for candidate in seat_candidates)
        num_parties = len(parties)

        # Count major parties (Democrat and Republican)
        major_parties = {"Democrat", "Republican"}
        major_parties_present = len([p for p in parties if p in major_parties])

        # Set baseline percentages based on number of parties
        baseline_percentages = {}

        if num_parties == 2:
            # Two parties: 50-50 split
            for candidate in seat_candidates:
                baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 50.0
        elif num_parties == 3:
            # Three parties: 40-40-20 (if Dem+Rep+other) or equal split
            if major_parties_present == 2:
                for candidate in seat_candidates:
                    if candidate["party"] in major_parties:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                    else:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 20.0
            else:
                # Equal split if not standard Dem-Rep-other
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 100.0 / 3
        elif num_parties == 4:
            # Four parties: 40-40-10-10 (if Dem+Rep+two others) or equal split
            if major_parties_present == 2:
                for candidate in seat_candidates:
                    if candidate["party"] in major_parties:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 40.0
                    else:
                        baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 10.0
            else:
                # Equal split if not standard setup
                for candidate in seat_candidates:
                    baseline_percentages[candidate.get('candidate', candidate.get('name', ''))] = 25.0
        else:
            # 5+ parties: prioritize taking from other/independents
            if major_parties_present == 2:
                # Democrat + Republican + multiple others: 40-40 for major, split remainder among others
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

        # Apply zero-sum redistribution
        final_percentages = {}

        # Calculate total campaign points across all candidates in this seat
        total_campaign_points = sum(candidate.get('points', 0.0) for candidate in seat_candidates)

        # If no campaign points exist, use baseline percentages
        if total_campaign_points == 0:
            final_percentages = baseline_percentages.copy()
        else:
            # Calculate the adjustment factor - how much total percentage change from campaign points
            # Each campaign point = 1% change potential, but we need to redistribute
            for candidate in seat_candidates:
                candidate_name = candidate.get('candidate', candidate.get('name', ''))
                baseline = baseline_percentages[candidate_name]
                candidate_points = candidate.get('points', 0.0)

                # Start with baseline percentage
                percentage = baseline

                # Add this candidate's campaign points as direct percentage gains
                percentage += candidate_points

                # Subtract a proportional share of OTHER candidates' gains
                # Each candidate loses percentage proportional to their baseline when others gain
                other_candidates_points = total_campaign_points - candidate_points
                if other_candidates_points > 0:
                    # Calculate proportional loss based on baseline share
                    total_baseline = sum(baseline_percentages.values())
                    proportional_loss = (baseline / total_baseline) * other_candidates_points
                    percentage -= proportional_loss

                # Ensure minimum percentage and store
                final_percentages[candidate_name] = max(0.1, percentage)

        # Normalize to exactly 100%
        total = sum(final_percentages.values())
        if total > 0:
            for name in final_percentages:
                final_percentages[name] = (final_percentages[name] / total) * 100.0

        return final_percentages

    def _calculate_poll_result(self, actual_percentage: float, margin_of_error: float = 7.0) -> float:
        """Calculate poll result with margin of error"""
        # Apply random variation within margin of error
        variation = random.uniform(-margin_of_error, margin_of_error)
        poll_result = actual_percentage + variation

        # Ensure result stays within reasonable bounds (0-100%)
        poll_result = max(0.1, min(99.9, poll_result))

        return poll_result

    @app_commands.command(
        name="poll",
        description="Conduct an NPC poll for a specific candidate (shows polling with 7% margin of error)"
    )
    @app_commands.describe(candidate_name="The candidate to poll (leave blank to poll yourself)")
    async def poll(self, interaction: discord.Interaction, candidate_name: Optional[str] = None):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")

        # If no candidate specified, check if user is a candidate
        if not candidate_name:
            signups_col, candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)
            if not candidate:
                await interaction.response.send_message(
                    "❌ You must specify a candidate name or be a registered candidate yourself.",
                    ephemeral=True
                )
                return
            candidate_name = candidate.get('candidate') or candidate.get('name')

        # Get the candidate
        signups_col, candidate = self._get_candidate_by_name(interaction.guild.id, candidate_name)
        if not candidate:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found.",
                ephemeral=True
            )
            return

        # Calculate actual polling percentage
        candidate_display_name = candidate.get('candidate') or candidate.get('name')

        if current_phase == "General Campaign":
            # For general campaign, use zero-sum percentages
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, candidate["seat_id"])
            actual_percentage = zero_sum_percentages.get(candidate_display_name, 50.0)
        else:
            # For primary campaign, calculate based on points relative to competition
            # Get all candidates for same seat and party
            if current_phase == "Primary Campaign":
                signups_col, signups_config = self._get_signups_config(interaction.guild.id)
                if signups_config:
                    current_year = time_config["current_rp_date"].year
                    seat_party_candidates = [
                        c for c in signups_config["candidates"]
                        if (c["seat_id"] == candidate["seat_id"] and 
                            c["party"] == candidate["party"] and 
                            c["year"] == current_year)
                    ]

                    if len(seat_party_candidates) == 1:
                        actual_percentage = 85.0  # Unopposed in primary
                    else:
                        # Calculate relative position based on points
                        total_points = sum(c.get('points', 0) for c in seat_party_candidates)
                        if total_points == 0:
                            actual_percentage = 100.0 / len(seat_party_candidates)  # Even split
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            # Ensure minimum viable percentage
                            actual_percentage = max(15.0, actual_percentage)
                else:
                    actual_percentage = 50.0
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
        sample_size = random.randint(400, 1200)
        days_ago = random.randint(1, 5)

        embed = discord.Embed(
            title="📊 NPC Poll Results",
            description=f"Latest polling data for **{candidate_display_name}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎯 Candidate",
            value=f"**{candidate_display_name}** ({candidate['party']})\n"
                  f"Running for: {candidate['seat_id']}\n"
                  f"Office: {candidate['office']}\n"
                  f"Region: {candidate.get('region') or candidate.get('state', 'Unknown')}",
            inline=True
        )

        embed.add_field(
            name="📈 Poll Results",
            value=f"**Support: {poll_result:.1f}%**\n"
                  f"Phase: {current_phase}\n"
                  f"Campaign Points: {candidate.get('points', 0):.2f}",
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
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)
            if signups_config:
                current_year = time_config["current_rp_date"].year
                primary_competitors = [
                    c for c in signups_config["candidates"]
                    if (c["seat_id"] == candidate["seat_id"] and 
                        c["party"] == candidate["party"] and 
                        c["year"] == current_year and
                        c["name"] != candidate_display_name)
                ]

                if primary_competitors:
                    embed.add_field(
                        name="🔍 Primary Context",
                        value=f"Competing against {len(primary_competitors)} other {candidate['party']} candidate{'s' if len(primary_competitors) > 1 else ''} in the primary",
                        inline=False
                    )
        else:
            # Show general election context
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, candidate["seat_id"])
            if len(zero_sum_percentages) > 1:
                embed.add_field(
                    name="🔍 General Election Context",
                    value=f"Competing against {len(zero_sum_percentages) - 1} other candidate{'s' if len(zero_sum_percentages) > 2 else ''} in the general election",
                    inline=False
                )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="state_poll",
        description="Conduct an NPC poll for all candidates in a specific state, broken down by ideology."
    )
    @app_commands.describe(state="The state to poll (e.g., 'California', 'NY')")
    async def state_poll(self, interaction: discord.Interaction, state: str):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # Get all candidates in the specified state
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)
        if not signups_config:
            await interaction.response.send_message(
                "❌ No candidate data found.",
                ephemeral=True
            )
            return

        state_candidates = [
            c for c in signups_config["candidates"]
            if c["state"].lower() == state.lower() and c["year"] == current_year
        ]

        if not state_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for state '{state}' in {current_year}.",
                ephemeral=True
            )
            return

        # Group candidates by party and ideology
        ideology_data = {
            "Democrat": {"liberal": [], "moderate": [], "conservative": []},
            "Republican": {"liberal": [], "moderate": [], "conservative": []},
            "Independent": {"liberal": [], "moderate": [], "conservative": []}
        }

        for candidate in state_candidates:
            party = candidate.get("party")
            ideology = candidate.get("ideology")
            
            if party in ideology_data and ideology in ideology_data[party]:
                ideology_data[party][ideology].append(candidate)

        # Calculate poll results for each ideology group
        poll_results_by_ideology = {}

        for party, ideologies in ideology_data.items():
            for ideology, candidates_in_group in ideologies.items():
                if not candidates_in_group:
                    continue

                group_key = f"{party} ({ideology})"
                
                if current_phase == "General Campaign":
                    # For general campaign, we need to consider their seat and then use zero-sum
                    # This is more complex as a state can have multiple seats.
                    # For simplicity here, let's aggregate by state and then try to infer.
                    # A more robust implementation would poll per seat.
                    
                    # For state-level polling by ideology, we'll approximate based on overall party strength and ideology distribution.
                    # This is a simplification; ideally, we'd poll for each seat in the state.
                    
                    # Let's assign a base percentage and then a variation.
                    # Base percentages could be influenced by party strength in the state.
                    
                    # A simplified approach: assign a base percentage to each party/ideology combination
                    # and then introduce variation.
                    
                    # Example base percentages (can be adjusted):
                    # Corrected base percentages
                    base_percentages = {
                        "Democrat (liberal)": 40,
                        "Democrat (moderate)": 30,
                        "Democrat (conservative)": 10,
                        "Republican (liberal)": 5,
                        "Republican (moderate)": 30,
                        "Republican (conservative)": 40,
                        "Independent (liberal)": 10,
                        "Independent (moderate)": 20,
                        "Independent (conservative)": 15
                        }
                    
                    actual_percentage = base_percentages.get(group_key, 20) # Default if not found
                    poll_result = self._calculate_poll_result(actual_percentage)
                    poll_results_by_ideology[group_key] = poll_result

                else: # Primary Campaign
                    # In primaries, poll within party and ideology.
                    # Calculate relative strength based on campaign points within this ideological group.
                    total_points = sum(c.get('points', 0) for c in candidates_in_group)
                    
                    if total_points == 0:
                        actual_percentage = 100.0 / len(candidates_in_group)
                    else:
                        # For simplicity, we'll take the average points of the group and poll that.
                        # A more detailed approach would poll each candidate in the group.
                        avg_points = total_points / len(candidates_in_group)
                        actual_percentage = max(15.0, avg_points) # Minimum 15%

                    poll_result = self._calculate_poll_result(actual_percentage)
                    poll_results_by_ideology[group_key] = poll_result

        # Sort results for display
        sorted_results = sorted(poll_results_by_ideology.items(), key=lambda item: item[1], reverse=True)

        # Generate polling details
        polling_orgs = [
            "Statewide Polling Inc.", "Ideology Analytics", "Voter Insight Group",
            "Political Compass Research", "Demographic Pulse"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2500)
        days_ago = random.randint(2, 6)

        embed = discord.Embed(
            title=f"📊 State Poll: {state}",
            description=f"**Ideological Breakdown** • {current_phase} ({current_year})",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        if not sorted_results:
            embed.add_field(
                name="No data available",
                value="No candidates found for the specified state and criteria.",
                inline=False
            )
        else:
            results_text = ""
            for group, poll in sorted_results:
                results_text += f"**{group}:** **{poll:.1f}%**\n"
            
            embed.add_field(
                name="📈 Ideological Support",
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
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="seat_poll",
        description="Conduct an NPC poll for a specific seat, showing all candidates with 7% margin of error"
    )
    @app_commands.describe(
        seat_id="The seat to poll (e.g., 'SEN-CA-1', 'CA-GOV')",
        candidate_name="Specific candidate to highlight (leave blank to highlight yourself)"
    )
    async def seat_poll(self, interaction: discord.Interaction, seat_id: str, candidate_name: Optional[str] = None):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                "❌ Polls can only be conducted during campaign phases.",
                ephemeral=True
            )
            return

        current_phase = time_config.get("current_phase", "")
        current_year = time_config["current_rp_date"].year

        # If no candidate specified, check if user is a candidate in this seat
        highlighted_candidate = None
        if not candidate_name:
            signups_col, user_candidate = self._get_user_candidate(interaction.guild.id, interaction.user.id)
            if user_candidate and user_candidate["seat_id"].upper() == seat_id.upper():
                candidate_name = user_candidate.get('candidate') or user_candidate.get('name')
                highlighted_candidate = user_candidate

        # Get all candidates for the specified seat
        seat_candidates = []
        
        if current_phase == "General Campaign":
            # Look in winners collection for general campaign
            winners_col = self.bot.db["winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            if winners_config:
                # For general campaign, look for primary winners from the previous year if we're in an even year
                # Or current year if odd year
                primary_year = current_year - 1 if current_year % 2 == 0 else current_year

                seat_candidates = [
                    w for w in winners_config["winners"] 
                    if (w["seat_id"].upper() == seat_id.upper() and 
                        w.get("primary_winner", False) and 
                        w["year"] == primary_year)
                ]
        else:
            # Look in signups collection for primary campaign
            signups_col, signups_config = self._get_signups_config(interaction.guild.id)
            if signups_config:
                seat_candidates = [
                    c for c in signups_config["candidates"]
                    if (c["seat_id"].upper() == seat_id.upper() and 
                        c["year"] == current_year)
                ]

        if not seat_candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for seat '{seat_id}' in the current {current_phase.lower()}.",
                ephemeral=True
            )
            return

        # Find highlighted candidate if specified by name
        if candidate_name and not highlighted_candidate:
            for candidate in seat_candidates:
                candidate_display_name = candidate.get('candidate') or candidate.get('name')
                if candidate_display_name.lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

            if not highlighted_candidate:
                await interaction.response.send_message(
                    f"❌ Candidate '{candidate_name}' not found in seat '{seat_id}'.",
                    ephemeral=True
                )
                return

        # Calculate polling percentages for each candidate
        poll_results = []

        if current_phase == "General Campaign":
            # For general campaign, use zero-sum percentages
            zero_sum_percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
            
            for candidate in seat_candidates:
                candidate_name = candidate.get('candidate') or candidate.get('name')
                actual_percentage = zero_sum_percentages.get(candidate_name, 50.0)
                poll_result = self._calculate_poll_result(actual_percentage)
                
                poll_results.append({
                    "candidate": candidate,
                    "name": candidate_name,
                    "actual": actual_percentage,
                    "poll": poll_result,
                    "is_highlighted": candidate == highlighted_candidate
                })
        else:
            # For primary campaign, group by party first
            parties = {}
            for candidate in seat_candidates:
                party = candidate["party"]
                if party not in parties:
                    parties[party] = []
                parties[party].append(candidate)

            # Calculate percentages within each party
            for party, party_candidates in parties.items():
                if len(party_candidates) == 1:
                    # Unopposed in primary
                    candidate = party_candidates[0]
                    candidate_name = candidate.get('candidate') or candidate.get('name')
                    actual_percentage = 85.0
                    poll_result = self._calculate_poll_result(actual_percentage)
                    
                    poll_results.append({
                        "candidate": candidate,
                        "name": candidate_name,
                        "actual": actual_percentage,
                        "poll": poll_result,
                        "party": party,
                        "is_highlighted": candidate == highlighted_candidate
                    })
                else:
                    # Calculate relative position based on points
                    total_points = sum(c.get('points', 0) for c in party_candidates)
                    
                    for candidate in party_candidates:
                        candidate_name = candidate.get('candidate') or candidate.get('name')
                        
                        if total_points == 0:
                            actual_percentage = 100.0 / len(party_candidates)  # Even split
                        else:
                            candidate_points = candidate.get('points', 0)
                            actual_percentage = (candidate_points / total_points) * 100.0
                            # Ensure minimum viable percentage
                            actual_percentage = max(15.0, actual_percentage)
                        
                        poll_result = self._calculate_poll_result(actual_percentage)
                        
                        poll_results.append({
                            "candidate": candidate,
                            "name": candidate_name,
                            "actual": actual_percentage,
                            "poll": poll_result,
                            "party": party,
                            "is_highlighted": candidate == highlighted_candidate
                        })

        # Sort by poll results (descending)
        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Generate random polling organization
        polling_orgs = [
            "Regional Polling Institute", "State University Poll", "Local News Survey",
            "Democracy Research Group", "Voter Insight Analytics", "Political Pulse Research",
            "Election Forecast Center", "Public Opinion Associates"
        ]

        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(600, 1500)
        days_ago = random.randint(1, 4)

        # Get seat info from first candidate
        seat_info = seat_candidates[0]

        embed = discord.Embed(
            title=f"📊 Seat Poll: {seat_id}",
            description=f"**{seat_info['office']}** in **{seat_info.get('region') or seat_info.get('state', 'Unknown')}** • {current_phase} ({current_year})",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Add poll results
        if current_phase == "General Campaign":
            # General election - show all candidates together
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                results_text += f"**{i}. {highlight}{result['name']}** ({result['candidate']['party']})\n"
                results_text += f"└ **{result['poll']:.1f}%** (MoE ±7%)\n"
                results_text += f"└ Campaign Points: {result['candidate'].get('points', 0):.2f}\n\n"

            embed.add_field(
                name="🗳️ General Election Results",
                value=results_text,
                inline=False
            )
        else:
            # Primary campaign - group by party
            parties_displayed = {}
            for result in poll_results:
                party = result["party"]
                if party not in parties_displayed:
                    parties_displayed[party] = []
                parties_displayed[party].append(result)

            for party, party_results in parties_displayed.items():
                party_text = ""
                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"└ **{result['poll']:.1f}%** (MoE ±7%)\n"
                    party_text += f"└ Campaign Points: {result['candidate'].get('points', 0):.2f}\n\n"

                embed.add_field(
                    name=f"🎗️ {party} Primary",
                    value=party_text,
                    inline=True
                )

        # Add highlighted candidate info if applicable
        if highlighted_candidate:
            highlighted_result = next((r for r in poll_results if r["is_highlighted"]), None)
            if highlighted_result:
                embed.add_field(
                    name="🎯 Highlighted Candidate",
                    value=f"**{highlighted_result['name']}** ({highlighted_result['candidate']['party']})\n"
                          f"Polling at: **{highlighted_result['poll']:.1f}%**\n"
                          f"Campaign Points: {highlighted_result['candidate'].get('points', 0):.2f}",
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

        # Add competition context
        if len(seat_candidates) > 1:
            embed.add_field(
                name="🔍 Competition Context",
                value=f"**Total Candidates:** {len(seat_candidates)}\n"
                      f"**Parties Competing:** {len(set(c['party'] for c in seat_candidates))}\n"
                      f"**Election Type:** {current_phase}",
                inline=True
            )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Polling(bot))