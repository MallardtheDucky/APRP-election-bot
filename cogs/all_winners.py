from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
from datetime import datetime

class AllWinners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("All Winners cog loaded successfully")

    def _get_winners_config(self, guild_id: int):
        """Get or create winners configuration"""
        col = self.bot.db["winners"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "winners": []
            }
            col.insert_one(config)
        return col, config

    def _get_signups_config(self, guild_id: int):
        """Get signups configuration"""
        col = self.bot.db["signups"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_elections_config(self, guild_id: int):
        """Get elections configuration"""
        col = self.bot.db["elections_config"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    @commands.Cog.listener()
    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Handle phase changes and process primary winners"""
        if old_phase == "Primary Election" and new_phase == "General Campaign":
            await self._process_primary_winners(guild_id, current_year)


    def _calculate_ideology_points(self, winner, state_data, region_medians, state_to_seat):
        """Calculate ideology-based baseline percentage for a candidate based on their seat and party"""
        seat_id = winner["seat_id"]
        party = winner["party"]
        office = winner["office"]

        # Map party names to ideology data keys
        party_mapping = {
            "Republican Party": "republican",
            "Democratic Party": "democrat", 
            "Independent": "other"
        }

        ideology_key = party_mapping.get(party)
        if not ideology_key:
            return 20.0  # Unknown party gets 20% baseline

        if "District" in office:
            # For House representatives, use specific state data
            # Find the state for this seat
            target_state = None
            for state, rep_seat in state_to_seat.items():
                if rep_seat == seat_id:
                    target_state = state
                    break

            if target_state and target_state in state_data:
                return state_data[target_state][ideology_key]
            else:
                return 20.0  # Fallback if state not found

        elif office in ["Senate", "Governor"]:
            # For Senate/Governor, use regional medians
            region = winner["region"]
            if region in region_medians:
                return region_medians[region][ideology_key]
            else:
                return 20.0  # Fallback if region not found

        else:
            # For other offices (President, VP, etc.), default baseline
            return 25.0

    def _calculate_seat_percentages(self, seat_candidates):
        """Calculate final percentages for candidates in a seat"""
        if not seat_candidates:
            return {}

        # Count parties and determine baseline percentages
        parties = {}
        for candidate in seat_candidates:
            party = candidate["party"]
            if party not in parties:
                parties[party] = []
            parties[party].append(candidate)

        num_parties = len(parties)
        major_parties = ["Republican Party", "Democratic Party"]

        # Determine baseline percentages based on party composition
        baseline_percentages = {}
        major_parties_present = sum(1 for p in parties.keys() if p in major_parties)

        if num_parties == 2:
            # 50-50 split (Democrat + Republican)
            for party in parties.keys():
                baseline_percentages[party] = 50.0
        elif num_parties == 3:
            # 40-40-20 split (Democrat + Republican + Independent)
            if major_parties_present == 2:
                for party in parties.keys():
                    if party in major_parties:
                        baseline_percentages[party] = 40.0
                    else:
                        baseline_percentages[party] = 20.0
            else:
                # If not standard Dem-Rep-Ind, split evenly
                for party in parties.keys():
                    baseline_percentages[party] = 100.0 / 3
        elif num_parties == 4:
            # 40-40-10-10 split (Democrat + Republican + Independent + Independent)
            if major_parties_present == 2:
                for party in parties.keys():
                    if party in major_parties:
                        baseline_percentages[party] = 40.0
                    else:
                        baseline_percentages[party] = 10.0
            else:
                # If not standard setup, split evenly
                for party in parties.keys():
                    baseline_percentages[party] = 25.0
        else:
            # For other numbers of parties, split evenly
            for party in parties.keys():
                baseline_percentages[party] = 100.0 / num_parties

        # Calculate campaign point adjustments for each candidate
        candidate_adjustments = {}

        for candidate in seat_candidates:
            points = candidate.get("points", 0.0)
            corruption = candidate.get("corruption", 0)

            # Points to percentage conversion (1200 points = 1%)
            points_adjustment = points / 1200.0

            # Apply corruption penalty
            corruption_penalty = corruption * 0.1  # Each corruption point = -0.1%

            # Net adjustment from campaign activities
            net_adjustment = points_adjustment - corruption_penalty
            candidate_adjustments[candidate["candidate"]] = net_adjustment

        # Apply adjustments to baseline percentages
        final_percentages = {}
        total_adjustment = sum(candidate_adjustments.values())

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]

            # Start with party baseline
            base_percentage = baseline_percentages[party]

            # Add individual candidate's campaign adjustment
            adjustment = candidate_adjustments[candidate_name]
            adjusted_percentage = base_percentage + adjustment

            # Ensure no negative percentages
            adjusted_percentage = max(0.1, adjusted_percentage)  # Minimum 0.1% to avoid zero

            final_percentages[candidate_name] = adjusted_percentage

        # Normalize to ensure total equals 100%
        total_percentage = sum(final_percentages.values())
        if total_percentage > 0:
            for candidate_name in final_percentages:
                final_percentages[candidate_name] = (final_percentages[candidate_name] / total_percentage) * 100.0

        return final_percentages

    def _calculate_baseline_percentage(self, guild_id: int, seat_id: str, candidate_party: str):
        """Calculate baseline starting percentage for general election based on party distribution"""
        # Get all primary winners for this seat to determine party distribution
        winners_col, winners_config = self._get_winners_config(guild_id)

        if not winners_config:
            return 50.0

        # Get current year
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Find all primary winners for this seat
        seat_winners = [
            w for w in winners_config["winners"] 
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

        if not seat_winners:
            return 50.0

        # Count unique parties
        parties = set(winner["party"] for winner in seat_winners)
        num_parties = len(parties)
        major_parties = {"Democratic Party", "Republican Party"}

        # Check how many major parties are present
        major_parties_present = major_parties.intersection(parties)
        num_major_parties = len(major_parties_present)

        # Calculate baseline percentages based on exact specifications
        if num_parties == 1:
            return 100.0  # Uncontested
        elif num_parties == 2:
            # Only works if both are major parties (Democrat + Republican)
            if num_major_parties == 2:
                return 50.0  # 50-50 split for Dem-Rep
            else:
                # If not both major parties, split evenly
                return 50.0
        elif num_parties == 3:
            # Democrat + Republican + Independent = 40-40-20
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 20.0  # Independent gets 20%
            else:
                # If not standard Dem-Rep-Ind, split evenly
                return 100.0 / 3
        elif num_parties == 4:
            # Democrat + Republican + Independent + Independent = 40-40-10-10
            if num_major_parties == 2:
                if candidate_party in major_parties:
                    return 40.0  # Democrat or Republican gets 40%
                else:
                    return 10.0  # Each Independent gets 10%
            else:
                # If not standard setup, split evenly
                return 25.0
        else:
            # For 5+ parties, split evenly
            return 100.0 / num_parties

    async def _process_primary_winners(self, guild_id: int, current_year: int):
        """Process primary election results and determine winners"""
        signups_col, signups_config = self._get_signups_config(guild_id)
        winners_col, winners_config = self._get_winners_config(guild_id)

        if not signups_config:
            return

        # Get all candidates for current year
        candidates = [c for c in signups_config["candidates"] if c["year"] == current_year]

        # Group candidates by seat and party
        seat_party_groups = {}
        for candidate in candidates:
            seat_id = candidate["seat_id"]
            party = candidate["party"]
            key = f"{seat_id}_{party}"

            if key not in seat_party_groups:
                seat_party_groups[key] = []
            seat_party_groups[key].append(candidate)

        primary_winners = []

        # Import ideology data for seat-based points
        from cogs.ideology import STATE_DATA, calculate_region_medians, STATE_TO_SEAT

        # Get region medians for senate/governor seats
        region_medians = calculate_region_medians()

        # Determine winner for each party in each seat
        for key, party_candidates in seat_party_groups.items():
            if len(party_candidates) == 1:
                # Only one candidate, automatic winner
                winner = party_candidates[0]
            else:
                # Multiple candidates, highest points wins
                winner = max(party_candidates, key=lambda x: x["points"])

            # Calculate baseline percentage for general election
            baseline_percentage = self._calculate_baseline_percentage(guild_id, winner["seat_id"], winner["party"])

            # Create winner entry
            winner_entry = {
                "year": current_year,
                "user_id": winner["user_id"],
                "office": winner["office"],
                "state": winner["region"],
                "seat_id": winner["seat_id"],
                "candidate": winner["name"],
                "party": winner["party"],
                "points": 0.0,  # Reset campaign points for general election
                "baseline_percentage": baseline_percentage,  # Store ideology-based baseline
                "votes": 0,   # To be input by admins
                "corruption": winner["corruption"],  # Keep corruption level
                "final_score": 0,  # Calculated later
                "stamina": winner["stamina"],
                "winner": False,  # TBD after general election
                "phase": "Primary Winner",
                "primary_winner": True,
                "general_winner": False,
                "created_date": datetime.utcnow()
            }

            primary_winners.append(winner_entry)

        # Add winners to database
        if primary_winners:
            winners_config["winners"].extend(primary_winners)
            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        # Send announcement
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._announce_primary_results(guild, primary_winners, current_year)

    async def _announce_primary_results(self, guild: discord.Guild, winners: List[dict], year: int):
        """Announce primary election results"""
        # Get announcement channel
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild.id})
        announcement_channel_id = setup_config.get("announcement_channel") if setup_config else None

        channel = None
        if announcement_channel_id:
            channel = guild.get_channel(announcement_channel_id)
        if not channel:
            channel = discord.utils.get(guild.channels, name="general") or guild.system_channel

        if not channel:
            return

        # Group winners by state for better display
        states = {}
        for winner in winners:
            state = winner["state"]
            if state not in states:
                states[state] = []
            states[state].append(winner)

        embed = discord.Embed(
            title=f"🗳️ {year} Primary Election Results!",
            description="The following candidates have won their party primaries and advance to the General Campaign:",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        for state, state_winners in sorted(states.items()):
            winner_text = ""
            for winner in state_winners:
                winner_text += f"**{winner['candidate']}** ({winner['party']})\n"
                winner_text += f"└ {winner['seat_id']} - {winner['office']}\n\n"

            embed.add_field(
                name=f"📍 {state}",
                value=winner_text,
                inline=True
            )

        embed.add_field(
            name="🎯 What's Next?",
            value=f"These {len(winners)} candidates will now compete in the General Campaign!\n"
                  f"Points have been reset to 0 for the general campaign phase.",
            inline=False
        )

        try:
            await channel.send(embed=embed)
        except:
            pass

    @app_commands.command(
        name="view_primary_winners",
        description="View all primary election winners for the current year"
    )
    async def view_primary_winners(self, interaction: discord.Interaction, year: int = None):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config["current_phase"]

        # If we're in a general election year (even year), look for primary winners from previous year
        if current_year % 2 == 0:  # Even year (general election year)
            target_year = year if year else (current_year - 1)  # Look at previous year's primaries
        else:  # Odd year (primary year)
            target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Filter primary winners for target year
        primary_winners = [
            w for w in winners_config["winners"] 
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not primary_winners:
            await interaction.response.send_message(
                f"📋 No primary winners found for {target_year}.",
                ephemeral=True
            )
            return

        # Group by state
        states = {}
        for winner in primary_winners:
            state = winner["state"]
            if state not in states:
                states[state] = []
            states[state].append(winner)

        if current_year % 2 == 0 and not year:  # Even year, showing previous year's winners
            description_text = f"Candidates from {target_year} primaries advancing to {current_year} General Campaign"
        else:
            description_text = f"Candidates advancing to the General Campaign"

        embed = discord.Embed(
            title=f"🏆 {target_year} Primary Election Winners",
            description=description_text,
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for state, state_winners in sorted(states.items()):
            winner_list = ""
            for winner in state_winners:
                winner_list += f"**{winner['candidate']}** ({winner['party']})\n"
                winner_list += f"└ {winner['seat_id']} - {winner['office']}\n"
                winner_list += f"└ Points: {winner['points']:.2f} | Stamina: {winner['stamina']} | Corruption: {winner['corruption']}\n"
                winner_list += f"└ Baseline: {winner.get('baseline_percentage', 0):.1f}%\n\n"

            embed.add_field(
                name=f"📍 {state}",
                value=winner_list,
                inline=True
            )

        embed.add_field(
            name="📊 Summary",
            value=f"**Total Primary Winners:** {len(primary_winners)}\n"
                  f"**States Represented:** {len(states)}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_set_winner_votes",
        description="Set votes for a primary winner (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_winner_votes(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        votes: int,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Find the candidate
        winner_found = -1
        for i, winner in enumerate(winners_config["winners"]):
            if (winner["candidate"].lower() == candidate_name.lower() and 
                winner["year"] == target_year and
                winner.get("primary_winner", False)):
                winner_found = i
                break

        if winner_found == -1:
            await interaction.response.send_message(
                f"❌ Primary winner '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        old_votes = winners_config["winners"][winner_found]["votes"]
        winners_config["winners"][winner_found]["votes"] = votes

        # Find all candidates in the same seat to recalculate percentages
        winner_data = winners_config["winners"][winner_found]
        seat_id = winner_data["seat_id"]
        seat_candidates = [
            w for w in winners_config["winners"] 
            if w["seat_id"] == seat_id and w["year"] == target_year and w.get("primary_winner", False)
        ]

        # Recalculate percentages for the entire seat
        percentages = self._calculate_seat_percentages(seat_candidates)

        # Update all candidates in this seat with new percentages
        for candidate_name_key, percentage in percentages.items():
            for i, winner in enumerate(winners_config["winners"]):
                if (winner["candidate"] == candidate_name_key and 
                    winner["year"] == target_year and
                    winner["seat_id"] == seat_id):
                    winners_config["winners"][i]["final_percentage"] = percentage
                    break

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        new_percentage = percentages.get(candidate_name, 0)
        await interaction.response.send_message(
            f"✅ Set votes for **{candidate_name}**: {old_votes} → {votes}\n"
            f"New final percentage: **{new_percentage:.2f}%**\n"
            f"Seat percentages have been recalculated for all candidates.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_declare_general_winners",
        description="Declare general election winners based on final scores (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_declare_general_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will declare general election winners for {target_year} based on final scores.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners for target year
        primary_winners = [
            w for w in winners_config["winners"] 
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not primary_winners:
            await interaction.response.send_message(
                f"❌ No primary winners found for {target_year}.",
                ephemeral=True
            )
            return

        # Group by seat to find winner for each seat
        seats = {}
        for winner in primary_winners:
            seat_id = winner["seat_id"]
            if seat_id not in seats:
                seats[seat_id] = []
            seats[seat_id].append(winner)

        general_winners = []

        for seat_id, candidates in seats.items():
            # Calculate final percentages for this seat
            percentages = self._calculate_seat_percentages(candidates)

            # Find candidate with highest percentage
            if percentages:
                winning_candidate = max(percentages.keys(), key=lambda x: percentages[x])
                winning_percentage = percentages[winning_candidate]

                # Update winner status and store final percentage
                for i, winner in enumerate(winners_config["winners"]):
                    if (winner["candidate"] == winning_candidate and 
                        winner["year"] == target_year and
                        winner["seat_id"] == seat_id):
                        winners_config["winners"][i]["general_winner"] = True
                        winners_config["winners"][i]["winner"] = True
                        winners_config["winners"][i]["final_percentage"] = winning_percentage
                        general_winners.append(winners_config["winners"][i])
                        break

                # Update all candidates in this seat with their final percentages
                for candidate_name, percentage in percentages.items():
                    for i, winner in enumerate(winners_config["winners"]):
                        if (winner["candidate"] == candidate_name and 
                            winner["year"] == target_year and
                            winner["seat_id"] == seat_id):
                            winners_config["winners"][i]["final_percentage"] = percentage
                            break

        # Update database
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        # Update election seats with new holders
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)

        if elections_config:
            for winner in general_winners:
                for i, seat in enumerate(elections_config["seats"]):
                    if seat["seat_id"] == winner["seat_id"]:
                        user = interaction.guild.get_member(winner["user_id"])
                        user_name = user.display_name if user else winner["candidate"]

                        # Calculate new term dates
                        term_start = datetime(target_year + 1, 1, 1)  # Terms start after election year
                        term_end = datetime(target_year + 1 + seat["term_years"], 1, 1)

                        elections_config["seats"][i].update({
                            "current_holder": user_name,
                            "current_holder_id": winner["user_id"],
                            "term_start": term_start,
                            "term_end": term_end,
                            "up_for_election": False
                        })
                        break

            elections_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": elections_config["seats"]}}
            )

        await interaction.response.send_message(
            f"✅ Declared {len(general_winners)} general election winners for {target_year}!\n"
            f"Election seats have been updated with new holders.",
            ephemeral=True
        )

    @app_commands.command(
        name="view_general_winners",
        description="View general election winners"
    )
    async def view_general_winners(self, interaction: discord.Interaction, year: int = None):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Filter general winners for target year
        general_winners = [
            w for w in winners_config["winners"] 
            if w["year"] == target_year and w.get("general_winner", False)
        ]

        # If no declared winners, check for general campaign candidates (primary winners)
        if not general_winners:
            # For even years (general election), look at previous year's primary winners
            primary_year = target_year - 1 if target_year % 2 == 0 else target_year

            campaign_candidates = [
                w for w in winners_config["winners"] 
                if w["year"] == primary_year and w.get("primary_winner", False)
            ]

            if campaign_candidates:
                await interaction.response.send_message(
                    f"📋 No general election winners declared yet for {target_year}.\n"
                    f"🎯 Use `/view_general_campaign` to see the {len(campaign_candidates)} candidates currently in the general campaign phase.",
                    ephemeral=True
                )
                return
            else:
                await interaction.response.send_message(
                    f"📋 No general election winners found for {target_year}.",
                    ephemeral=True
                )
                return

        # Group by state
        states = {}
        for winner in general_winners:
            state = winner["state"]
            if state not in states:
                states[state] = []
            states[state].append(winner)

        embed = discord.Embed(
            title=f"🏆 {target_year} General Election Winners",
            description=f"Elected officials taking office",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for state, state_winners in sorted(states.items()):
            winner_list = ""
            for winner in state_winners:
                winner_list += f"**{winner['candidate']}** ({winner['party']})\n"
                winner_list += f"└ {winner['seat_id']} - {winner['office']}\n"
                winner_list += f"└ Final Percentage: {winner.get('final_percentage', 0):.2f}%\n"
                winner_list += f"└ Points: {winner['points']:.2f} | Votes: {winner['votes']} | Corruption: {winner['corruption']}\n\n"

            embed.add_field(
                name=f"📍 {state}",
                value=winner_list,
                inline=True
            )

        embed.add_field(
            name="📊 Summary",
            value=f"**Total Winners:** {len(general_winners)}\n"
                  f"**States Represented:** {len(states)}",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_bulk_set_votes",
        description="Bulk set votes for multiple candidates (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_set_votes(
        self,
        interaction: discord.Interaction,
        vote_data: str,
        year: int = None
    ):
        """Format: candidate1:votes1,candidate2:votes2,..."""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Parse vote data
        pairs = vote_data.split(",")
        updated_candidates = []
        errors = []
        candidate_percentages = {} # To store updated percentages

        for pair in pairs:
            try:
                candidate_name, votes_str = pair.strip().split(":")
                votes = int(votes_str)

                # Find the candidate
                candidate_found_index = -1
                for i, winner in enumerate(winners_config["winners"]):
                    if (winner["candidate"].lower() == candidate_name.lower() and 
                        winner["year"] == target_year and
                        winner.get("primary_winner", False)):
                        candidate_found_index = i
                        break

                if candidate_found_index != -1:
                    winners_config["winners"][candidate_found_index]["votes"] = votes

                    # Recalculate percentages for the seat
                    winner_data = winners_config["winners"][candidate_found_index]
                    seat_id = winner_data["seat_id"]
                    seat_candidates = [
                        w for w in winners_config["winners"] 
                        if w["seat_id"] == seat_id and w["year"] == target_year and w.get("primary_winner", False)
                    ]
                    percentages = self._calculate_seat_percentages(seat_candidates)

                    # Update all candidates in this seat with new percentages
                    for candidate_name_key, percentage in percentages.items():
                        for i, winner in enumerate(winners_config["winners"]):
                            if (winner["candidate"] == candidate_name_key and 
                                winner["year"] == target_year and
                                winner["seat_id"] == seat_id):
                                winners_config["winners"][i]["final_percentage"] = percentage
                                candidate_percentages[candidate_name_key] = percentage # Store for response
                                break

                    updated_candidates.append(f"{candidate_name}: {votes} votes (New %: {percentages.get(candidate_name, 0):.2f}%)")
                else:
                    errors.append(f"Candidate {candidate_name} not found")

            except (ValueError, IndexError):
                errors.append(f"Invalid format: {pair}")

        if updated_candidates:
            winners_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        response = f"✅ Updated votes for {len(updated_candidates)} candidates"
        if updated_candidates:
            response += ":\n• " + "\n• ".join(updated_candidates[:10])
            if len(updated_candidates) > 10:
                response += f"\n• and {len(updated_candidates) - 10} more"

        if errors:
            response += f"\n\n❌ Errors:\n• " + "\n• ".join(errors[:5])

        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(
        name="admin_view_general_points",
        description="View all candidate points in general campaign phase (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_general_points(
        self,
        interaction: discord.Interaction,
        sort_by: str = "points",
        filter_state: str = None,
        filter_party: str = None,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general election)
        # If we're in a general election year (even), look for primary winners from previous year
        if target_year % 2 == 0:  # Even year (general election year)
            primary_year = target_year - 1  # Look at previous year's primaries
        else:  # Odd year (primary year)
            primary_year = target_year

        candidates = [
            w for w in winners_config["winners"] 
            if w["year"] == primary_year and w.get("primary_winner", False)
        ]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No general election candidates found for {target_year}.",
                ephemeral=True
            )
            return

        # Apply filters
        if filter_state:
            candidates = [c for c in candidates if c["state"].lower() == filter_state.lower()]

        if filter_party:
            candidates = [c for c in candidates if c["party"].lower() == filter_party.lower()]

        if not candidates:
            await interaction.response.send_message(
                "❌ No candidates found with those filters.",
                ephemeral=True
            )
            return

        # Sort candidates
        if sort_by.lower() == "points":
            candidates.sort(key=lambda x: x["points"], reverse=True)
        elif sort_by.lower() == "votes":
            candidates.sort(key=lambda x: x["votes"], reverse=True)
        elif sort_by.lower() == "final_percentage":
            candidates.sort(key=lambda x: x.get("final_percentage", 0), reverse=True)
        elif sort_by.lower() == "corruption":
            candidates.sort(key=lambda x: x["corruption"], reverse=True)
        elif sort_by.lower() == "stamina":
            candidates.sort(key=lambda x: x["stamina"], reverse=True)
        else:
            candidates.sort(key=lambda x: x["candidate"].lower())

        # Create embed with top candidates
        embed = discord.Embed(
            title=f"📊 {target_year} General Campaign Points",
            description=f"Sorted by {sort_by} • {len(candidates)} candidates",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Show top 15 candidates
        top_candidates = candidates[:15]
        candidate_list = ""

        for i, candidate in enumerate(top_candidates, 1):
            user = interaction.guild.get_member(candidate["user_id"])
            user_mention = user.mention if user else candidate["candidate"]

            candidate_list += (
                f"**{i}.** {candidate['candidate']} ({candidate['party']})\n"
                f"   └ {candidate['seat_id']} • Points: {candidate['points']:.2f} • "
                f"Votes: {candidate['votes']} • %: {candidate.get('final_percentage', 0):.2f}%\n"
                f"   └ Stamina: {candidate['stamina']} • Corruption: {candidate['corruption']} • {user_mention}\n\n"
            )

        embed.add_field(
            name="🏆 Top Candidates",
            value=candidate_list[:1024],  # Discord field limit
            inline=False
        )

        # Summary stats
        total_points = sum(c['points'] for c in candidates)
        total_votes = sum(c['votes'] for c in candidates)
        avg_corruption = sum(c['corruption'] for c in candidates) / len(candidates) if candidates else 0
        total_percentage = sum(c.get('final_percentage', 0) for c in candidates)

        embed.add_field(
            name="📈 Summary Statistics",
            value=f"**Total Candidates:** {len(candidates)}\n"
                  f"**Total Points:** {total_points:.2f}\n"
                  f"**Total Votes:** {total_votes:,}\n"
                  f"**Avg Corruption:** {avg_corruption:.1f}\n"
                  f"**Total %:** {total_percentage:.2f}%",
            inline=True
        )

        # Show filter info if applied
        filter_info = ""
        if filter_state:
            filter_info += f"State: {filter_state} • "
        if filter_party:
            filter_info += f"Party: {filter_party} • "
        if filter_info:
            embed.add_field(
                name="🔍 Active Filters",
                value=filter_info.rstrip(" • "),
                inline=True
            )

        if len(candidates) > 15:
            embed.set_footer(text=f"Showing top 15 of {len(candidates)} candidates")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_view_candidate_details",
        description="View detailed info for a specific general election candidate (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_candidate_details(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Find the candidate
        # If we're in a general election year (even), look for primary winners from previous year
        if target_year % 2 == 0:  # Even year (general election year)
            primary_year = target_year - 1  # Look at previous year's primaries
        else:  # Odd year (primary year)
            primary_year = target_year

        candidate = None
        for w in winners_config["winners"]:
            if (w["candidate"].lower() == candidate_name.lower() and 
                w["year"] == primary_year and
                w.get("primary_winner", False)):
                candidate = w
                break

        if not candidate:
            await interaction.response.send_message(
                f"❌ General election candidate '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        user = interaction.guild.get_member(candidate["user_id"])
        user_info = f"{user.mention} ({user.display_name})" if user else "User not found"

        embed = discord.Embed(
            title=f"👤 {candidate['candidate']} - Campaign Details",
            description=f"**{candidate['party']}** candidate for **{candidate['seat_id']}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🏛️ Election Info",
            value=f"**Year:** {candidate['year']}\n"
                  f"**Office:** {candidate['office']}\n"
                  f"**State/Region:** {candidate['state']}\n"
                  f"**Seat ID:** {candidate['seat_id']}",
            inline=True
        )

        embed.add_field(
            name="📊 Campaign Stats",
            value=f"**Points:** {candidate['points']:.2f}\n"
                  f"**Votes:** {candidate['votes']:,}\n"
                  f"**Final Percentage:** {candidate.get('final_percentage', 0):.2f}%\n"
                  f"**Stamina:** {candidate['stamina']}/100",
            inline=True
        )

        embed.add_field(
            name="⚖️ Status",
            value=f"**Corruption:** {candidate['corruption']}\n"
                  f"**Primary Winner:** {'✅' if candidate.get('primary_winner') else '❌'}\n"
                  f"**General Winner:** {'✅' if candidate.get('general_winner') else '❌'}\n"
                  f"**Phase:** {candidate.get('phase', 'General Campaign')}",
            inline=True
        )

        embed.add_field(
            name="👤 Player Info",
            value=user_info,
            inline=False
        )

        # Calculate score breakdown
        score_breakdown = f"**Percentage Calculation:**\n"
        score_breakdown += f"Baseline: {candidate.get('baseline_percentage', 0):.1f}%\n"
        score_breakdown += f"+ Points to % ({candidate['points']:.2f}): {(candidate['points'] / 1200.0):.2f}%\n"
        score_breakdown += f"- Corruption ({candidate['corruption']}): {(candidate['corruption'] * 0.1):.1f}%\n"
        score_breakdown += f"= **Final Percentage: {candidate.get('final_percentage', 0):.2f}%**"

        embed.add_field(
            name="🧮 Percentage Breakdown",
            value=score_breakdown,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_force_primary_winners",
        description="Force declare primary winners from current signups (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_force_declare_primary_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Manually trigger primary winner processing"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will process all signups for {target_year} and declare primary winners.\n"
                f"This will move candidates from signups to winners with ideology-based points.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        await self._process_primary_winners(interaction.guild.id, target_year)

        await interaction.response.send_message(
            f"✅ Successfully processed primary winners for {target_year}!\n"
            f"Check the announcements channel for results.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_clear_all_winners",
        description="Clear all winners data (Admin only - DESTRUCTIVE)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_all_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Clear all winners data for a specific year or all years"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else None

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        if target_year:
            # Clear specific year
            year_winners = [w for w in winners_config["winners"] if w["year"] == target_year]
            if not confirm:
                await interaction.response.send_message(
                    f"⚠️ **Warning:** This will permanently delete {len(year_winners)} winners for {target_year}.\n"
                    f"To confirm, run with `confirm:True`",
                    ephemeral=True
                )
                return

            winners_config["winners"] = [w for w in winners_config["winners"] if w["year"] != target_year]
            cleared_count = len(year_winners)
            message = f"✅ Cleared {cleared_count} winners for {target_year}."
        else:
            # Clear all years
            all_winners_count = len(winners_config["winners"])
            if not confirm:
                await interaction.response.send_message(
                    f"⚠️ **DANGER:** This will permanently delete ALL {all_winners_count} winners from ALL years.\n"
                    f"To confirm this destructive action, run with `confirm:True`",
                    ephemeral=True
                )
                return

            winners_config["winners"] = []
            cleared_count = all_winners_count
            message = f"✅ Cleared ALL {cleared_count} winners from all years."

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(
        name="admin_reset_general_election",
        description="Reset general election by clearing all primary winners (Admin only - DESTRUCTIVE)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_general_election(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Reset general election by clearing all primary winners and general winners"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Count winners for target year (both primary and general)
        year_winners = [w for w in winners_config["winners"] if w["year"] == target_year]
        primary_winners = [w for w in year_winners if w.get("primary_winner", False)]
        general_winners = [w for w in year_winners if w.get("general_winner", False)]

        if not year_winners:
            await interaction.response.send_message(
                f"❌ No election winners found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **DANGER:** This will completely reset the {target_year} general election!\n"
                f"• Remove ALL {len(primary_winners)} primary winners\n"
                f"• Remove ALL {len(general_winners)} general election winners\n"
                f"• Clear all general campaign points, votes, and percentages\n"
                f"• Reset all election seat holders\n"
                f"• Cannot be undone!\n\n"
                f"To confirm this destructive action, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Remove all winners for target year
        winners_config["winners"] = [w for w in winners_config["winners"] if w["year"] != target_year]

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        # Reset election seats that were won in this year
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)
        seats_reset = 0

        if elections_config:
            for i, seat in enumerate(elections_config["seats"]):
                # Check if this seat was won in the target year
                if (seat.get("term_start") and 
                    seat["term_start"].year == target_year + 1):  # Terms start year after election
                    elections_config["seats"][i].update({
                        "current_holder": None,
                        "current_holder_id": None,
                        "term_start": None,
                        "term_end": None,
                        "up_for_election": True
                    })
                    seats_reset += 1

            elections_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": elections_config["seats"]}}
            )

        await interaction.response.send_message(
            f"✅ **General Election Reset Complete!**\n"
            f"• Removed {len(primary_winners)} primary winners for {target_year}\n"
            f"• Removed {len(general_winners)} general election winners\n"
            f"• Reset {seats_reset} election seats to vacant\n"
            f"• All general election data has been cleared\n"
            f"• Primary elections can now be run again from signups",
            ephemeral=True
        )

    @app_commands.command(
        name="view_general_campaign",
        description="View all candidates currently in the general campaign phase"
    )
    async def view_general_campaign(self, interaction: discord.Interaction, year: int = None):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general campaign) for target year
        # If we're in a general election year (even), look for primary winners from previous year
        if target_year % 2 == 0:  # Even year (general election year)
            primary_year = target_year - 1  # Look at previous year's primaries
        else:  # Odd year (primary year)
            primary_year = target_year

        general_candidates = [
            w for w in winners_config["winners"] 
            if w["year"] == primary_year and w.get("primary_winner", False)
        ]

        if not general_candidates:
            await interaction.response.send_message(
                f"📋 No candidates found in general campaign for {target_year}.",
                ephemeral=True
            )
            return

        # Group by state/region
        regions = {}
        for candidate in general_candidates:
            region = candidate["state"]
            if region not in regions:
                regions[region] = []
            regions[region].append(candidate)

        embed = discord.Embed(
            title=f"🎯 {target_year} General Campaign Candidates",
            description=f"Primary winners advancing to general election • Current phase: **{current_phase}**",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        for region, region_candidates in sorted(regions.items()):
            # Sort by points (campaign progress)
            region_candidates.sort(key=lambda x: x.get("points", 0), reverse=True)

            candidate_list = ""
            for candidate in region_candidates:
                candidate_list += f"**{candidate['candidate']}** ({candidate['party']})\n"
                candidate_list += f"└ {candidate['seat_id']} - {candidate['office']}\n"
                candidate_list += f"└ Stamina: {candidate.get('stamina', 100)} | Corruption: {candidate.get('corruption', 0)}\n"

                user = interaction.guild.get_member(candidate["user_id"])
                if user:
                    candidate_list += f"└ {user.mention}\n\n"
                else:
                    candidate_list += "\n"

            # Handle long field values
            if len(candidate_list) > 1024:
                parts = candidate_list.split('\n\n')
                current_part = ""
                part_num = 1

                for part in parts:
                    if len(current_part + part + '\n\n') > 1024:
                        embed.add_field(
                            name=f"📍 {region} (Part {part_num})",
                            value=current_part,
                            inline=False
                        )
                        current_part = part + '\n\n'
                        part_num += 1
                    else:
                        current_part += part + '\n\n'

                if current_part:
                    embed.add_field(
                        name=f"📍 {region} (Part {part_num})" if part_num > 1 else f"📍 {region}",
                        value=current_part,
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"📍 {region}",
                    value=candidate_list,
                    inline=False
                )

        # Summary statistics
        total_candidates = len(general_candidates)
        total_regions = len(regions)
        avg_stamina = sum(c.get('stamina', 100) for c in general_candidates) / total_candidates if total_candidates else 0
        avg_corruption = sum(c.get('corruption', 0) for c in general_candidates) / total_candidates if total_candidates else 0
        total_campaign_points = sum(c.get('points', 0) for c in general_candidates)

        embed.add_field(
            name="📊 Campaign Summary",
            value=f"**Total Candidates:** {total_candidates}\n"
                  f"**Regions Represented:** {total_regions}\n"
                  f"**Average Stamina:** {avg_stamina:.1f}\n"
                  f"**Average Corruption:** {avg_corruption:.1f}\n"
                  f"**Total Campaign Points:** {total_campaign_points:.2f}",
            inline=False
        )

        if target_year % 2 == 0 and not year:  # Even year, showing previous year's winners
            embed.set_footer(text=f"Showing {primary_year} primary winners advancing to {target_year} general election")
        else:
            embed.set_footer(text=f"General campaign candidates for {target_year}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_export_winners",
        description="Export winners data (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_export_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        winner_type: str = "all"  # "primary", "general", or "all"
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Filter winners
        winners = [w for w in winners_config["winners"] if w["year"] == target_year]

        if winner_type.lower() == "primary":
            winners = [w for w in winners if w.get("primary_winner", False)]
        elif winner_type.lower() == "general":
            winners = [w for w in winners if w.get("general_winner", False)]

        if not winners:
            await interaction.response.send_message(
                f"❌ No {winner_type} winners found for {target_year}.",
                ephemeral=True
            )
            return

        # Create CSV format
        lines = ["year,user_id,office,state,seat_id,candidate,party,points,baseline_percentage,votes,corruption,final_percentage,stamina,winner"]

        for winner in winners:
            lines.append(
                f"{winner['year']},{winner['user_id']},{winner['office']},{winner['state']},"
                f"{winner['seat_id']},{winner['candidate']},{winner['party']},{winner['points']},"
                f"{winner.get('baseline_percentage', 0)},{winner['votes']},{winner['corruption']},{winner.get('final_percentage', 0)},"
                f"{winner['stamina']},{winner.get('general_winner', False)}"
            )

        export_text = "\n".join(lines)

        # Handle long responses
        if len(export_text) > 1900:
            chunk_size = 1900
            chunks = [export_text[i:i+chunk_size] for i in range(0, len(export_text), chunk_size)]

            await interaction.response.send_message(
                f"📊 {target_year} {winner_type.title()} Winners Export - Part 1/{len(chunks)}:\n```csv\n{chunks[0]}\n```",
                ephemeral=True
            )

            for i, chunk in enumerate(chunks[1:], 2):
                await interaction.followup.send(
                    f"📊 Part {i}/{len(chunks)}:\n```csv\n{chunk}\n```",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"📊 {target_year} {winner_type.title()} Winners Export:\n```csv\n{export_text}\n```",
                ephemeral=True
            )

async def setup(bot):
    print("Loading AllWinners cog...")
    await bot.add_cog(AllWinners(bot))