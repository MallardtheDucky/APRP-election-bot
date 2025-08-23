import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
from typing import Optional, List
from .ideology import STATE_DATA

class Polling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Polling cog loaded successfully")

    # Create main command groups
    poll_group = app_commands.Group(name="poll", description="Polling commands")

    # Create subgroups
    poll_admin_group = app_commands.Group(name="admin", description="Poll admin commands", parent=poll_group)
    poll_vote_group = app_commands.Group(name="vote", description="Poll voting commands", parent=poll_group)
    poll_info_group = app_commands.Group(name="info", description="Poll information commands", parent=poll_group)

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
            # First normalize
            for name in final_percentages:
                final_percentages[name] = (final_percentages[name] / total) * 100.0

            # Handle rounding to ensure exact 100% total
            new_total = sum(final_percentages.values())
            if abs(new_total - 100.0) > 0.01:  # If rounding errors exist
                # Adjust the largest percentage to make total exactly 100%
                largest_name = max(final_percentages.keys(), key=lambda k: final_percentages[k])
                final_percentages[largest_name] += (100.0 - new_total)

        return final_percentages

    def _calculate_poll_result(self, actual_percentage: float, margin_of_error: float = 7.0) -> float:
        """Calculate poll result with margin of error"""
        # Apply random variation within margin of error
        variation = random.uniform(-margin_of_error, margin_of_error)
        poll_result = actual_percentage + variation

        # Ensure result stays within reasonable bounds (0-100%)
        poll_result = max(0.1, min(99.9, poll_result))

        return poll_result

    # Commands under /poll group
    @poll_group.command(
        name="candidate",
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

    @poll_info_group.command(
        name="state",
        description="Conduct an NPC poll for all parties in a specific state, showing Rep/Dem/Independent support."
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

        # Use STATE_DATA to get base percentages for Republican, Democrat, and Independent
        state_info = STATE_DATA.get(state.upper())  # STATE_DATA uses uppercase keys

        if not state_info:
            await interaction.response.send_message(
                f"❌ State data not found for '{state}'. Cannot determine party base percentages.",
                ephemeral=True
            )
            return

        # Get base party percentages from STATE_DATA
        republican_base = state_info.get("republican", 33.0)
        democrat_base = state_info.get("democrat", 33.0) 
        independent_base = state_info.get("other", 34.0)

        # Calculate poll results with margin of error
        poll_results = {
            "Republican": self._calculate_poll_result(republican_base),
            "Democrat": self._calculate_poll_result(democrat_base),
            "Independent": self._calculate_poll_result(independent_base)
        }

        # Sort results for display
        sorted_results = sorted(poll_results.items(), key=lambda item: item[1], reverse=True)

        # Generate polling details
        polling_orgs = [
            "Statewide Polling Inc.", "Political Analytics", "Voter Insight Group",
            "State University Poll", "Regional Polling Institute"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(800, 2500)
        days_ago = random.randint(2, 6)

        embed = discord.Embed(
            title=f"📊 State Poll: {state}",
            description=f"**Party Support Breakdown** • {current_phase} ({current_year})",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        # Create visual progress bar function
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        results_text = ""
        for party, poll_percentage in sorted_results:
            # Party abbreviations
            party_abbrev = "R" if party == "Republican" else ("D" if party == "Democrat" else "I")
            
            progress_bar = create_progress_bar(poll_percentage)
            results_text += f"**{party_abbrev} - {party}**\n"
            results_text += f"{progress_bar} **{poll_percentage:.1f}%**\n\n"

        embed.add_field(
            name="📈 Party Support",
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

    @poll_group.command(
        name="seat",
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

        # Create visual progress bar function
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        # Add poll results
        if current_phase == "General Campaign":
            # General election - show all candidates together
            results_text = ""
            for i, result in enumerate(poll_results, 1):
                highlight = "👑 " if result["is_highlighted"] else ""
                party_abbrev = result['candidate']['party'][0] if result['candidate']['party'] else "I"
                progress_bar = create_progress_bar(result['poll'])

                results_text += f"**{i}. {highlight}{result['name']}**\n"
                results_text += f"**{party_abbrev} - {result['candidate']['party']}**\n"
                results_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

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
                party_abbrev = party[0] if party else "I"

                for i, result in enumerate(party_results, 1):
                    highlight = "👑 " if result["is_highlighted"] else ""
                    progress_bar = create_progress_bar(result['poll'])

                    party_text += f"**{i}. {highlight}{result['name']}**\n"
                    party_text += f"**{party_abbrev} - {party}**\n"
                    party_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

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