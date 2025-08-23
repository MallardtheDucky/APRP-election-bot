from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import math

class SeatsUpDropdown(discord.ui.Select):
    def __init__(self, office_groups, current_year):
        self.office_groups = office_groups
        self.current_year = current_year

        options = []
        for i, (office_type, seats) in enumerate(office_groups.items()):
            options.append(discord.SelectOption(
                label=f"🏛️ {office_type}",
                description=f"{len(seats)} seats up for election",
                value=str(i)
            ))

        super().__init__(placeholder="Select office type to view seats...", options=options)

    async def callback(self, interaction: discord.Interaction):
        office_type = list(self.office_groups.keys())[int(self.values[0])]
        seats = self.office_groups[office_type]

        embed = discord.Embed(
            title=f"🗳️ {office_type} Seats Up for Election ({self.current_year})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Handle House seats with potential pagination due to high count
        if office_type == "House" and len(seats) > 15:
            # Group House seats by state for better organization
            state_groups = {}
            for seat in seats:
                state = seat["state"]
                if state not in state_groups:
                    state_groups[state] = []
                state_groups[state].append(seat)

            # Add fields for each state
            for state_name, state_seats in state_groups.items():
                seat_list = ""
                for seat in state_seats:
                    incumbent = seat.get("current_holder", "Open Seat")
                    seat_list += f"• **{seat['seat_id']}** - Current: {incumbent}\n"
                
                # Ensure we don't exceed field value limit (1024 chars)
                if len(seat_list) > 1000:
                    seat_list = seat_list[:1000] + "...\n[More seats in this state]"
                
                embed.add_field(
                    name=f"📍 {state_name} ({len(state_seats)} seats)",
                    value=seat_list,
                    inline=True
                )
        else:
            # For other office types or smaller House lists, use original format
            seat_list = ""
            for seat in seats:
                incumbent = seat.get("current_holder", "Open Seat")
                seat_entry = f"• **{seat['seat_id']}** ({seat['state']})\n  Current: {incumbent}\n"
                
                # Check if adding this entry would exceed the limit
                if len(seat_list + seat_entry) > 1000:
                    seat_list += "...\n[Additional seats truncated]"
                    break
                seat_list += seat_entry

            embed.add_field(
                name=f"🏛️ {office_type} ({len(seats)} seats)",
                value=seat_list or "No seats to display",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self.view)

class SeatsUpView(discord.ui.View):
    def __init__(self, office_groups, current_year):
        super().__init__(timeout=300)
        self.office_groups = office_groups
        self.current_year = current_year
        self.add_item(SeatsUpDropdown(office_groups, current_year))

class SeatTermsDropdown(discord.ui.Select):
    def __init__(self, state_groups):
        self.state_groups = state_groups

        options = []
        for i, (state_name, seats) in enumerate(list(state_groups.items())[:25]):  # Discord limit
            options.append(discord.SelectOption(
                label=f"📍 {state_name}",
                description=f"{len(seats)} seats",
                value=str(i)
            ))

        super().__init__(placeholder="Select state to view seat terms...", options=options)

    async def callback(self, interaction: discord.Interaction):
        state_name = list(self.state_groups.keys())[int(self.values[0])]
        seats = self.state_groups[state_name]

        embed = discord.Embed(
            title=f"📅 Seat Terms: {state_name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Sort seats by term end year
        seats_with_terms = []
        seats_without_terms = []

        for seat in seats:
            if seat.get("term_end"):
                seats_with_terms.append((seat, seat["term_end"].year))
            else:
                seats_without_terms.append(seat)

        seats_with_terms.sort(key=lambda x: x[1])

        if seats_with_terms:
            term_text = ""
            for seat, year in seats_with_terms:
                holder = seat.get("current_holder", "Vacant")
                up_indicator = " 🗳️" if seat.get("up_for_election") else ""
                term_text += f"**{seat['seat_id']}** - {year}{up_indicator}\n"
                term_text += f"  {seat['office']} ({holder})\n\n"

            embed.add_field(
                name="🗓️ Seats with Set Terms",
                value=term_text[:1024],
                inline=False
            )

        if seats_without_terms:
            no_term_text = ""
            for seat in seats_without_terms:
                holder = seat.get("current_holder", "Vacant")
                up_indicator = " 🗳️" if seat.get("up_for_election") else ""
                no_term_text += f"**{seat['seat_id']}**{up_indicator} - {seat['office']} ({holder})\n"

            if no_term_text:
                embed.add_field(
                    name="❓ Seats without Set Terms",
                    value=no_term_text[:1024],
                    inline=False
                )

        embed.add_field(
            name="Legend",
            value="🗳️ = Up for election this cycle",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=self.view)

class SeatTermsView(discord.ui.View):
    def __init__(self, state_groups):
        super().__init__(timeout=300)
        self.state_groups = state_groups
        self.add_item(SeatTermsDropdown(state_groups))

class Elections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.seats_data = self._initialize_seats()
        print("Elections cog loaded successfully")

    # Create main command group
    election_group = app_commands.Group(name="election", description="Election management commands")
    
    # Create subgroups under election
    election_admin_group = app_commands.Group(name="admin", description="Election admin commands", parent=election_group)
    election_info_group = app_commands.Group(name="info", description="Election information commands", parent=election_group)
    election_seat_group = app_commands.Group(name="seat", description="Seat management commands", parent=election_group)
    election_state_group = app_commands.Group(name="state", description="State management commands", parent=election_group)
    
    # Create vote subgroup under election to consolidate commands
    election_vote_group = app_commands.Group(name="vote", description="Voting commands", parent=election_group)

    @election_vote_group.command(
        name="admin_bulk_set_votes",
        description="Set vote counts for multiple candidates (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_set_votes(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        vote_data: str
    ):
        """Set vote counts for candidates in format: candidate1:votes,candidate2:votes"""
        votes_col = self.bot.db["votes"]
        
        # Clear existing votes for this seat
        votes_col.delete_many({
            "guild_id": interaction.guild.id,
            "seat_id": seat_id.upper()
        })
        
        # Parse vote data
        vote_pairs = vote_data.split(",")
        total_votes = 0
        added_candidates = []
        
        for pair in vote_pairs:
            try:
                candidate, vote_count_str = pair.strip().split(":")
                vote_count = int(vote_count_str)
                
                # Create fake votes for this candidate
                for i in range(vote_count):
                    vote_record = {
                        "guild_id": interaction.guild.id,
                        "user_id": f"fake_voter_{seat_id}_{candidate}_{i}",  # Fake user ID
                        "seat_id": seat_id.upper(),
                        "candidate": candidate.strip(),
                        "timestamp": datetime.utcnow()
                    }
                    votes_col.insert_one(vote_record)
                
                total_votes += vote_count
                added_candidates.append(f"{candidate.strip()}: {vote_count}")
                
            except (ValueError, IndexError):
                await interaction.response.send_message(f"❌ Invalid format in: {pair}", ephemeral=True)
                return
        
        embed = discord.Embed(
            title=f"✅ Votes Set for {seat_id}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Vote Counts",
            value="\n".join(added_candidates),
            inline=False
        )
        
        embed.add_field(
            name="Total Votes",
            value=str(total_votes),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @election_vote_group.command(
        name="admin_set_winner_votes",
        description="Set election winner and vote counts for general elections (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_winner_votes(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        winner_candidate: str,
        vote_data: str
    ):
        """Set election winner and vote counts for general elections"""
        # Check if we're in general election phase
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        
        if time_config:
            current_phase = time_config.get("current_phase", "")
            if "General" not in current_phase:
                await interaction.response.send_message(
                    "⚠️ This command is intended for general elections only.",
                    ephemeral=True
                )
        
        # Set the votes using the bulk vote function
        votes_col = self.bot.db["votes"]
        
        # Clear existing votes for this seat
        votes_col.delete_many({
            "guild_id": interaction.guild.id,
            "seat_id": seat_id.upper()
        })
        
        # Parse vote data
        vote_pairs = vote_data.split(",")
        total_votes = 0
        added_candidates = []
        winner_votes = 0
        
        for pair in vote_pairs:
            try:
                candidate, vote_count_str = pair.strip().split(":")
                vote_count = int(vote_count_str)
                candidate = candidate.strip()
                
                # Track winner votes
                if candidate.lower() == winner_candidate.lower():
                    winner_votes = vote_count
                
                # Create fake votes for this candidate
                for i in range(vote_count):
                    vote_record = {
                        "guild_id": interaction.guild.id,
                        "user_id": f"fake_voter_{seat_id}_{candidate}_{i}",
                        "seat_id": seat_id.upper(),
                        "candidate": candidate,
                        "timestamp": datetime.utcnow()
                    }
                    votes_col.insert_one(vote_record)
                
                total_votes += vote_count
                added_candidates.append(f"{candidate}: {vote_count}")
                
            except (ValueError, IndexError):
                await interaction.response.send_message(f"❌ Invalid format in: {pair}", ephemeral=True)
                return
        
        # Update the seat with the winner
        col, config = self._get_elections_config(interaction.guild.id)
        
        # Find and update the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break
        
        if seat_found is not None:
            # Get current RP year for term calculation
            current_year = time_config["current_rp_date"].year if time_config else 2024
            term_start = datetime(current_year, 1, 1)
            term_end = datetime(current_year + config["seats"][seat_found]["term_years"], 1, 1)
            
            config["seats"][seat_found].update({
                "current_holder": winner_candidate,
                "current_holder_id": None,  # No real user ID for admin-set winners
                "term_start": term_start,
                "term_end": term_end,
                "up_for_election": False
            })
            
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": config["seats"]}}
            )
        
        embed = discord.Embed(
            title=f"🏆 General Election Results: {seat_id}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎉 Winner",
            value=f"**{winner_candidate}** ({winner_votes:,} votes)",
            inline=False
        )
        
        embed.add_field(
            name="📊 All Results",
            value="\n".join(added_candidates),
            inline=False
        )
        
        embed.add_field(
            name="📈 Total Votes Cast",
            value=f"{total_votes:,}",
            inline=True
        )
        
        if seat_found is not None:
            embed.add_field(
                name="🏛️ Seat Assigned",
                value=f"Winner has been assigned to {seat_id}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Automatically handle phase changes from time manager"""
        try:
            await self._handle_automatic_phase_change(guild_id, old_phase, new_phase, current_year)

            # If we're ending a General Election phase, auto-advance all term dates
            if old_phase == "General Election" and new_phase == "Signups":
                updated_seats = await self._auto_advance_terms_after_election(guild_id, current_year)
                if updated_seats:
                    print(f"Auto-advanced {len(updated_seats)} seat terms for next cycle")

        except Exception as e:
            print(f"Error handling phase change in elections: {e}")

    async def _handle_automatic_phase_change(self, guild_id: int, old_phase: str, new_phase: str, current_year: int):
        """Handle automatic election management based on phase changes"""
        col, config = self._get_elections_config(guild_id)
        guild = self.bot.get_guild(guild_id)

        if not guild:
            return

        # Get announcement channel
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild_id})
        announcement_channel_id = setup_config.get("announcement_channel") if setup_config else None

        channel = None
        if announcement_channel_id:
            channel = guild.get_channel(announcement_channel_id)
        if not channel:
            channel = discord.utils.get(guild.channels, name="general") or guild.system_channel

        # Handle different phase transitions
        if new_phase == "Signups":
            await self._handle_signups_phase(config, col, guild_id, current_year, channel)
        elif new_phase == "Primary Campaign":
            await self._handle_primary_campaign_phase(config, col, guild_id, current_year, channel)
        elif new_phase == "Primary Election":
            await self._handle_primary_election_phase(config, col, guild_id, current_year, channel)
        elif new_phase == "General Campaign":
            await self._handle_general_campaign_phase(config, col, guild_id, current_year, channel)
        elif new_phase == "General Election":
            await self._handle_general_election_phase(config, col, guild_id, current_year, channel)

    async def _handle_signups_phase(self, config, col, guild_id: int, current_year: int, channel):
        """Handle the start of signup phase - determine which seats are up for election"""
        seats_up = []

        for i, seat in enumerate(config["seats"]):
            # Check if term expires during this election cycle
            should_be_up = False

            if seat.get("term_end"):
                # Seat has an assigned term that expires at the end of next year (election year)
                # Elections are held in the year before the term expires
                if seat["term_end"].year == current_year + 1:
                    should_be_up = True
                    # Auto-advance the term end date for next cycle
                    new_term_end_year = seat["term_end"].year + seat["term_years"]
                    config["seats"][i]["term_end"] = datetime(new_term_end_year, 12, 31)
            else:
                # Seat is vacant or never been assigned - check if it should be up based on election schedule
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)

            if should_be_up and not seat.get("up_for_election"):
                config["seats"][i]["up_for_election"] = True
                seats_up.append(seat["seat_id"])

        # Update database
        col.update_one(
            {"guild_id": guild_id},
            {"$set": {"seats": config["seats"]}}
        )

        # Send announcement
        if channel and seats_up:
            embed = discord.Embed(
                title="🗳️ Election Signups Open!",
                description="The following seats are now up for election this cycle:",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Group seats by type for better display
            seat_groups = {}
            for seat_id in seats_up:
                seat = next(s for s in config["seats"] if s["seat_id"] == seat_id)
                office_type = seat["office"] if seat["office"] in ["Senate", "Governor"] else "House" if "District" in seat["office"] else "National"
                if office_type not in seat_groups:
                    seat_groups[office_type] = []
                seat_groups[office_type].append(f"{seat_id} ({seat['state']})")

            for office_type, seat_list in seat_groups.items():
                embed.add_field(
                    name=f"🏛️ {office_type}",
                    value="\n".join(seat_list),
                    inline=True
                )

            embed.add_field(
                name="📝 What's Next?",
                value="Candidates can now register for these positions during the signup phase!",
                inline=False
            )

            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _handle_primary_campaign_phase(self, config, col, guild_id: int, current_year: int, channel):
        """Handle primary campaign phase"""
        if channel:
            up_for_election = [s for s in config["seats"] if s.get("up_for_election")]

            embed = discord.Embed(
                title="🎪 Primary Campaign Phase Begins!",
                description=f"Candidates are now campaigning for the {len(up_for_election)} seats up for election!",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📢 Campaign Period",
                value="This is the time for primary candidates to make their case to voters!",
                inline=False
            )

            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _handle_primary_election_phase(self, config, col, guild_id: int, current_year: int, channel):
        """Handle primary election phase"""
        if channel:
            up_for_election = [s for s in config["seats"] if s.get("up_for_election")]

            embed = discord.Embed(
                title="🗳️ Primary Elections Now Open!",
                description=f"Voting is now open for primary elections across {len(up_for_election)} seats!",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="⏰ Voting Period",
                value="Primary elections are underway! Make your voice heard!",
                inline=False
            )

            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _handle_general_campaign_phase(self, config, col, guild_id: int, current_year: int, channel):
        """Handle general campaign phase"""
        if channel:
            up_for_election = [s for s in config["seats"] if s.get("up_for_election")]

            embed = discord.Embed(
                title="🎯 General Campaign Phase!",
                description=f"The final campaign period has begun for {len(up_for_election)} seats!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="🏁 Final Stretch",
                value="Candidates are making their final appeals before the general election!",
                inline=False
            )

            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _handle_general_election_phase(self, config, col, guild_id: int, current_year: int, channel):
        """Handle general election phase"""
        if channel:
            up_for_election = [s for s in config["seats"] if s.get("up_for_election")]

            embed = discord.Embed(
                title="🗳️ GENERAL ELECTION DAY!",
                description=f"The general election is now underway for {len(up_for_election)} seats!",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="🎉 Election Day",
                value="This is it! The final vote that will determine who represents you!",
                inline=False
            )

            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _auto_advance_terms_after_election(self, guild_id: int, current_year: int):
        """Automatically advance term end dates for seats that were up for election"""
        col, config = self._get_elections_config(guild_id)

        updated_seats = []

        for i, seat in enumerate(config["seats"]):
            if seat.get("up_for_election"):
                # Calculate new term end based on current election year + term length
                new_term_end_year = current_year + seat["term_years"] 
                config["seats"][i]["term_end"] = datetime(new_term_end_year, 12, 31)
                config["seats"][i]["up_for_election"] = False  # Reset election flag
                updated_seats.append(f"{seat['seat_id']} -> {new_term_end_year}")

        if updated_seats:
            col.update_one(
                {"guild_id": guild_id},
                {"$set": {"seats": config["seats"]}}
            )

        return updated_seats

    def _initialize_seats(self):
        """Initialize all election seats with their terms"""
        return [
            # Senate seats (6 year terms)
            {"seat_id": "SEN-CO-1", "office": "Senate", "state": "Columbia", "term_years": 6},
            {"seat_id": "SEN-CO-2", "office": "Senate", "state": "Columbia", "term_years": 6},
            {"seat_id": "SEN-CO-3", "office": "Senate", "state": "Columbia", "term_years": 6},
            {"seat_id": "SEN-CA-1", "office": "Senate", "state": "Cambridge", "term_years": 6},
            {"seat_id": "SEN-CA-2", "office": "Senate", "state": "Cambridge", "term_years": 6},
            {"seat_id": "SEN-CA-3", "office": "Senate", "state": "Cambridge", "term_years": 6},
            {"seat_id": "SEN-AU-1", "office": "Senate", "state": "Austin", "term_years": 6},
            {"seat_id": "SEN-AU-2", "office": "Senate", "state": "Austin", "term_years": 6},
            {"seat_id": "SEN-AU-3", "office": "Senate", "state": "Austin", "term_years": 6},
            {"seat_id": "SEN-SU-1", "office": "Senate", "state": "Superior", "term_years": 6},
            {"seat_id": "SEN-SU-2", "office": "Senate", "state": "Superior", "term_years": 6},
            {"seat_id": "SEN-SU-3", "office": "Senate", "state": "Superior", "term_years": 6},
            {"seat_id": "SEN-HL-1", "office": "Senate", "state": "Heartland", "term_years": 6},
            {"seat_id": "SEN-HL-2", "office": "Senate", "state": "Heartland", "term_years": 6},
            {"seat_id": "SEN-HL-3", "office": "Senate", "state": "Heartland", "term_years": 6},
            {"seat_id": "SEN-YS-1", "office": "Senate", "state": "Yellowstone", "term_years": 6},
            {"seat_id": "SEN-YS-2", "office": "Senate", "state": "Yellowstone", "term_years": 6},
            {"seat_id": "SEN-YS-3", "office": "Senate", "state": "Yellowstone", "term_years": 6},
            {"seat_id": "SEN-PH-1", "office": "Senate", "state": "Phoenix", "term_years": 6},
            {"seat_id": "SEN-PH-2", "office": "Senate", "state": "Phoenix", "term_years": 6},
            {"seat_id": "SEN-PH-3", "office": "Senate", "state": "Phoenix", "term_years": 6},

            # Governor seats (4 year terms)
            {"seat_id": "CO-GOV", "office": "Governor", "state": "Columbia", "term_years": 4},
            {"seat_id": "CA-GOV", "office": "Governor", "state": "Cambridge", "term_years": 4},
            {"seat_id": "AU-GOV", "office": "Governor", "state": "Austin", "term_years": 4},
            {"seat_id": "SU-GOV", "office": "Governor", "state": "Superior", "term_years": 4},
            {"seat_id": "HL-GOV", "office": "Governor", "state": "Heartland", "term_years": 4},
            {"seat_id": "YS-GOV", "office": "Governor", "state": "Yellowstone", "term_years": 4},
            {"seat_id": "PH-GOV", "office": "Governor", "state": "Phoenix", "term_years": 4},

            # Representative seats (2 year terms)
            {"seat_id": "REP-CA-1", "office": "District 1", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CA-2", "office": "District 2", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CA-3", "office": "District 3", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CA-4", "office": "District 4", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CA-5", "office": "District 5", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CA-6", "office": "District 6", "state": "Cambridge", "term_years": 2},
            {"seat_id": "REP-CO-1", "office": "District 1", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-2", "office": "District 2", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-3", "office": "District 3", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-4", "office": "District 4", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-5", "office": "District 5", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-6", "office": "District 6", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-CO-7", "office": "District 7", "state": "Columbia", "term_years": 2},
            {"seat_id": "REP-SU-1", "office": "District 1", "state": "Superior", "term_years": 2},
            {"seat_id": "REP-SU-2", "office": "District 2", "state": "Superior", "term_years": 2},
            {"seat_id": "REP-SU-3", "office": "District 3", "state": "Superior", "term_years": 2},
            {"seat_id": "REP-SU-4", "office": "District 4", "state": "Superior", "term_years": 2},
            {"seat_id": "REP-HL-1", "office": "District 1", "state": "Heartland", "term_years": 2},
            {"seat_id": "REP-HL-2", "office": "District 2", "state": "Heartland", "term_years": 2},
            {"seat_id": "REP-HL-3", "office": "District 3", "state": "Heartland", "term_years": 2},
            {"seat_id": "REP-HL-4", "office": "District 4", "state": "Heartland", "term_years": 2},
            {"seat_id": "REP-YS-1", "office": "District 1", "state": "Yellowstone", "term_years": 2},
            {"seat_id": "REP-YS-2", "office": "District 2", "state": "Yellowstone", "term_years": 2},
            {"seat_id": "REP-YS-3", "office": "District 3", "state": "Yellowstone", "term_years": 2},
            {"seat_id": "REP-PH-1", "office": "District 1", "state": "Phoenix", "term_years": 2},
            {"seat_id": "REP-PH-2", "office": "District 2", "state": "Phoenix", "term_years": 2},
            {"seat_id": "REP-PH-3", "office": "District 3", "state": "Phoenix", "term_years": 2},
            {"seat_id": "REP-PH-4", "office": "District 4", "state": "Phoenix", "term_years": 2},
            {"seat_id": "REP-AU-1", "office": "District 1", "state": "Austin", "term_years": 2},
            {"seat_id": "REP-AU-2", "office": "District 2", "state": "Austin", "term_years": 2},

            # National offices (4 year terms)
            {"seat_id": "US-PRES", "office": "President", "state": "National", "term_years": 4},
            {"seat_id": "US-VP", "office": "Vice President", "state": "National", "term_years": 4},
        ]

    def _should_seat_be_up_for_election(self, seat, current_year):
        """Determine if a seat should be up for election based on standard cycles"""
        office = seat["office"]
        seat_id = seat["seat_id"]

        # For signups in odd years, we're preparing for elections in the next even year
        # For even years, we're in the actual election year
        if current_year % 2 == 1:  # Odd years (signup years)
            election_year = current_year + 1  # Elections happen next year
        else:  # Even years (election years)
            election_year = current_year  # Elections happen this year

        if office == "Senate":
            # Senate elections every 6 years, staggered into 3 classes
            # Use seat number to create staggered pattern
            seat_num = int(seat_id.split("-")[-1]) if seat_id.split("-")[-1].isdigit() else 1
            
            # Simplified staggered cycle - ensure there are always seats up for election
            if seat_num % 3 == 1:  # Class 1 seats
                return election_year % 6 == 0  # 2000, 2006, 2012, etc.
            elif seat_num % 3 == 2:  # Class 2 seats
                return (election_year - 2) % 6 == 0  # 1998, 2004, 2010, etc.
            else:  # Class 3 seats  
                return (election_year - 4) % 6 == 0  # 1996, 2002, 2008, etc.
                
        elif office == "Governor":
            # Governor elections every 4 years
            return election_year % 4 == 0  # 2000, 2004, 2008, etc.
        elif "District" in office:
            # House elections every 2 years (every even year)
            return election_year % 2 == 0  # All even years
        elif seat["state"] == "National":
            # Presidential elections every 4 years
            return election_year % 4 == 0  # 2000, 2004, 2008, etc.

        return False

    def _get_elections_config(self, guild_id: int):
        """Get or create elections configuration for a guild"""
        col = self.bot.db["elections_config"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            # Initialize seats in database
            seats_in_db = []
            for seat in self.seats_data:
                seats_in_db.append({
                    **seat,
                    "current_holder": None,
                    "current_holder_id": None,
                    "term_start": None,
                    "term_end": None,
                    "up_for_election": True
                })

            config = {
                "guild_id": guild_id,
                "seats": seats_in_db,
                "candidates": [],  # List of candidate registrations
                "elections": []    # List of past/current elections
            }
            col.insert_one(config)
        return col, config

    @election_info_group.command(
        name="show_seats",
        description="Show all election seats by state or office type"
    )
    async def show_seats(
        self, 
        interaction: discord.Interaction, 
        filter_by: str = None,
        state: str = None
    ):
        try:
            col, config = self._get_elections_config(interaction.guild.id)

            seats = config["seats"]

            # Apply filters
            if state:
                seats = [s for s in seats if s["state"].lower() == state.lower()]

            if filter_by:
                if filter_by.lower() == "senate":
                    seats = [s for s in seats if s["office"] == "Senate"]
                elif filter_by.lower() == "governor":
                    seats = [s for s in seats if s["office"] == "Governor"]
                elif filter_by.lower() == "house":
                    seats = [s for s in seats if "District" in s["office"]]
                elif filter_by.lower() == "national":
                    seats = [s for s in seats if s["state"] == "National"]

            if not seats:
                await interaction.response.send_message("No seats found with those criteria.", ephemeral=True)
                return

            # Group seats by state for better organization
            states = {}
            for seat in seats:
                if seat["state"] not in states:
                    states[seat["state"]] = []
                states[seat["state"]].append(seat)

            embed = discord.Embed(
                title="🏛️ Election Seats",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            for state_name, state_seats in states.items():
                seat_text = ""
                for seat in state_seats:
                    holder_text = seat.get("current_holder", "Vacant")
                    term_text = f" ({seat['term_years']}yr term)"
                    seat_text += f"**{seat['seat_id']}** - {seat['office']}{term_text}\n"
                    seat_text += f"Current: {holder_text}\n\n"

                embed.add_field(
                    name=f"📍 {state_name}",
                    value=seat_text,
                    inline=True
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading seats: {str(e)}", ephemeral=True)


    @election_admin_group.command(
        name="fill_vacant_seat",
        description="Fill a vacant seat with a user (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_fill_vacant_seat(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        seat_id: str = None,
        term_start_year: int = None
    ):
        """Admin command to fill a vacant seat"""
        col, config = self._get_elections_config(interaction.guild.id)

        # If no seat_id provided, show available vacant seats
        if not seat_id:
            vacant_seats = [
                seat for seat in config["seats"] 
                if not seat.get("current_holder")
            ]

            if not vacant_seats:
                await interaction.response.send_message(
                    "❌ No vacant seats available to fill.",
                    ephemeral=True
                )
                return

            # Create embed showing vacant seats
            embed = discord.Embed(
                title="🏛️ Available Vacant Seats",
                description=f"Use this command again with a specific seat_id to assign **{user.display_name}** to a seat.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            # Group by state for better organization
            state_groups = {}
            for seat in vacant_seats:
                state = seat["state"]
                if state not in state_groups:
                    state_groups[state] = []
                state_groups[state].append(seat)

            for state_name, state_seats in state_groups.items():
                seat_list = ""
                for seat in state_seats:
                    up_indicator = " 🗳️" if seat.get("up_for_election") else ""
                    seat_list += f"• **{seat['seat_id']}** - {seat['office']}{up_indicator}\n"

                embed.add_field(
                    name=f"📍 {state_name}",
                    value=seat_list,
                    inline=True
                )

            embed.add_field(
                name="📝 Usage",
                value=f"Use: `/election admin fill_vacant_seat user:{user.mention} seat_id:<SEAT_ID>`",
                inline=False
            )

            embed.add_field(
                name="Legend",
                value="🗳️ = Currently up for election",
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Find the specific seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(
                f"❌ Seat '{seat_id}' not found.",
                ephemeral=True
            )
            return

        seat = config["seats"][seat_found]

        # Check if seat is actually vacant
        if seat.get("current_holder"):
            await interaction.response.send_message(
                f"❌ Seat **{seat_id}** is not vacant. Current holder: {seat['current_holder']}",
                ephemeral=True
            )
            return

        # Calculate term dates
        if term_start_year is None:
            # Get current RP year from time manager
            time_col = self.bot.db["time_configs"]
            time_config = time_col.find_one({"guild_id": interaction.guild.id})
            if time_config:
                term_start_year = time_config["current_rp_date"].year
            else:
                term_start_year = 2024  # Default fallback

        term_start = datetime(term_start_year, 1, 1)
        term_end = datetime(term_start_year + seat["term_years"], 1, 1)

        # Update seat
        config["seats"][seat_found].update({
            "current_holder": user.display_name,
            "current_holder_id": user.id,
            "term_start": term_start,
            "term_end": term_end,
            "up_for_election": False
        })

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        # Create success embed
        embed = discord.Embed(
            title="✅ Vacant Seat Filled",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 Appointed Official",
            value=user.mention,
            inline=True
        )

        embed.add_field(
            name="🏛️ Seat Details",
            value=f"**Seat ID:** {seat_id}\n**Office:** {seat['office']}\n**State/Region:** {seat['state']}",
            inline=True
        )

        embed.add_field(
            name="📅 Term Information",
            value=f"**Start:** {term_start_year}\n**End:** {term_start_year + seat['term_years']}\n**Length:** {seat['term_years']} years",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @election_seat_group.command(
        name="assign",
        description="Assign a user to an election seat"
    )
    async def assign_seat(
        self, 
        interaction: discord.Interaction, 
        seat_id: str,
        user: discord.Member,
        term_start_year: int = None
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(f"❌ Seat '{seat_id}' not found.", ephemeral=True)
            return

        seat = config["seats"][seat_found]

        # Calculate term dates
        if term_start_year is None:
            # Get current RP year from time manager
            time_col = self.bot.db["time_configs"]
            time_config = time_col.find_one({"guild_id": interaction.guild.id})
            if time_config:
                term_start_year = time_config["current_rp_date"].year
            else:
                term_start_year = 2024  # Default fallback

        term_start = datetime(term_start_year, 1, 1)
        term_end = datetime(term_start_year + seat["term_years"], 1, 1)

        # Update seat
        config["seats"][seat_found].update({
            "current_holder": user.display_name,
            "current_holder_id": user.id,
            "term_start": term_start,
            "term_end": term_end,
            "up_for_election": False
        })

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Assigned **{user.display_name}** to seat **{seat_id}** ({seat['office']}, {seat['state']})\n"
            f"Term: {term_start_year} - {term_start_year + seat['term_years']} ({seat['term_years']} years)",
            ephemeral=True
        )

    @election_info_group.command(
        name="seats_up_for_election",
        description="Show all seats that are up for election this cycle"
    )
    async def seats_up_for_election(self, interaction: discord.Interaction):
        col, config = self._get_elections_config(interaction.guild.id)

        # Get current RP year
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        up_for_election = []
        for seat in config["seats"]:
            # Check if seat should be up for election this cycle
            should_be_up = False

            if seat.get("up_for_election"):
                should_be_up = True
            elif seat.get("term_end"):
                # For seats with set term end dates, check if they expire next year (election year)
                # When in 1999 (odd year), we're preparing for 2000 elections
                election_year = current_year + 1 if current_year % 2 == 1 else current_year
                if seat["term_end"].year == election_year:
                    should_be_up = True
            elif not seat.get("current_holder"):
                # Vacant seat - check if it should be up this cycle
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)
            else:
                # Seat has a holder but no explicit term end - check standard cycle
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)

            if should_be_up:
                up_for_election.append(seat)

        if not up_for_election:
            await interaction.response.send_message("🗳️ No seats are currently up for election.", ephemeral=True)
            return

        # Group by office type
        office_groups = {}
        for seat in up_for_election:
            office_type = seat["office"] if seat["office"] in ["Senate", "Governor", "President", "Vice President"] else "House"
            if office_type not in office_groups:
                office_groups[office_type] = []
            office_groups[office_type].append(seat)

        # Create main overview embed
        embed = discord.Embed(
            title=f"🗳️ Seats Up for Election ({current_year})",
            description="Use the dropdown below to view detailed information for each office type.",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Add summary information
        summary_text = ""
        for office_type, seats in office_groups.items():
            summary_text += f"**{office_type}:** {len(seats)} seats\n"

        embed.add_field(
            name="📊 Summary",
            value=summary_text,
            inline=True
        )

        embed.add_field(
            name="ℹ️ Total",
            value=f"**{len(up_for_election)}** seats up for election",
            inline=True
        )

        view = SeatsUpView(office_groups, current_year)
        await interaction.response.send_message(embed=embed, view=view)

    @election_seat_group.command(
        name="toggle_election",
        description="Toggle whether a seat is up for election"
    )
    async def toggle_seat_election(
        self, 
        interaction: discord.Interaction, 
        seat_id: str
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(f"❌ Seat '{seat_id}' not found.", ephemeral=True)
            return

        seat = config["seats"][seat_found]
        current_status = seat.get("up_for_election", False)
        new_status = not current_status

        config["seats"][seat_found]["up_for_election"] = new_status

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        status_text = "up for election" if new_status else "not up for election"
        await interaction.response.send_message(
            f"✅ Seat **{seat_id}** ({seat['office']}, {seat['state']}) is now **{status_text}**.",
            ephemeral=True
        )

    @election_seat_group.command(
        name="vacant",
        description="Mark a seat as vacant (remove current holder)"
    )
    async def vacant_seat(
        self, 
        interaction: discord.Interaction, 
        seat_id: str
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(f"❌ Seat '{seat_id}' not found.", ephemeral=True)
            return

        seat = config["seats"][seat_found]

        # Clear the seat
        config["seats"][seat_found].update({
            "current_holder": None,
            "current_holder_id": None,
            "term_start": None,
            "term_end": None,
            "up_for_election": True
        })

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Seat **{seat_id}** ({seat['office']}, {seat['state']}) is now vacant and up for election.",
            ephemeral=True
        )

    @election_seat_group.command(
        name="bulk_assign_election",
        description="Mark all seats of a specific type or state as up for election"
    )
    async def bulk_assign_election(
        self, 
        interaction: discord.Interaction, 
        office_type: str = None,
        state: str = None
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        if not office_type and not state:
            await interaction.response.send_message("❌ Please specify either office_type or state.", ephemeral=True)
            return

        updated_seats = []

        for i, seat in enumerate(config["seats"]):
            should_update = False

            if office_type:
                if office_type.lower() == "senate" and seat["office"] == "Senate":
                    should_update = True
                elif office_type.lower() == "governor" and seat["office"] == "Governor":
                    should_update = True
                elif office_type.lower() == "house" and "District" in seat["office"]:
                    should_update = True
                elif office_type.lower() == "national" and seat["state"] == "National":
                    should_update = True

            if state and seat["state"].lower() == state.lower():
                should_update = True

            if should_update:
                config["seats"][i]["up_for_election"] = True
                updated_seats.append(seat["seat_id"])

        if not updated_seats:
            await interaction.response.send_message("❌ No seats found matching the criteria.", ephemeral=True)
            return

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        filter_text = f"office type '{office_type}'" if office_type else f"state '{state}'"
        await interaction.response.send_message(
            f"✅ Marked {len(updated_seats)} seats with {filter_text} as up for election.\n"
            f"Updated seats: {', '.join(updated_seats[:10])}{'...' if len(updated_seats) > 10 else ''}",
            ephemeral=True
        )

    @election_seat_group.command(
        name="modify_term",
        description="Modify the term length for a specific seat type"
    )
    async def modify_seat_term(
        self, 
        interaction: discord.Interaction, 
        office_type: str,
        new_term_years: int
    ):
        if new_term_years < 1 or new_term_years > 10:
            await interaction.response.send_message("❌ Term length must be between 1 and 10 years.", ephemeral=True)
            return

        col, config = self._get_elections_config(interaction.guild.id)

        updated_seats = []

        for i, seat in enumerate(config["seats"]):
            should_update = False

            if office_type.lower() == "senate" and seat["office"] == "Senate":
                should_update = True
            elif office_type.lower() == "governor" and seat["office"] == "Governor":
                should_update = True
            elif office_type.lower() == "house" and "District" in seat["office"]:
                should_update = True
            elif office_type.lower() == "national" and seat["state"] == "National":
                should_update = True

            if should_update:
                config["seats"][i]["term_years"] = new_term_years
                updated_seats.append(seat["seat_id"])

        if not updated_seats:
            await interaction.response.send_message(f"❌ No seats found for office type '{office_type}'.", ephemeral=True)
            return

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Updated term length for {len(updated_seats)} {office_type} seats to {new_term_years} years.\n"
            f"Updated seats: {', '.join(updated_seats[:10])}{'...' if len(updated_seats) > 10 else ''}",
            ephemeral=True
        )

    @election_info_group.command(
        name="stats",
        description="Show statistics about current elections and seats"
    )
    async def election_stats(self, interaction: discord.Interaction):
        col, config = self._get_elections_config(interaction.guild.id)

        # Get current RP year
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        seats = config["seats"]

        # Count totals
        total_seats = len(seats)
        filled_seats = len([s for s in seats if s.get("current_holder")])
        vacant_seats = total_seats - filled_seats
        up_for_election = len([s for s in seats if s.get("up_for_election") or 
                              (s.get("term_end") and s["term_end"].year == current_year)])

        # Count by office type
        senate_seats = len([s for s in seats if s["office"] == "Senate"])
        governor_seats = len([s for s in seats if s["office"] == "Governor"])
        house_seats = len([s for s in seats if "District" in s["office"]])
        national_seats = len([s for s in seats if s["state"] == "National"])

        # Count by state
        state_counts = {}
        for seat in seats:
            state = seat["state"]
            if state not in state_counts:
                state_counts[state] = {"total": 0, "filled": 0}
            state_counts[state]["total"] += 1
            if seat.get("current_holder"):
                state_counts[state]["filled"] += 1

        embed = discord.Embed(
            title="📊 Election Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Overall stats
        embed.add_field(
            name="📈 Overall Statistics",
            value=f"**Total Seats:** {total_seats}\n"
                  f"**Filled Seats:** {filled_seats}\n"
                  f"**Vacant Seats:** {vacant_seats}\n"
                  f"**Up for Election:** {up_for_election}",
            inline=True
        )

        # By office type
        embed.add_field(
            name="🏛️ By Office Type",
            value=f"**Senate:** {senate_seats}\n"
                  f"**Governor:** {governor_seats}\n"
                  f"**House:** {house_seats}\n"
                  f"**National:** {national_seats}",
            inline=True
        )

        # By state (top 5)
        state_text = ""
        sorted_states = sorted(state_counts.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
        for state, counts in sorted_states:
            state_text += f"**{state}:** {counts['filled']}/{counts['total']}\n"

        embed.add_field(
            name="🗺️ Top States (Filled/Total)",
            value=state_text,
            inline=True
        )

        embed.add_field(
            name="📅 Current Election Year",
            value=str(current_year),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @election_state_group.command(
        name="add",
        description="Add a new state/region with configurable seats"
    )
    async def add_state(
        self, 
        interaction: discord.Interaction, 
        state_name: str,
        state_code: str,
        senate_seats: int = 3,
        house_districts: int = 4,
        has_governor: bool = True
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Validate inputs
        state_code = state_code.upper()
        if len(state_code) != 2:
            await interaction.response.send_message("❌ State code must be exactly 2 characters (e.g., 'NY', 'CA')", ephemeral=True)
            return

        if senate_seats < 1 or senate_seats > 10:
            await interaction.response.send_message("❌ Senate seats must be between 1 and 10", ephemeral=True)
            return

        if house_districts < 1 or house_districts > 20:
            await interaction.response.send_message("❌ House districts must be between 1 and 20", ephemeral=True)
            return

        # Check if state already exists
        existing_state = any(seat["state"] == state_name for seat in config["seats"])
        if existing_state:
            await interaction.response.send_message(f"❌ State '{state_name}' already exists", ephemeral=True)
            return

        new_seats = []

        # Add Senate seats
        for i in range(1, senate_seats + 1):
            new_seats.append({
                "seat_id": f"SEN-{state_code}-{i}",
                "office": "Senate",
                "state": state_name,
                "term_years": 6,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        # Add Governor seat if requested
        if has_governor:
            new_seats.append({
                "seat_id": f"{state_code}-GOV",
                "office": "Governor",
                "state": state_name,
                "term_years": 4,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        # Add House districts
        for i in range(1, house_districts + 1):
            new_seats.append({
                "seat_id": f"REP-{state_code}-{i}",
                "office": f"District {i}",
                "state": state_name,
                "term_years": 2,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        # Add all new seats to config
        config["seats"].extend(new_seats)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        total_added = len(new_seats)
        seat_breakdown = f"{senate_seats} Senate"
        if has_governor:
            seat_breakdown += f", 1 Governor"
        seat_breakdown += f", {house_districts} House"

        await interaction.response.send_message(
            f"✅ Added state **{state_name}** ({state_code}) with {total_added} seats:\n"
            f"• {seat_breakdown}\n"
            f"• All seats are marked as up for election by default",
            ephemeral=True
        )

    @election_state_group.command(
        name="add_districts",
        description="Add additional house districts to an existing state"
    )
    async def add_districts(
        self, 
        interaction: discord.Interaction, 
        state_name: str,
        additional_districts: int
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        if additional_districts < 1 or additional_districts > 10:
            await interaction.response.send_message("❌ Additional districts must be between 1 and 10", ephemeral=True)
            return

        # Find existing districts for this state
        existing_districts = [
            seat for seat in config["seats"] 
            if seat["state"] == state_name and "District" in seat["office"]
        ]

        if not existing_districts:
            await interaction.response.send_message(f"❌ No existing districts found for state '{state_name}'", ephemeral=True)
            return

        # Find state code from existing seats
        state_code = None
        for seat in config["seats"]:
            if seat["state"] == state_name and seat["seat_id"].startswith("REP-"):
                state_code = seat["seat_id"].split("-")[1]
                break

        if not state_code:
            await interaction.response.send_message(f"❌ Could not determine state code for '{state_name}'", ephemeral=True)
            return

        # Get highest existing district number
        max_district = 0
        for seat in existing_districts:
            if "District" in seat["office"]:
                try:
                    district_num = int(seat["office"].split("District ")[1])
                    max_district = max(max_district, district_num)
                except (IndexError, ValueError):
                    continue

        # Add new districts
        new_seats = []
        for i in range(max_district + 1, max_district + additional_districts + 1):
            new_seats.append({
                "seat_id": f"REP-{state_code}-{i}",
                "office": f"District {i}",
                "state": state_name,
                "term_years": 2,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        config["seats"].extend(new_seats)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        seat_ids = [seat["seat_id"] for seat in new_seats]
        await interaction.response.send_message(
            f"✅ Added {additional_districts} additional districts to **{state_name}**:\n"
            f"• {', '.join(seat_ids)}\n"
            f"• All new districts are marked as up for election",
            ephemeral=True
        )

    @election_state_group.command(
        name="add_senate_seats",
        description="Add additional senate seats to an existing state"
    )
    async def add_senate_seats(
        self, 
        interaction: discord.Interaction, 
        state_name: str,
        additional_seats: int
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        if additional_seats < 1 or additional_seats > 5:
            await interaction.response.send_message("❌ Additional senate seats must be between 1 and 5", ephemeral=True)
            return

        # Find existing senate seats for this state
        existing_senate = [
            seat for seat in config["seats"] 
            if seat["state"] == state_name and seat["office"] == "Senate"
        ]

        if not existing_senate:
            await interaction.response.send_message(f"❌ No existing senate seats found for state '{state_name}'", ephemeral=True)
            return

        # Find state code from existing seats
        state_code = None
        for seat in existing_senate:
            if seat["seat_id"].startswith("SEN-"):
                state_code = seat["seat_id"].split("-")[1]
                break

        if not state_code:
            await interaction.response.send_message(f"❌ Could not determine state code for '{state_name}'", ephemeral=True)
            return

        # Get highest existing senate seat number
        max_seat = 0
        for seat in existing_senate:
            try:
                seat_num = int(seat["seat_id"].split("-")[2])
                max_seat = max(max_seat, seat_num)
            except (IndexError, ValueError):
                continue

        # Add new senate seats
        new_seats = []
        for i in range(max_seat + 1, max_seat + additional_seats + 1):
            new_seats.append({
                "seat_id": f"SEN-{state_code}-{i}",
                "office": "Senate",
                "state": state_name,
                "term_years": 6,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        config["seats"].extend(new_seats)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        seat_ids = [seat["seat_id"] for seat in new_seats]
        await interaction.response.send_message(
            f"✅ Added {additional_seats} additional senate seats to **{state_name}**:\n"
            f"• {', '.join(seat_ids)}\n"
            f"• All new seats are marked as up for election",
            ephemeral=True
        )

    @election_seat_group.command(
        name="remove",
        description="Remove a specific seat from the election system"
    )
    async def remove_seat(
        self, 
        interaction: discord.Interaction, 
        seat_id: str
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(f"❌ Seat '{seat_id}' not found", ephemeral=True)
            return

        removed_seat = config["seats"][seat_found]
        config["seats"].pop(seat_found)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Removed seat **{removed_seat['seat_id']}** ({removed_seat['office']}, {removed_seat['state']})",
            ephemeral=True
        )

    @election_state_group.command(
        name="remove",
        description="Remove an entire state/region and all its seats"
    )
    async def remove_state(
        self, 
        interaction: discord.Interaction, 
        state_name: str,
        confirm: bool = False
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find seats in this state
        state_seats = [seat for seat in config["seats"] if seat["state"] == state_name]

        if not state_seats:
            await interaction.response.send_message(f"❌ State '{state_name}' not found", ephemeral=True)
            return

        if not confirm:
            seat_count = len(state_seats)
            seat_types = {}
            for seat in state_seats:
                office = seat["office"] if seat["office"] in ["Senate", "Governor"] else "House"
                seat_types[office] = seat_types.get(office, 0) + 1

            type_breakdown = ", ".join([f"{count} {office}" for office, count in seat_types.items()])

            await interaction.response.send_message(
                f"⚠️ **Warning:** This will remove state **{state_name}** and all {seat_count} seats:\n"
                f"• {type_breakdown}\n\n"
                f"To confirm this action, run the command again with `confirm:True`",
                ephemeral=True
            )
            return

        # Remove all seats from this state
        config["seats"] = [seat for seat in config["seats"] if seat["state"] != state_name]

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        removed_seats = [seat["seat_id"] for seat in state_seats]
        await interaction.response.send_message(
            f"✅ Removed state **{state_name}** and {len(state_seats)} seats:\n"
            f"• {', '.join(removed_seats[:10])}{'...' if len(removed_seats) > 10 else ''}",
            ephemeral=True
        )

    @election_seat_group.command(
        name="set_term_year",
        description="Set a specific term end year for a seat"
    )
    async def set_seat_term_year(
        self, 
        interaction: discord.Interaction, 
        seat_id: str,
        term_end_year: int
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Find the seat
        seat_found = None
        for i, seat in enumerate(config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_found = i
                break

        if seat_found is None:
            await interaction.response.send_message(f"❌ Seat '{seat_id}' not found.", ephemeral=True)
            return

        seat = config["seats"][seat_found]

        # Set the term end date
        term_end = datetime(term_end_year, 12, 31)  # End of the specified year

        config["seats"][seat_found].update({
            "term_end": term_end,
            "up_for_election": term_end_year == datetime.now().year  # Up for election if term ends this year
        })

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Set term end year for **{seat_id}** ({seat['office']}, {seat['state']}) to **{term_end_year}**",
            ephemeral=True
        )

    @election_admin_group.command(
        name="bulk_set_term_years",
        description="Bulk set term end years for multiple seats (format: SEAT-ID:YEAR,SEAT-ID:YEAR)"
    )
    async def bulk_set_term_years(
        self, 
        interaction: discord.Interaction, 
        seat_year_pairs: str
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        # Parse the input format: "SEN-CO-1:1986,SEN-CO-2:1988,..."
        pairs = seat_year_pairs.split(",")
        updated_seats = []
        errors = []

        for pair in pairs:
            try:
                seat_id, year_str = pair.strip().split(":")
                year = int(year_str)

                # Find the seat
                seat_found = None
                for i, seat in enumerate(config["seats"]):
                    if seat["seat_id"].upper() == seat_id.upper():
                        seat_found = i
                        break

                if seat_found is not None:
                    term_end = datetime(year, 12, 31)
                    config["seats"][seat_found].update({
                        "term_end": term_end,
                        "up_for_election": year == datetime.now().year
                    })
                    updated_seats.append(f"{seat_id}:{year}")
                else:
                    errors.append(f"Seat {seat_id} not found")

            except (ValueError, IndexError):
                errors.append(f"Invalid format: {pair}")

        if updated_seats:
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": config["seats"]}}
            )

        response = f"✅ Updated {len(updated_seats)} seats with term end years"
        if updated_seats:  # Show first 5
            response += f":\n• {chr(10).join(updated_seats[:5])}"
            if len(updated_seats) > 5:
                response += f"\n• ... and {len(updated_seats) - 5} more"

        if errors:
            response += f"\n\n❌ Errors:\n• {chr(10).join(errors[:5])}"

        await interaction.response.send_message(response, ephemeral=True)

    @election_admin_group.command(
        name="advance_all_terms",
        description="Manually advance all seat terms that were up for election"
    )
    async def advance_all_terms(self, interaction: discord.Interaction):
        """Manually advance terms for seats that were up for election"""
        # Get current RP year
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        updated_seats = await self._auto_advance_terms_after_election(interaction.guild.id, current_year)

        if updated_seats:
            response = f"✅ Advanced {len(updated_seats)} seat terms:\n"
            response += "\n".join([f"• {seat}" for seat in updated_seats[:10]])
            if len(updated_seats) > 10:
                response += f"\n• ... and {len(updated_seats) - 10} more"
        else:
            response = "ℹ️ No seats were up for election to advance"

        await interaction.response.send_message(response, ephemeral=True)

    @election_admin_group.command(
        name="announce_seats_up",
        description="Announce which seats are up for election this cycle (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def announce_seats_up(self, interaction: discord.Interaction):
        """Announce seats up for election in the configured announcement channel"""
        col, config = self._get_elections_config(interaction.guild.id)

        # Get current RP year
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Get announcement channel
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": interaction.guild.id})
        announcement_channel_id = setup_config.get("announcement_channel") if setup_config else None

        if not announcement_channel_id:
            await interaction.response.send_message(
                "❌ No announcement channel configured. Use `/setup announcement_channel` first.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(announcement_channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ Announcement channel not found. Please reconfigure it.",
                ephemeral=True
            )
            return

        # Get seats up for election
        up_for_election = []
        for seat in config["seats"]:
            should_be_up = False

            if seat.get("up_for_election"):
                should_be_up = True
            elif seat.get("term_end"):
                election_year = current_year + 1 if current_year % 2 == 1 else current_year
                if seat["term_end"].year == election_year:
                    should_be_up = True
            elif not seat.get("current_holder"):
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)
            else:
                should_be_up = self._should_seat_be_up_for_election(seat, current_year)

            if should_be_up:
                up_for_election.append(seat)

        if not up_for_election:
            await interaction.response.send_message("🗳️ No seats are currently up for election to announce.", ephemeral=True)
            return

        # Group by office type
        office_groups = {}
        for seat in up_for_election:
            office_type = seat["office"] if seat["office"] in ["Senate", "Governor", "President", "Vice President"] else "House"
            if office_type not in office_groups:
                office_groups[office_type] = []
            office_groups[office_type].append(seat)

        # Create main overview embed with dropdown navigation
        embed = discord.Embed(
            title="🗳️ ELECTION ANNOUNCEMENT",
            description=f"**{len(up_for_election)} seats** are now up for election in the **{current_year}** election cycle!\n\nUse the dropdown below to view detailed information for each office type.",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        # Add summary information
        summary_text = ""
        for office_type, seats in office_groups.items():
            summary_text += f"**{office_type}:** {len(seats)} seats\n"

        embed.add_field(
            name="📊 Summary",
            value=summary_text,
            inline=True
        )

        embed.add_field(
            name="ℹ️ Total",
            value=f"**{len(up_for_election)}** seats up for election",
            inline=True
        )

        embed.add_field(
            name="📝 Next Steps",
            value="Candidates can now register for these positions during the signup phase!\nUse `/signup` to enter the race.",
            inline=False
        )

        embed.set_footer(text="Good luck to all potential candidates!")

        # Create the dropdown view for detailed seat information
        view = SeatsUpView(office_groups, current_year)

        try:
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Announced {len(up_for_election)} seats up for election in {channel.mention}",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to send messages in the announcement channel.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to send announcement: {str(e)}",
                ephemeral=True
            )

    @election_info_group.command(
        name="show_seat_terms",
        description="Show term end years for all seats or filter by state/office"
    )
    async def show_seat_terms(
        self, 
        interaction: discord.Interaction, 
        state: str = None,
        office_type: str = None
    ):
        col, config = self._get_elections_config(interaction.guild.id)

        seats = config["seats"]

        # Apply filters
        if state:
            seats = [s for s in seats if s["state"].lower() == state.lower()]

        if office_type:
            if office_type.lower() == "senate":
                seats = [s for s in seats if s["office"] == "Senate"]
            elif office_type.lower() == "governor":
                seats = [s for s in seats if s["office"] == "Governor"]
            elif office_type.lower() == "house":
                seats = [s for s in seats if "District" in s["office"]]
            elif office_type.lower() == "national":
                seats = [s for s in seats if s["state"] == "National"]

        if not seats:
            await interaction.response.send_message("No seats found with those criteria.", ephemeral=True)
            return

        # Group seats by state for pagination
        state_groups = {}
        for seat in seats:
            if seat["state"] not in state_groups:
                state_groups[seat["state"]] = []
            state_groups[seat["state"]].append(seat)

        # Create main overview embed
        embed = discord.Embed(
            title="📅 Seat Term End Years",
            description="Use the dropdown below to view detailed term information for each state.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Add summary information
        summary_text = ""
        total_seats = 0
        seats_with_terms = 0

        for state_name, state_seats in state_groups.items():
            total_seats += len(state_seats)
            seats_with_terms += len([s for s in state_seats if s.get("term_end")])
            summary_text += f"**{state_name}:** {len(state_seats)} seats\n"

        embed.add_field(
            name="📊 Summary by State",
            value=summary_text[:1024],
            inline=True
        )

        embed.add_field(
            name="ℹ️ Statistics",
            value=f"**Total Seats:** {total_seats}\n**With Set Terms:** {seats_with_terms}\n**Without Terms:** {total_seats - seats_with_terms}",
            inline=True
        )

        embed.add_field(
            name="Legend",
            value="🗳️ = Up for election this cycle",
            inline=False
        )

        view = SeatTermsView(state_groups)
        await interaction.response.send_message(embed=embed, view=view)

    @election_info_group.command(
        name="list_states",
        description="List all states/regions and their seat counts"
    )
    async def list_states(self, interaction: discord.Interaction):
        col, config = self._get_elections_config(interaction.guild.id)

        # Group seats by state
        state_info = {}
        for seat in config["seats"]:
            state = seat["state"]
            if state not in state_info:
                state_info[state] = {"senate": 0, "governor": 0, "house": 0, "national": 0}

            if seat["office"] == "Senate":
                state_info[state]["senate"] += 1
            elif seat["office"] == "Governor":
                state_info[state]["governor"] += 1
            elif "District" in seat["office"]:
                state_info[state]["house"] += 1
            elif seat["state"] == "National":
                state_info[state]["national"] += 1

        if not state_info:
            await interaction.response.send_message("❌ No states configured yet", ephemeral=True)
            return

        embed = discord.Embed(
            title="🗺️ Configured States/Regions",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        for state, counts in sorted(state_info.items()):
            breakdown = []
            if counts["senate"] > 0:
                breakdown.append(f"{counts['senate']} Senate")
            if counts["governor"] > 0:
                breakdown.append(f"{counts['governor']} Governor")
            if counts["house"] > 0:
                breakdown.append(f"{counts['house']} House")
            if counts["national"] > 0:
                breakdown.append(f"{counts['national']} National")

            total = sum(counts.values())
            seat_text = f"**Total: {total} seats**\n" + " • ".join(breakdown)

            embed.add_field(
                name=f"📍 {state}",
                value=seat_text,
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    @election_admin_group.command(
        name="import_seat_term_years",
        description="Import term end years for specific seats (format: SEAT-ID:YEAR,SEAT-ID:YEAR)"
    )
    async def import_seat_term_years(
        self,
        interaction: discord.Interaction,
        seat_year_data: str,
        confirm: bool = False
    ):
        """Import term end years for specific seats"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will set specific term end years for multiple seats.\n"
                f"Example format: `SEN-CO-1:1986,SEN-CO-2:1988,CO-GOV:1988`\n"
                f"To confirm, run the command again with `confirm:True`",
                ephemeral=True
            )
            return

        col, config = self._get_elections_config(interaction.guild.id)

        # Get current RP year for comparison
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})
        current_year = time_config["current_rp_date"].year if time_config else 2024

        # Parse the input
        pairs = seat_year_data.split(",")
        updated_seats = []
        errors = []

        for pair in pairs:
            try:
                seat_id, year_str = pair.strip().split(":")
                year = int(year_str)

                # Find the seat
                seat_found = None
                for i, seat in enumerate(config["seats"]):
                    if seat["seat_id"].upper() == seat_id.upper():
                        seat_found = i
                        break

                if seat_found is not None:
                    term_end = datetime(year, 12, 31)
                    config["seats"][seat_found].update({
                        "term_end": term_end,
                        "up_for_election": year == current_year  # Up for election if term ends this year
                    })
                    updated_seats.append(f"{seat_id}:{year}")
                else:
                    errors.append(f"Seat {seat_id} not found")

            except (ValueError, IndexError):
                errors.append(f"Invalid format: {pair}")

        if updated_seats:
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": config["seats"]}}
            )

        response = f"✅ Updated {len(updated_seats)} seats with term end years"
        if updated_seats:
            response += f":\n• {chr(10).join(updated_seats[:15])}"
            if len(updated_seats) > 15:
                response += f"\n• ... and {len(updated_seats) - 15} more"

        if errors:
            response += f"\n\n❌ Errors:\n• {chr(10).join(errors[:5])}"

        await interaction.response.send_message(response, ephemeral=True)

    @election_admin_group.command(
        name="shift_all_term_years_negative",
        description="Shift all seat term end years by a specified number of years (subtract)"
    )
    async def shift_all_term_years_negative(
        self,
        interaction: discord.Interaction,
        years_to_subtract: int,
        confirm: bool = False
    ):
        """Shift all term end years by the specified amount (can be negative)"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will shift ALL seat term end years by -{years_to_subtract} years.\n"
                f"To confirm, run the command again with `confirm:True`",
                ephemeral=True
            )
            return

        col, config = self._get_elections_config(interaction.guild.id)
        updated_seats = []

        for i, seat in enumerate(config["seats"]):
            if seat.get("term_end"):
                old_year = seat["term_end"].year
                new_year = old_year - years_to_subtract
                config["seats"][i]["term_end"] = datetime(new_year, 12, 31)
                updated_seats.append(f"{seat['seat_id']}: {old_year} → {new_year}")

        if updated_seats:
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": config["seats"]}}
            )

        await interaction.response.send_message(
            f"✅ Shifted {len(updated_seats)} seat terms by -{years_to_subtract} years:\n" +
            "\n".join([f"• {seat}" for seat in updated_seats[:10]]) +
            (f"\n• ... and {len(updated_seats) - 10} more" if len(updated_seats) > 10 else ""),
            ephemeral=True
        )

    @election_group.command(
        name="admin_clear_all_elections",
        description="Clear all election data (Admin only - DESTRUCTIVE)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_all_elections(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """Clear all election data - seats, candidates, elections"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **DANGER:** This will permanently delete ALL election data including:\n"
                f"• All seats and their holders\n"
                f"• All candidate signups\n"
                f"• All election history\n\n"
                f"To confirm this destructive action, run with `confirm:True`",
                ephemeral=True
            )
            return

        col, config = self._get_elections_config(interaction.guild.id)
        
        # Reset to initial state
        seats_in_db = []
        for seat in self.seats_data:
            seats_in_db.append({
                **seat,
                "current_holder": None,
                "current_holder_id": None,
                "term_start": None,
                "term_end": None,
                "up_for_election": True
            })

        new_config = {
            "guild_id": interaction.guild.id,
            "seats": seats_in_db,
            "candidates": [],
            "elections": []
        }

        col.replace_one(
            {"guild_id": interaction.guild.id},
            new_config
        )

        await interaction.response.send_message(
            f"✅ All election data has been cleared and reset to defaults.\n"
            f"• {len(seats_in_db)} seats reset to vacant\n"
            f"• All candidate signups removed\n"
            f"• All election history cleared",
            ephemeral=True
        )

    @election_group.command(
        name="admin_bulk_clear_holders",
        description="Clear all current seat holders (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_clear_holders(
        self,
        interaction: discord.Interaction,
        office_type: str = None,
        confirm: bool = False
    ):
        """Clear seat holders for all seats or specific office type"""
        if not confirm:
            filter_text = f" for {office_type}" if office_type else ""
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will clear all current seat holders{filter_text}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        col, config = self._get_elections_config(interaction.guild.id)
        cleared_seats = []

        for i, seat in enumerate(config["seats"]):
            should_clear = False

            if not office_type:
                should_clear = True
            elif office_type.lower() == "senate" and seat["office"] == "Senate":
                should_clear = True
            elif office_type.lower() == "governor" and seat["office"] == "Governor":
                should_clear = True
            elif office_type.lower() == "house" and "District" in seat["office"]:
                should_clear = True
            elif office_type.lower() == "national" and seat["state"] == "National":
                should_clear = True

            if should_clear and seat.get("current_holder"):
                config["seats"][i].update({
                    "current_holder": None,
                    "current_holder_id": None,
                    "term_start": None,
                    "term_end": None,
                    "up_for_election": True
                })
                cleared_seats.append(seat["seat_id"])

        if cleared_seats:
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"seats": config["seats"]}}
            )

        filter_text = f" ({office_type})" if office_type else ""
        await interaction.response.send_message(
            f"✅ Cleared {len(cleared_seats)} seat holders{filter_text}:\n" +
            "\n".join([f"• {seat}" for seat in cleared_seats[:15]]) +
            (f"\n• ... and {len(cleared_seats) - 15} more" if len(cleared_seats) > 15 else ""),
            ephemeral=True
        )

    @election_group.command(
        name="admin_modify_election_config",
        description="Modify election configuration settings (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_modify_election_config(
        self,
        interaction: discord.Interaction,
        setting: str,
        value: str
    ):
        """Modify various election settings"""
        col, config = self._get_elections_config(interaction.guild.id)

        valid_settings = ["default_senate_term", "default_governor_term", "default_house_term", "default_national_term"]
        
        if setting not in valid_settings:
            await interaction.response.send_message(
                f"❌ Invalid setting. Valid options: {', '.join(valid_settings)}",
                ephemeral=True
            )
            return

        try:
            if "term" in setting:
                term_years = int(value)
                if term_years < 1 or term_years > 10:
                    raise ValueError("Term years must be between 1 and 10")

                # Update default term lengths for new seats
                if setting == "default_senate_term":
                    office_type = "Senate"
                elif setting == "default_governor_term":
                    office_type = "Governor"
                elif setting == "default_house_term":
                    office_type = "District"
                elif setting == "default_national_term":
                    office_type = "National"

                # Store in config for future reference
                if "defaults" not in config:
                    config["defaults"] = {}
                config["defaults"][setting] = term_years

                col.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": {"defaults": config["defaults"]}}
                )

                await interaction.response.send_message(
                    f"✅ Set {setting} to {term_years} years. This will apply to newly created seats.",
                    ephemeral=True
                )

        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid value: {str(e)}", ephemeral=True)

    @election_group.command(
        name="admin_export_seats",
        description="Export seat configuration as text (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_export_seats(
        self,
        interaction: discord.Interaction,
        format_type: str = "csv"
    ):
        """Export seat data in various formats"""
        col, config = self._get_elections_config(interaction.guild.id)

        if format_type.lower() == "csv":
            lines = ["seat_id,office,state,term_years,current_holder,term_end,up_for_election"]
            for seat in config["seats"]:
                holder = seat.get("current_holder", "")
                term_end = seat.get("term_end", "").strftime("%Y-%m-%d") if seat.get("term_end") else ""
                up_for_election = "yes" if seat.get("up_for_election") else "no"
                lines.append(f"{seat['seat_id']},{seat['office']},{seat['state']},{seat['term_years']},{holder},{term_end},{up_for_election}")
            
            export_text = "\n".join(lines)
        else:
            # JSON-like format
            export_lines = []
            for seat in config["seats"]:
                holder = seat.get("current_holder", "None")
                term_end = seat.get("term_end", "None")
                if term_end != "None":
                    term_end = f"'{term_end.strftime('%Y-%m-%d')}'"
                up_for_election = seat.get("up_for_election", False)
                
                export_lines.append(
                    f"'{seat['seat_id']}': {seat['office']}, {seat['state']}, "
                    f"{seat['term_years']}yr, Holder: {holder}, Term End: {term_end}, "
                    f"Up: {up_for_election}"
                )
            
            export_text = "\n".join(export_lines)

        # Split into chunks if too long
        if len(export_text) > 1900:
            chunk_size = 1900
            chunks = [export_text[i:i+chunk_size] for i in range(0, len(export_text), chunk_size)]
            
            await interaction.response.send_message(
                f"📊 Seat Export ({format_type.upper()}) - Part 1/{len(chunks)}:\n```\n{chunks[0]}\n```",
                ephemeral=True
            )
            
            for i, chunk in enumerate(chunks[1:], 2):
                await interaction.followup.send(
                    f"📊 Part {i}/{len(chunks)}:\n```\n{chunk}\n```",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"📊 Seat Export ({format_type.upper()}):\n```\n{export_text}\n```",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Elections(bot))