from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
from datetime import datetime

class CampaignPointsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, sort_by: str, filter_state: str, filter_party: str, year: int, total_pages: int, current_page: int):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.sort_by = sort_by
        self.filter_state = filter_state
        self.filter_party = filter_party
        self.year = year
        self.total_pages = total_pages
        self.current_page = current_page

        # Add page selector dropdown
        self.add_item(PageSelector(total_pages, current_page))

class PageSelector(discord.ui.Select):
    def __init__(self, total_pages: int, current_page: int):
        # Create options for page selection
        options = []

        # Show all pages if 25 or fewer, otherwise show smart selection
        if total_pages <= 25:
            for page in range(1, total_pages + 1):
                label = f"Page {page}"
                if page == current_page:
                    label += " (Current)"
                options.append(discord.SelectOption(
                    label=label,
                    value=str(page),
                    default=(page == current_page)
                ))
        else:
            # For many pages, show first few, current area, and last few
            pages_to_show = set()

            # First 3 pages
            pages_to_show.update(range(1, min(4, total_pages + 1)))

            # Current page and neighbors
            start = max(1, current_page - 2)
            end = min(total_pages + 1, current_page + 3)
            pages_to_show.update(range(start, end))

            # Last 3 pages
            pages_to_show.update(range(max(1, total_pages - 2), total_pages + 1))

            sorted_pages = sorted(pages_to_show)

            for page in sorted_pages:
                label = f"Page {page}"
                if page == current_page:
                    label += " (Current)"
                options.append(discord.SelectOption(
                    label=label,
                    value=str(page),
                    default=(page == current_page)
                ))

        super().__init__(
            placeholder=f"Jump to page... (Current: {current_page}/{total_pages})",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_page = int(self.values[0])
        await interaction.response.defer()

        # Get the cog and regenerate the page content
        cog = interaction.client.get_cog('AllWinners')
        if not cog:
            await interaction.followup.send("❌ Error: Cog not found", ephemeral=True)
            return

        # Get time and winners config
        time_col, time_config = cog._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.followup.send("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        target_year = self.view.year if self.view.year else current_year

        winners_col, winners_config = cog._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general election)
        candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        # Apply filters
        if self.view.filter_state:
            candidates = [c for c in candidates if self.view.filter_state.upper() in c.get("seat_id", "")]
        if self.view.filter_party:
            candidates = [c for c in candidates if self.view.filter_party.lower() in c.get("party", "").lower()]

        # Sort candidates
        if self.view.sort_by == "points":
            candidates.sort(key=lambda x: x.get("points", 0), reverse=True)
        elif self.view.sort_by == "total_points":
            candidates.sort(key=lambda x: x.get("total_points", 0), reverse=True)
        elif self.view.sort_by == "corruption":
            candidates.sort(key=lambda x: x.get("corruption", 0), reverse=True)
        elif self.view.sort_by == "seat":
            candidates.sort(key=lambda x: x.get("seat_id", ""))
        elif self.view.sort_by == "name":
            candidates.sort(key=lambda x: x.get("candidate", ""))

        # Pagination
        candidates_per_page = 10
        total_pages = max(1, (len(candidates) + candidates_per_page - 1) // candidates_per_page)
        start_idx = (selected_page - 1) * candidates_per_page
        end_idx = start_idx + candidates_per_page
        page_candidates = candidates[start_idx:end_idx]

        # Calculate percentages if in General Campaign
        if current_phase == "General Campaign":
            for candidate in page_candidates:
                percentages = cog._calculate_zero_sum_percentages(interaction.guild.id, candidate.get("seat_id", ""))
                candidate['calculated_percentage'] = percentages.get(candidate.get("candidate", ""), 50.0)

        # Create embed
        embed = discord.Embed(
            title=f"📊 {target_year} General Campaign Points",
            description=f"Sorted by {self.view.sort_by} • Page {selected_page}/{total_pages} • {len(candidates)} total candidates",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Build candidate list
        candidate_entries = []
        for i, candidate in enumerate(page_candidates, start_idx + 1):
            user = interaction.guild.get_member(candidate.get("user_id"))
            user_mention = user.mention if user else candidate.get("candidate", "Unknown")

            points_display = f"{candidate.get('points', 0):.2f}"
            if current_phase == "General Campaign":
                total_points = candidate.get('total_points', 0)
                if total_points > 0:
                    points_display = f"{total_points:.2f}"

                percentage = candidate.get('calculated_percentage', 50.0)
                points_display += f" ({percentage:.1f}%)"

            entry = (
                f"**{i}.** {candidate.get('candidate', 'Unknown')} ({candidate.get('party', 'Unknown')})\n"
                f"   └ {candidate.get('seat_id', 'Unknown')} • Points: {points_display}\n"
                f"   └ Stamina: {candidate.get('stamina', 100)} • "
                f"Corruption: {candidate.get('corruption', 0)} • {user_mention}"
            )
            candidate_entries.append(entry)

        # Split into fields to handle Discord's field limits
        field_content = ""
        field_count = 1
        for entry in candidate_entries:
            if len(field_content + entry + "\n\n") > 1024:
                embed.add_field(
                    name=f"🏆 Candidates{f' (Part {field_count})' if field_count > 1 else ''}",
                    value=field_content,
                    inline=False
                )
                field_content = entry + "\n\n"
                field_count += 1
            else:
                field_content += entry + "\n\n"

        if field_content:
            embed.add_field(
                name=f"🏆 Candidates{f' (Part {field_count})' if field_count > 1 else ''}",
                value=field_content,
                inline=False
            )

        # Add statistics
        if candidates:
            total_points = sum(c.get("points", 0) for c in candidates)
            total_votes = sum(c.get("votes", 0) for c in candidates)
            avg_corruption = sum(c.get("corruption", 0) for c in candidates) / len(candidates)

            embed.add_field(
                name="📈 Summary Statistics",
                value=f"**Total Candidates:** {len(candidates)}\n"
                      f"**Total Points:** {total_points:.2f}\n"
                      f"**Total Votes:** {total_votes:,}\n"
                      f"**Avg Corruption:** {avg_corruption:.1f}",
                inline=True
            )

        # Show filter info if applied
        filter_info = ""
        if self.view.filter_state:
            filter_info += f"State: {self.view.filter_state} • "
        if self.view.filter_party:
            filter_info += f"Party: {self.view.filter_party} • "
        if filter_info:
            embed.add_field(
                name="🔍 Active Filters",
                value=filter_info.rstrip(" • "),
                inline=True
            )

        # Navigation info
        navigation_info = f"**Page {selected_page} of {total_pages}**\n"
        if selected_page > 1:
            navigation_info += f"Use `page:{selected_page-1}` for previous page\n"
        if selected_page < total_pages:
            navigation_info += f"Use `page:{selected_page+1}` for next page\n"
        navigation_info += f"Showing candidates {start_idx + 1}-{min(end_idx, len(candidates))}"

        embed.add_field(
            name="📄 Navigation",
            value=navigation_info,
            inline=False
        )

        # Create new view with updated page
        new_view = CampaignPointsView(
            interaction,
            self.view.sort_by,
            self.view.filter_state,
            self.view.filter_party,
            self.view.year,
            total_pages,
            selected_page
        )

        await interaction.edit_original_response(embed=embed, view=new_view)

class GeneralCampaignRegionDropdown(discord.ui.Select):
    def __init__(self, regions, candidates_by_region, year, seat_percentages_cache):
        self.candidates_by_region = candidates_by_region
        self.year = year
        self.seat_percentages_cache = seat_percentages_cache

        options = [
            discord.SelectOption(
                label="🌍 All Regions",
                description="View candidates from all regions",
                value="all",
                emoji="🌍"
            )
        ]

        # Add region options with candidate counts
        for region in sorted(regions.keys()):
            candidate_count = len(regions[region])
            options.append(
                discord.SelectOption(
                    label=f"📍 {region}",
                    description=f"{candidate_count} candidate{'s' if candidate_count != 1 else ''}",
                    value=region
                )
            )

        super().__init__(placeholder="Select a region to view candidates...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_region = self.values[0]

            if selected_region == "all":
                # Show overview of all regions
                embed = discord.Embed(
                    title=f"🎯 {self.year} General Campaign - All Regions",
                    description="Primary winners advancing to general election",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )

                # Add summary for each region
                for region, candidates in sorted(self.candidates_by_region.items()):
                    candidate_list = ""
                    for candidate in sorted(candidates, key=lambda x: x.get("points", 0), reverse=True)[:5]:
                        candidate_name = candidate.get('candidate', 'Unknown')
                        candidate_party = candidate.get('party', 'Unknown')
                        candidate_seat = candidate.get('seat_id', 'Unknown')
                        candidate_list += f"• **{candidate_name}** ({candidate_party}) - {candidate_seat}\n"

                    if len(candidates) > 5:
                        candidate_list += f"• ... and {len(candidates) - 5} more"

                    embed.add_field(
                        name=f"📍 {region} ({len(candidates)} candidates)",
                        value=candidate_list or "No candidates",
                        inline=True
                    )
            else:
                # Show detailed view for selected region
                candidates = self.candidates_by_region.get(selected_region, [])

                embed = discord.Embed(
                    title=f"🎯 {self.year} General Campaign - {selected_region}",
                    description=f"Primary winners from {selected_region} advancing to general election",
                    color=discord.Color.purple(),
                    timestamp=datetime.utcnow()
                )

                if not candidates:
                    embed.add_field(
                        name="📋 No Candidates",
                        value=f"No candidates found for {selected_region}",
                        inline=False
                    )
                else:
                    # Group candidates by seat for proper percentage calculation
                    seats_in_region = {}
                    for candidate in candidates:
                        seat_id = candidate.get("seat_id", "Unknown")
                        if seat_id not in seats_in_region:
                            seats_in_region[seat_id] = []
                        seats_in_region[seat_id].append(candidate)

                    candidate_list = ""
                    for seat_id, seat_candidates in sorted(seats_in_region.items()):
                        seat_percentages = self.seat_percentages_cache.get(seat_id, {})

                        for candidate in sorted(seat_candidates, key=lambda x: x.get("points", 0), reverse=True):
                            # Safely get candidate data
                            candidate_name = candidate.get("candidate", "Unknown")
                            candidate_party = candidate.get("party", "Unknown")
                            candidate_office = candidate.get("office", "Unknown")
                            candidate_points = candidate.get("points", 0)
                            candidate_stamina = candidate.get("stamina", 100)
                            candidate_corruption = candidate.get("corruption", 0)
                            
                            # Get user mention
                            user_id = candidate.get("user_id")
                            user_mention = f"<@{user_id}>" if user_id else "No user"

                            # Get percentage for this candidate
                            candidate_percentage = seat_percentages.get(candidate_name, 50.0)

                            candidate_list += (
                                f"**{candidate_name}** ({candidate_party})\n"
                                f"└ {seat_id} - {candidate_office}\n"
                                f"└ Points: {candidate_points:.2f} | Stamina: {candidate_stamina}\n"
                                f"└ Percentage: {candidate_percentage:.1f}% | Corruption: {candidate_corruption}\n"
                                f"└ {user_mention}\n\n"
                            )

                    # Handle long content by splitting into multiple fields
                    if len(candidate_list) > 1024:
                        parts = candidate_list.split('\n\n')
                        current_part = ""
                        part_num = 1

                        for part in parts:
                            if part.strip():  # Skip empty parts
                                if len(current_part + part + '\n\n') > 1024:
                                    if current_part.strip():
                                        embed.add_field(
                                            name=f"📊 Candidates (Part {part_num})",
                                            value=current_part.strip(),
                                            inline=False
                                        )
                                    current_part = part + '\n\n'
                                    part_num += 1
                                else:
                                    current_part += part + '\n\n'

                        if current_part.strip():
                            embed.add_field(
                                name=f"📊 Candidates (Part {part_num})" if part_num > 1 else "📊 Candidates",
                                value=current_part.strip(),
                                inline=False
                            )
                    else:
                        embed.add_field(
                            name="📊 Candidates",
                            value=candidate_list.strip() if candidate_list.strip() else "No candidates found",
                            inline=False
                        )

                    # Add region statistics
                    if candidates:
                        total_points = sum(c.get('points', 0) for c in candidates)
                        avg_stamina = sum(c.get('stamina', 100) for c in candidates) / len(candidates)
                        avg_corruption = sum(c.get('corruption', 0) for c in candidates) / len(candidates)

                        embed.add_field(
                            name="📈 Region Statistics",
                            value=f"**Total Candidates:** {len(candidates)}\n"
                                  f"**Total Campaign Points:** {total_points:.2f}\n"
                                  f"**Average Stamina:** {avg_stamina:.1f}\n"
                                  f"**Average Corruption:** {avg_corruption:.1f}",
                            inline=False
                        )

            embed.set_footer(text=f"Use the dropdown to view other regions • Year: {self.year}")
            await interaction.response.edit_message(embed=embed, view=self.view)

        except Exception as e:
            print(f"Error in GeneralCampaignRegionDropdown callback: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred while switching regions: {str(e)}", 
                ephemeral=True
            )

class GeneralCampaignRegionView(discord.ui.View):
    def __init__(self, regions, candidates_by_region, year, seat_percentages_cache):
        super().__init__(timeout=300)
        self.add_item(GeneralCampaignRegionDropdown(regions, candidates_by_region, year, seat_percentages_cache))

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
        if old_phase == "Primary Campaign" and new_phase == "Primary Election":
            # Process signups from the current year for primary elections
            # In odd years (1999), process 1999 signups for 2000 elections
            # In even years (2000), process signups from the same year
            if current_year % 2 == 1:  # Odd year (1999)
                signup_year = current_year
                election_year = current_year + 1
            else:  # Even year (2000)
                signup_year = current_year - 1
                election_year = current_year

            await self._process_primary_winners(guild_id, signup_year, election_year)

        elif old_phase == "Primary Election" and new_phase == "General Campaign":
            # Ensure primary winners are ready for general campaign
            # Use the current year as election year for finding primary winners
            await self._ensure_general_campaign_candidates(guild_id, current_year)

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

    def _calculate_zero_sum_percentages(self, guild_id: int, seat_id: str):
        """Calculate final percentages for candidates in a seat with zero-sum redistribution"""
        winners_col, winners_config = self._get_winners_config(guild_id)

        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year

        # Find all primary winners for this seat for the current year
        seat_candidates = [
            w for w in winners_config.get("winners", [])
            if w["seat_id"] == seat_id and w["year"] == current_year and w.get("primary_winner", False)
        ]

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

        # Step 1: Calculate each candidate's raw change (a_i)
        raw_changes = {}
        B = 100.0  # Total baseline percentage

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]

            # a_i = (p_i / 1200) - (0.1 * c_i)
            points_change = candidate.get("points", 0.0) / 1200.0
            corruption_penalty = candidate.get("corruption", 0) * 0.1
            raw_change = points_change - corruption_penalty

            raw_changes[candidate_name] = raw_change

        # Step 2: Calculate net change across all candidates (s)
        net_change_s = sum(raw_changes.values())

        # Step 3: Apply zero-sum redistribution formula
        final_percentages = {}

        for candidate in seat_candidates:
            party = candidate["party"]
            candidate_name = candidate["candidate"]

            # Final_i = b_i + a_i - (b_i / B) * s
            baseline_bi = baseline_percentages[party]
            raw_change_ai = raw_changes[candidate_name]
            redistribution = (baseline_bi / B) * net_change_s

            final_percentage = baseline_bi + raw_change_ai - redistribution

            # Ensure minimum percentage (optional guardrail)
            final_percentage = max(0.1, final_percentage)
            final_percentages[candidate_name] = final_percentage

        # COMPLETE 100% NORMALIZATION - Force total to exactly 100%
        total_percentage = sum(final_percentages.values())
        if total_percentage > 0:
            for candidate_name in final_percentages:
                final_percentages[candidate_name] = (final_percentages[candidate_name] / total_percentage) * 100.0

        # Final verification and correction for floating point errors
        final_total = sum(final_percentages.values())
        if abs(final_total - 100.0) > 0.001:
            # Apply micro-adjustment to the largest percentage
            largest_candidate = max(final_percentages.keys(), key=lambda x: final_percentages[x])
            adjustment = 100.0 - final_total
            final_percentages[largest_candidate] += adjustment

        return final_percentages

    def _calculate_baseline_percentage(self, guild_id: int, seat_id: str, candidate_party: str):
        """Calculate baseline starting percentage for general election based on party distribution"""
        # Get all primary winners for this seat
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

        # Calculate baseline percentages based on party specifications
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

    async def _process_primary_winners(self, guild_id: int, signup_year: int, election_year: int = None):
        """Process primary winners from signups"""
        if election_year is None:
            # Default logic: if signup_year is odd (1999), election_year is next even year (2000)
            # if signup_year is even (2000), election_year is the same year (2000)
            if signup_year % 2 == 1:  # Odd year
                election_year = signup_year + 1
            else:  # Even year
                election_year = signup_year

        signups_col, signups_config = self._get_signups_config(guild_id)
        winners_col, winners_config = self._get_winners_config(guild_id)

        if not signups_config:
            return

        # Get all candidates for the signup year (previous year for even election years)
        candidates = [c for c in signups_config.get("candidates", []) if c["year"] == signup_year]

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
        try:
            from cogs.ideology import STATE_DATA, calculate_region_medians, STATE_TO_SEAT
        except ImportError:
            print("Could not import ideology data. Ideology-based points will not be calculated.")
            STATE_DATA, calculate_region_medians, STATE_TO_SEAT = {}, lambda: {}, {}

        # Get region medians for senate/governor seats
        region_medians = calculate_region_medians()

        # Determine winner for each party in each seat
        for key, party_candidates in seat_party_groups.items():
            if len(party_candidates) == 1:
                # Only one candidate, automatic winner
                winner = party_candidates[0]
            else:
                # Multiple candidates, highest points wins
                winner = max(party_candidates, key=lambda x: x.get("points", 0))

            # Calculate baseline percentage for general election
            baseline_percentage = self._calculate_baseline_percentage(guild_id, winner["seat_id"], winner["party"])

            # Create winner entry
            winner_entry = {
                "year": election_year,  # Use election year, not signup year
                "user_id": winner["user_id"],
                "office": winner["office"],
                "state": winner.get("region", "Unknown State"), # Use 'region' from signup if available
                "seat_id": winner["seat_id"],
                "candidate": winner["name"],
                "party": winner["party"],
                "points": 0.0,  # Reset campaign points for general election
                "baseline_percentage": baseline_percentage,  # Store ideology-based baseline
                "votes": 0,   # To be input by admins
                "corruption": winner.get("corruption", 0),  # Keep corruption level
                "final_score": 0,  # Calculated later
                "stamina": winner.get("stamina", 100),
                "winner": False,  # TBD after general election
                "phase": "Primary Winner",
                "primary_winner": True,
                "general_winner": False,
                "created_date": datetime.utcnow()
            }

            primary_winners.append(winner_entry)

        # Add winners to database
        if primary_winners:
            if "winners" not in winners_config:
                winners_config["winners"] = []
            winners_config["winners"].extend(primary_winners)
            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        # Send announcement
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._announce_primary_results(guild, primary_winners, election_year)

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
        except Exception as e:
            print(f"Error sending primary results announcement: {e}")

    async def _ensure_general_campaign_candidates(self, guild_id: int, current_year: int):
        """Ensure primary winners are properly transitioned to general campaign"""
        winners_col, winners_config = self._get_winners_config(guild_id)

        # For general campaign phase, we need to look for primary winners
        # If current_year is even (2000), we look for primary winners from the same year
        # If current_year is odd (1999), we look for primary winners from the same year
        primary_winners = [
            w for w in winners_config.get("winners", [])
            if w.get("year") == current_year and w.get("primary_winner", False)
        ]

        if not primary_winners:
            print(f"No primary winners found for general campaign transition in guild {guild_id} for year {current_year}")
            return

        # Reset points and stamina for general campaign
        updated_count = 0
        for i, winner in enumerate(winners_config["winners"]):
            if (winner.get("year") == current_year and
                winner.get("primary_winner", False) and
                winner.get("phase") != "General Campaign"):

                winners_config["winners"][i]["points"] = 0.0  # Reset points for general campaign
                winners_config["winners"][i]["stamina"] = 100  # Reset stamina
                winners_config["winners"][i]["phase"] = "General Campaign"
                updated_count += 1

        if updated_count > 0:
            winners_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"winners": winners_config["winners"]}}
            )
            print(f"Updated {updated_count} primary winners for general campaign in guild {guild_id}")

        # Also ensure presidential candidates are transitioned
        await self._ensure_presidential_general_campaign_candidates(guild_id, current_year)

    async def _ensure_presidential_general_campaign_candidates(self, guild_id: int, current_year: int):
        """Ensure presidential primary winners are transitioned to general campaign"""
        # Get presidential signups and check for primary winners
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})

        if not pres_signups_config:
            return

        # Get presidential winners from the presidential_winners collection
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_config = pres_winners_col.find_one({"guild_id": guild_id})

        if not pres_winners_config or not pres_winners_config.get("winners"):
            return

        # Reset points and stamina for presidential candidates in general campaign
        candidates_updated = []
        for i, candidate in enumerate(pres_signups_config.get("candidates", [])):
            if (candidate.get("year") == current_year and
                candidate.get("office") in ["President", "Vice President"] and
                candidate.get("phase") != "General Campaign"):

                # Check if this candidate is a primary winner
                candidate_party = candidate.get("party", "")
                candidate_name = candidate.get("name", "")

                # Map party names for presidential winners
                party_key = None
                if "Democratic" in candidate_party:
                    party_key = "Democrats"
                elif "Republican" in candidate_party:
                    party_key = "Republican"
                else:
                    party_key = "Others"

                if party_key and pres_winners_config["winners"].get(party_key) == candidate_name:
                    # This candidate is a primary winner, reset for general campaign
                    pres_signups_config["candidates"][i]["points"] = 0.0
                    pres_signups_config["candidates"][i]["stamina"] = 200  # Presidential candidates get higher stamina
                    pres_signups_config["candidates"][i]["phase"] = "General Campaign"
                    candidates_updated.append(candidate_name)

        if candidates_updated:
            pres_signups_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"candidates": pres_signups_config["candidates"]}}
            )
            print(f"Updated {len(candidates_updated)} presidential primary winners for general campaign: {candidates_updated}")

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
        current_phase = time_config.get("current_phase", "")

        # Look for primary winners for the specified year or current year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Filter primary winners for target year
        primary_winners = [
            w for w in winners_config.get("winners", [])
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
                winner_list += f"└ Points: {winner.get('points', 0):.2f} | Stamina: {winner.get('stamina', 100)} | Corruption: {winner.get('corruption', 0)}\n"
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
        winner_found_index = -1
        for i, winner in enumerate(winners_config.get("winners", [])):
            if (winner["candidate"].lower() == candidate_name.lower() and
                winner["year"] == target_year and
                winner.get("primary_winner", False)):
                winner_found_index = i
                break

        if winner_found_index == -1:
            await interaction.response.send_message(
                f"❌ Primary winner '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        old_votes = winners_config["winners"][winner_found_index]["votes"]
        winners_config["winners"][winner_found_index]["votes"] = votes

        # Find all candidates in the same seat to recalculate percentages
        winner_data = winners_config["winners"][winner_found_index]
        seat_id = winner_data["seat_id"]
        seat_candidates = [
            w for w in winners_config.get("winners", [])
            if w["seat_id"] == seat_id and w["year"] == target_year and w.get("primary_winner", False)
        ]

        # Recalculate percentages for the entire seat
        percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)

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

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners for target year
        primary_winners = [
            w for w in winners_config.get("winners", [])
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
            percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)

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

        # Apply ideology shifts for winners
        try:
            from cogs.ideology import shift_state_ideology_for_winner
            for winner in general_winners:
                shift_state_ideology_for_winner(winner, shift_amount=1.0)
            print(f"Applied ideology shifts for {len(general_winners)} election winners")
        except Exception as e:
            print(f"Error applying ideology shifts: {e}")

        # Update database
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        # Update election seats with new holders
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)

        if elections_config and "seats" in elections_config:
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
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("general_winner", False)
        ]

        # If no declared winners, check for general campaign candidates (primary winners)
        if not general_winners:
            # For even years (general election), look at previous year's primary winners
            primary_year = target_year - 1 if target_year % 2 == 0 else target_year

            campaign_candidates = [
                w for w in winners_config.get("winners", [])
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
                winner_list += f"└ Points: {winner.get('points', 0):.2f} | Votes: {winner['votes']} | Corruption: {winner.get('corruption', 0)}\n\n"

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

        # Calculate primary_year based on current_year
        primary_year = current_year - 1 if current_year % 2 == 0 else current_year
        embed.set_footer(text=f"Showing {primary_year} primary winners advancing to {target_year} general election")

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
                for i, winner in enumerate(winners_config.get("winners", [])):
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
                        w for w in winners_config.get("winners", [])
                        if w["seat_id"] == seat_id and w["year"] == target_year and w.get("primary_winner", False)
                    ]
                    percentages = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)

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
        name="admin_view_all_campaign_points",
        description="View all candidate points in general campaign phase (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_all_campaign_points(
        self,
        interaction: discord.Interaction,
        sort_by: str = "points",
        filter_state: str = None,
        filter_party: str = None,
        year: int = None,
        page: int = 1
    ):
        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.followup.send("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get primary winners (candidates in general election)
        candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not candidates:
            await interaction.followup.send(
                f"❌ No general election candidates found for {target_year}.",
                ephemeral=True
            )
            return

        # Apply filters
        if filter_state:
            candidates = [c for c in candidates if c.get("state", "").lower() == filter_state.lower()]

        if filter_party:
            candidates = [c for c in candidates if c.get("party", "").lower() == filter_party.lower()]

        if not candidates:
            await interaction.followup.send(
                "❌ No candidates found with those filters.",
                ephemeral=True
            )
            return

        # Sort candidates
        if sort_by.lower() == "points":
            candidates.sort(key=lambda x: x.get("points", 0), reverse=True)
        elif sort_by.lower() == "votes":
            candidates.sort(key=lambda x: x.get("votes", 0), reverse=True)
        elif sort_by.lower() == "final_percentage":
            candidates.sort(key=lambda x: x.get("final_percentage", 0), reverse=True)
        elif sort_by.lower() == "corruption":
            candidates.sort(key=lambda x: x.get("corruption", 0), reverse=True)
        elif sort_by.lower() == "stamina":
            candidates.sort(key=lambda x: x.get("stamina", 100), reverse=True)
        else:
            candidates.sort(key=lambda x: x.get("candidate", "").lower())

        # Pagination setup - reduced for better field handling
        candidates_per_page = 10
        total_pages = (len(candidates) + candidates_per_page - 1) // candidates_per_page
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * candidates_per_page
        end_idx = start_idx + candidates_per_page
        page_candidates = candidates[start_idx:end_idx]

        # Pre-calculate zero-sum percentages for unique seats only
        unique_seats = list(set(c.get("seat_id") for c in page_candidates if c.get("seat_id")))
        seat_percentages_cache = {}

        for seat_id in unique_seats:
            if seat_id and seat_id != "N/A":
                try:
                    seat_percentages_cache[seat_id] = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)
                except Exception as e:
                    print(f"Error calculating percentages for seat {seat_id}: {e}")
                    seat_percentages_cache[seat_id] = {}

        # Apply calculated percentages to candidates
        for candidate in page_candidates:
            seat_id = candidate.get('seat_id')
            candidate_name = candidate.get('candidate', '')
            if seat_id in seat_percentages_cache:
                candidate['calculated_percentage'] = seat_percentages_cache[seat_id].get(candidate_name, 50.0)
            else:
                candidate['calculated_percentage'] = 50.0

        # Create embed
        embed = discord.Embed(
            title=f"📊 {target_year} General Campaign Points",
            description=f"Sorted by {sort_by} • Page {page}/{total_pages} • {len(candidates)} total candidates",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Build candidate list with field splitting for large lists
        candidate_entries = []
        for i, candidate in enumerate(page_candidates, start_idx + 1):
            # Get user info
            user = interaction.guild.get_member(candidate.get("user_id"))
            user_mention = user.mention if user else candidate.get("candidate", "Unknown")

            points_display = f"{candidate.get('points', 0):.2f}"
            if current_phase == "General Campaign":
                total_points = candidate.get('total_points', 0)
                if total_points > 0:
                    points_display = f"{total_points:.2f}"

                # Show percentage if available
                percentage = candidate.get('calculated_percentage', 50.0)
                points_display += f" ({percentage:.1f}%)"

            entry = (
                f"**{i}.** {candidate.get('candidate', 'Unknown')} ({candidate.get('party', 'Unknown')})\n"
                f"   └ {candidate.get('seat_id', 'N/A')} • Points: {points_display}\n"
                f"   └ Stamina: {candidate.get('stamina', 100)} • Corruption: {candidate.get('corruption', 0)} • {user_mention}\n\n"
            )
            candidate_entries.append(entry)

        # Split candidates into multiple fields if needed (Discord 1024 char limit per field)
        current_field = ""
        field_count = 1

        for entry in candidate_entries:
            # Check if adding this entry would exceed the limit
            if len(current_field + entry) > 1020:  # Leave some buffer
                # Add the current field and start a new one
                embed.add_field(
                    name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                    value=current_field.strip() if current_field.strip() else "No candidates found",
                    inline=False
                )
                current_field = entry
                field_count += 1
            else:
                current_field += entry

        # Add any remaining candidates
        if current_field:
            embed.add_field(
                name=f"🏆 Candidates (Part {field_count})" if field_count > 1 else "🏆 Candidates",
                value=current_field.strip() if current_field.strip() else "No candidates found",
                inline=False
            )
        elif not candidate_entries:
            embed.add_field(
                name="🏆 Candidates",
                value="No candidates found",
                inline=False
            )

        # Summary statistics
        total_votes = sum(c.get("votes", 0) for c in candidates)
        total_points = sum(c.get("points", 0) for c in candidates)
        avg_corruption = sum(c.get("corruption", 0) for c in candidates) / len(candidates) if candidates else 0

        embed.add_field(
            name="📈 Summary Statistics",
            value=f"**Total Candidates:** {len(candidates)}\n"
                  f"**Total Points:** {total_points:.2f}\n"
                  f"**Total Votes:** {total_votes:,}\n"
                  f"**Avg Corruption:** {avg_corruption:.1f}",
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

        # Navigation info
        navigation_info = f"**Page {page} of {total_pages}**\n"
        if page > 1:
            navigation_info += f"Use `page:{page-1}` for previous page\n"
        if page < total_pages:
            navigation_info += f"Use `page:{page+1}` for next page\n"
        navigation_info += f"Showing candidates {start_idx + 1}-{min(end_idx, len(candidates))}"

        embed.add_field(
            name="📄 Navigation",
            value=navigation_info,
            inline=False
        )

        # Create dropdown for quick navigation if many pages
        if total_pages > 1:
            view = CampaignPointsView(interaction, sort_by, filter_state, filter_party, year, total_pages, page)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

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
        for w in winners_config.get("winners", []):
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
            value=f"**Points:** {candidate.get('points', 0):.2f}\n"
                  f"**Votes:** {candidate.get('votes', 0):,}\n"
                  f"**Final Percentage:** {candidate.get('final_percentage', 0):.2f}%\n"
                  f"**Stamina:** {candidate.get('stamina', 100)}/100",
            inline=True
        )

        embed.add_field(
            name="⚖️ Status",
            value=f"**Corruption:** {candidate.get('corruption', 0)}\n"
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
        score_breakdown += f"+ Points to % ({candidate.get('points', 0):.2f}): {(candidate.get('points', 0) / 1200.0):.2f}%\n"
        score_breakdown += f"- Corruption ({candidate.get('corruption', 0)}): {(candidate.get('corruption', 0) * 0.1):.1f}%\n"
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
    async def admin_force_primary_winners(
        self,
        interaction: discord.Interaction,
        signup_year: int = None,
        confirm: bool = False
    ):
        """Manually trigger primary winner processing"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        # Default to processing previous year's signups for current year elections
        target_signup_year = signup_year if signup_year else (current_year - 1 if current_year % 2 == 0 else current_year)

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will process all signups from {target_signup_year} and declare primary winners for {current_year} elections.\n"
                f"This will move candidates from signups to winners with ideology-based points.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        await self._process_primary_winners(interaction.guild.id, target_signup_year, current_year)

        await interaction.response.send_message(
            f"✅ Successfully processed primary winners from {target_signup_year} signups for {current_year} elections!\n"
            f"Check the announcements channel for results.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_transition_candidates",
        description="Manually transition candidates from signups to primary winners (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_transition_candidates(
        self,
        interaction: discord.Interaction,
        from_year: int,
        to_year: int,
        confirm: bool = False
    ):
        """Manually transition candidates between years"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will transition all candidates from {from_year} signups to {to_year} primary winners.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Get signups from from_year
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)
        candidates = [c for c in signups_config.get("candidates", []) if c["year"] == from_year]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No candidates found for {from_year}.",
                ephemeral=True
            )
            return

        # Process them as primary winners for to_year
        await self._process_primary_winners(interaction.guild.id, from_year, to_year)

        # Update the year in winners to to_year
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        updated_count = 0
        for i, winner in enumerate(winners_config.get("winners", [])):
            if winner.get("year") == to_year and winner.get("primary_winner", False):
                # This part needs careful consideration. If _process_primary_winners was just called,
                # the 'year' field should already be set to 'to_year'.
                # We are essentially ensuring that stats like points/stamina are reset for the next phase.

                # Reset stats for general campaign phase if 'to_year' is an election year
                if to_year % 2 == 0: # General Election Year
                    winners_config["winners"][i]["points"] = 0.0
                    winners_config["winners"][i]["stamina"] = 100
                    winners_config["winners"][i]["phase"] = "General Campaign"
                else: # Primary Election Year
                    # For primary election years, we might still reset points/stamina for consistency or next primary stage.
                    winners_config["winners"][i]["points"] = 0.0
                    winners_config["winners"][i]["stamina"] = 100
                    winners_config["winners"][i]["phase"] = "Primary Election"

                updated_count += 1


        if updated_count > 0:
            winners_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        await interaction.response.send_message(
            f"✅ Successfully transitioned {len(candidates)} candidates from {from_year} signups to {to_year} primary winners!\n"
            f"Updated {updated_count} winners for general campaign.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_force_year_transition",
        description="Force transition candidates from one year to another (Admin only)"
    )
    @app_commands.describe(
        from_year="Year to transition candidates from",
        to_year="Year to transition candidates to",
        confirm="Set to True to confirm the transition"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_force_year_transition(
        self,
        interaction: discord.Interaction,
        from_year: int,
        to_year: int,
        confirm: bool = False
    ):
        """Force transition all candidates from one year to another"""
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        if not confirm:
            await interaction.followup.send(
                f"⚠️ **Warning:** This will transition ALL candidates from {from_year} to {to_year}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Process signups to primary winners if needed
        signups_col, signups_config = self._get_signups_config(interaction.guild.id)

        if not signups_config:
            await interaction.followup.send("❌ No signups found.", ephemeral=True)
            return

        candidates_to_transition = [
            c for c in signups_config.get("candidates", [])
            if c["year"] == from_year
        ]

        if not candidates_to_transition:
            await interaction.followup.send(
                f"❌ No candidates found for year {from_year}.",
                ephemeral=True
            )
            return

        # Process the candidates from 'from_year' signups to become primary winners for 'to_year'
        # We need to adjust the _process_primary_winners call to reflect this
        # It expects the CURRENT election year, and it processes the PREVIOUS year's signups.
        # So, if we want to transition from year X to year Y, we call it with Y as the current year.
        await self._process_primary_winners(interaction.guild.id, from_year, to_year)


        # Update the year in winners to to_year and reset stats for general campaign phase if applicable
        winners_col, winners_config = self._get_winners_config(interaction.guild.id)
        updated_winners = 0
        for i, winner in enumerate(winners_config.get("winners", [])):
            # Check if this winner was processed from the 'from_year' signups
            # This logic assumes _process_primary_winners correctly sets the 'year' field
            if winner.get("year") == to_year and winner.get("primary_winner", False):
                 # Ensure the winner actually originated from the from_year signups.
                 # This is a bit tricky without explicitly storing the original signup year.
                 # A more robust approach might involve a temporary collection or more explicit tracking.
                 # For now, we'll assume if they are in the 'to_year' as primary winners, they are the ones we transitioned.

                 # Reset stats if the target phase is General Campaign
                 # We need to know the target phase based on 'to_year'. Assuming 'to_year' is an election year (even).
                 if to_year % 2 == 0: # General Election Year
                     winners_config["winners"][i]["points"] = 0.0
                     winners_config["winners"][i]["stamina"] = 100
                     winners_config["winners"][i]["phase"] = "General Campaign"
                 else: # Primary Election Year
                     # For primary election years, we might still reset points/stamina for consistency or next primary stage.
                     winners_config["winners"][i]["points"] = 0.0 # Reset points for next primary stage if applicable
                     winners_config["winners"][i]["stamina"] = 100 # Reset stamina
                     winners_config["winners"][i]["phase"] = "Primary Election" # Set phase appropriately

                 updated_winners += 1


        if updated_winners > 0:
            winners_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"winners": winners_config["winners"]}}
            )

        await interaction.followup.send(
            f"✅ Successfully transitioned candidates from {from_year} signups to {to_year} primary winners!\n"
            f"Updated {updated_winners} winners for the {to_year} election cycle.",
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
            year_winners = [w for w in winners_config.get("winners", []) if w["year"] == target_year]
            if not confirm:
                await interaction.response.send_message(
                    f"⚠️ **Warning:** This will permanently delete {len(year_winners)} winners for {target_year}.\n"
                    f"To confirm, run with `confirm:True`",
                    ephemeral=True
                )
                return

            winners_config["winners"] = [w for w in winners_config.get("winners", []) if w["year"] != target_year]
            cleared_count = len(year_winners)
            message = f"✅ Cleared {cleared_count} winners for {target_year}."
        else:
            # Clear all years
            all_winners_count = len(winners_config.get("winners", []))
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
        """Reset general election by clearing all primary winners"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Count winners for target year (both primary and general)
        year_winners = [w for w in winners_config.get("winners", []) if w["year"] == target_year]
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
        winners_config["winners"] = [w for w in winners_config.get("winners", []) if w["year"] != target_year]

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        # Reset election seats that were won in this year
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)

        seats_reset = 0

        if elections_config and "seats" in elections_config:
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
        # Look for primary winners with the target year (they were transitioned to have the election year)
        general_candidates = [
            w for w in winners_config.get("winners", [])
            if w["year"] == target_year and w.get("primary_winner", False)
        ]

        if not general_candidates:
            await interaction.response.send_message(
                f"📋 No candidates found in general campaign for {target_year}.",
                ephemeral=True
            )
            return

        # Defer response to prevent timeout
        await interaction.response.defer()

        # Pre-calculate all seat percentages to avoid repeated calculations
        all_seats = list(set(c["seat_id"] for c in general_candidates))
        seat_percentages_cache = {}
        for seat_id in all_seats:
            seat_percentages_cache[seat_id] = self._calculate_zero_sum_percentages(interaction.guild.id, seat_id)

        # Group by state/region
        regions = {}
        for candidate in general_candidates:
            region = candidate["state"]
            if region not in regions:
                regions[region] = []
            regions[region].append(candidate)

        # Create main overview embed
        embed = discord.Embed(
            title=f"🎯 {target_year} General Campaign Candidates",
            description=f"Primary winners advancing to general election • Current phase: **{current_phase}**\n\nUse the dropdown below to view detailed information for each region.",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Add summary information for all regions
        summary_text = ""
        total_candidates = 0
        for region, candidates in sorted(regions.items()):
            candidate_count = len(candidates)
            total_candidates += candidate_count
            summary_text += f"**{region}:** {candidate_count} candidate{'s' if candidate_count != 1 else ''}\n"

        embed.add_field(
            name="📊 Regional Summary",
            value=summary_text,
            inline=True
        )

        # Overall statistics
        avg_stamina = sum(c.get('stamina', 100) for c in general_candidates) / total_candidates if total_candidates else 0
        avg_corruption = sum(c.get('corruption', 0) for c in general_candidates) / total_candidates if total_candidates else 0
        total_campaign_points = sum(c.get('points', 0) for c in general_candidates)

        embed.add_field(
            name="📈 Overall Statistics",
            value=f"**Total Candidates:** {total_candidates}\n"
                  f"**Regions:** {len(regions)}\n"
                  f"**Avg Stamina:** {avg_stamina:.1f}\n"
                  f"**Avg Corruption:** {avg_corruption:.1f}\n"
                  f"**Total Points:** {total_campaign_points:.2f}",
            inline=True
        )

        embed.add_field(
            name="🗳️ Instructions",
            value="Select a region from the dropdown menu below to view detailed candidate information for that region.",
            inline=False
        )

        # Create the dropdown view
        view = GeneralCampaignRegionView(regions, regions, target_year, seat_percentages_cache)

        if target_year % 2 == 0 and not year:  # Even year, showing current year's winners
            embed.set_footer(text=f"Showing {target_year} primary winners advancing to general election")
        else:
            embed.set_footer(text=f"General campaign candidates for {target_year}")

        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="admin_cleanup_duplicate_winners",
        description="Remove duplicate winners entries (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_cleanup_duplicate_winners(
        self,
        interaction: discord.Interaction,
        year: int = None,
        confirm: bool = False
    ):
        """Remove duplicate winners entries for a specific year"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Get all winners for the target year
        year_winners = [w for w in winners_config.get("winners", []) if w["year"] == target_year]

        if not year_winners:
            await interaction.response.send_message(
                f"❌ No winners found for {target_year}.",
                ephemeral=True
            )
            return

        # Track unique winners by creating a key from user_id, seat_id, year, and primary_winner status
        seen_winners = {}
        cleaned_winners = []
        duplicates_removed = 0

        for winner in winners_config.get("winners", []):
            if winner["year"] != target_year:
                # Keep winners from other years as-is
                cleaned_winners.append(winner)
                continue

            # Create unique key for this year's winners
            winner_key = f"{winner['user_id']}_{winner['seat_id']}_{winner['year']}_{winner.get('primary_winner', False)}"

            if winner_key in seen_winners:
                # This is a duplicate
                duplicates_removed += 1
                continue
            else:
                # First time seeing this winner combination
                seen_winners[winner_key] = winner
                cleaned_winners.append(winner)

        if duplicates_removed == 0:
            await interaction.response.send_message(
                f"✅ No duplicate winners found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** Found {duplicates_removed} duplicate winner entries for {target_year}.\n"
                f"This will remove duplicate entries while keeping one copy of each unique winner.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Update the database
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": cleaned_winners}}
        )

        await interaction.response.send_message(
            f"✅ Cleanup complete! Removed **{duplicates_removed}** duplicate winner entries for {target_year}.\n"
            f"Remaining unique winners: **{len([w for w in cleaned_winners if w['year'] == target_year])}**",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_remove_winner",
        description="Remove a specific winner from the winners collection (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_winner(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        year: int = None,
        confirm: bool = False
    ):
        """Remove a specific winner from the winners collection"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        winners_col, winners_config = self._get_winners_config(interaction.guild.id)

        # Find the winner
        winner_found = None
        winner_index = None
        for i, winner in enumerate(winners_config.get("winners", [])):
            if (winner["candidate"].lower() == candidate_name.lower() and
                winner["year"] == target_year):
                winner_found = winner
                winner_index = i
                break

        if not winner_found:
            await interaction.response.send_message(
                f"❌ Winner '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will permanently remove **{candidate_name}** from {target_year} winners.\n"
                f"**Details:**\n"
                f"• Office: {winner_found.get('office', 'N/A')}\n"
                f"• Party: {winner_found.get('party', 'N/A')}\n"
                f"• Seat: {winner_found.get('seat_id', 'N/A')}\n"
                f"• Primary Winner: {winner_found.get('primary_winner', False)}\n"
                f"• General Winner: {winner_found.get('general_winner', False)}\n\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Remove the winner
        winners_config["winners"].pop(winner_index)

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        await interaction.response.send_message(
            f"✅ Successfully removed **{candidate_name}** from {target_year} winners.\n"
            f"Remaining winners for {target_year}: {len([w for w in winners_config['winners'] if w['year'] == target_year])}",
            ephemeral=True
        )

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
        winners = [w for w in winners_config.get("winners", []) if w["year"] == target_year]

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
                f"{winner['seat_id']},{winner['candidate']},{winner['party']},{winner.get('points', 0)},"
                f"{winner.get('baseline_percentage', 0)},{winner.get('votes', 0)},{winner.get('corruption', 0)},{winner.get('final_percentage', 0)},"
                f"{winner.get('stamina', 100)},{winner.get('general_winner', False)}"
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