
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
        """Calculate ideology-based points for a candidate based on their seat and party"""
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
            return 0  # Unknown party gets no ideology bonus
        
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
                return 0  # Fallback if state not found
                
        elif office in ["Senate", "Governor"]:
            # For Senate/Governor, use regional medians
            region = winner["region"]
            if region in region_medians:
                return region_medians[region][ideology_key]
            else:
                return 0  # Fallback if region not found
                
        else:
            # For other offices (President, VP, etc.), no ideology bonus
            return 0


    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Handle phase changes and process primary winners"""
        if old_phase == "Primary Election" and new_phase == "General Campaign":
            await self._process_primary_winners(guild_id, current_year)

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
        from ideology import STATE_DATA, calculate_region_medians, STATE_TO_SEAT
        
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
            
            # Calculate ideology-based points for general campaign
            ideology_points = self._calculate_ideology_points(winner, STATE_DATA, region_medians, STATE_TO_SEAT)
            
            # Create winner entry
            winner_entry = {
                "year": current_year,
                "user_id": winner["user_id"],
                "office": winner["office"],
                "state": winner["region"],
                "seat_id": winner["seat_id"],
                "candidate": winner["name"],
                "party": winner["party"],
                "points": ideology_points,  # Set ideology-based points for general election
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
            description="The following candidates have won their party primaries and advance to the General Election:",
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
            value=f"These {len(winners)} candidates will now compete in the General Election!\n"
                  "Points have been reset to 0 for the general campaign.",
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

        embed = discord.Embed(
            title=f"🏆 {target_year} Primary Election Winners",
            description=f"Candidates advancing to the General Election",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for state, state_winners in sorted(states.items()):
            winner_list = ""
            for winner in state_winners:
                winner_list += f"**{winner['candidate']}** ({winner['party']})\n"
                winner_list += f"└ {winner['seat_id']} - {winner['office']}\n"
                winner_list += f"└ Points: {winner['points']} | Stamina: {winner['stamina']} | Corruption: {winner['corruption']}\n\n"

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

        # Find the winner
        winner_found = None
        for i, winner in enumerate(winners_config["winners"]):
            if (winner["candidate"].lower() == candidate_name.lower() and 
                winner["year"] == target_year and
                winner.get("primary_winner", False)):
                winner_found = i
                break

        if winner_found is None:
            await interaction.response.send_message(
                f"❌ Primary winner '{candidate_name}' not found for {target_year}.",
                ephemeral=True
            )
            return

        old_votes = winners_config["winners"][winner_found]["votes"]
        winners_config["winners"][winner_found]["votes"] = votes
        
        # Recalculate final score (simple formula: points + votes - corruption)
        winner_data = winners_config["winners"][winner_found]
        final_score = winner_data["points"] + votes - winner_data["corruption"]
        winners_config["winners"][winner_found]["final_score"] = final_score

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": winners_config["winners"]}}
        )

        await interaction.response.send_message(
            f"✅ Set votes for **{candidate_name}**: {old_votes} → {votes}\n"
            f"New final score: **{final_score}**",
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
            # Find candidate with highest final score
            seat_winner = max(candidates, key=lambda x: x["final_score"])
            
            # Update winner status
            for i, winner in enumerate(winners_config["winners"]):
                if (winner["candidate"] == seat_winner["candidate"] and 
                    winner["year"] == target_year and
                    winner["seat_id"] == seat_id):
                    winners_config["winners"][i]["general_winner"] = True
                    winners_config["winners"][i]["winner"] = True
                    general_winners.append(winners_config["winners"][i])
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

        if not general_winners:
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
                winner_list += f"└ Final Score: {winner['final_score']} (P:{winner['points']} + V:{winner['votes']} - C:{winner['corruption']})\n\n"

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

        for pair in pairs:
            try:
                candidate_name, votes_str = pair.strip().split(":")
                votes = int(votes_str)

                # Find the candidate
                candidate_found = None
                for i, winner in enumerate(winners_config["winners"]):
                    if (winner["candidate"].lower() == candidate_name.lower() and 
                        winner["year"] == target_year and
                        winner.get("primary_winner", False)):
                        candidate_found = i
                        break

                if candidate_found is not None:
                    winners_config["winners"][candidate_found]["votes"] = votes
                    
                    # Recalculate final score
                    winner_data = winners_config["winners"][candidate_found]
                    final_score = winner_data["points"] + votes - winner_data["corruption"]
                    winners_config["winners"][candidate_found]["final_score"] = final_score
                    
                    updated_candidates.append(f"{candidate_name}: {votes} votes (Score: {final_score})")
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
                response += f"\n• ... and {len(updated_candidates) - 10} more"

        if errors:
            response += f"\n\n❌ Errors:\n• " + "\n• ".join(errors[:5])

        await interaction.response.send_message(response, ephemeral=True)

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
        lines = ["year,user_id,office,state,seat_id,candidate,party,points,votes,corruption,final_score,stamina,winner"]
        
        for winner in winners:
            lines.append(
                f"{winner['year']},{winner['user_id']},{winner['office']},{winner['state']},"
                f"{winner['seat_id']},{winner['candidate']},{winner['party']},{winner['points']},"
                f"{winner['votes']},{winner['corruption']},{winner['final_score']},"
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
