
from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class Elections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.seats_data = self._initialize_seats()
        print("Elections cog loaded successfully")

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
                # Seat has an assigned term that expires this year or next year (election year)
                if seat["term_end"].year <= current_year + 1:
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

        if office == "Senate":
            # Senate elections every 6 years, staggered
            # Use seat number to create staggered pattern
            seat_num = int(seat_id.split("-")[-1]) if seat_id.split("-")[-1].isdigit() else 1
            # Create staggered 6-year cycles based on seat number
            if seat_num % 3 == 1:  # Class 1 seats (years ending in 6, 2, 8)
                return current_year % 6 == 0
            elif seat_num % 3 == 2:  # Class 2 seats (years ending in 8, 4, 0) 
                return (current_year - 2) % 6 == 0
            else:  # Class 3 seats (years ending in 0, 6, 2)
                return (current_year - 4) % 6 == 0
        elif office == "Governor":
            # Governor elections every 4 years
            return current_year % 4 == 0
        elif "District" in office:
            # House elections every 2 years
            return current_year % 2 == 0
        elif seat["state"] == "National":
            # Presidential elections every 4 years
            return current_year % 4 == 0

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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="show_seats",
        description="Show all election seats by state or office type"
    )
    async def show_seats(
        self, 
        interaction: discord.Interaction, 
        filter_by: str = None,
        state: str = None
    ):
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="assign_seat",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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
            # Check if term expires this year/next year or seat is explicitly up for election
            should_be_up = False

            if seat.get("up_for_election"):
                should_be_up = True
            elif seat.get("term_end") and seat["term_end"].year <= current_year + 1:
                should_be_up = True
            elif not seat.get("current_holder"):
                # Vacant seat - check if it should be up this cycle
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

        embed = discord.Embed(
            title=f"🗳️ Seats Up for Election ({current_year})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for office_type, seats in office_groups.items():
            seat_list = ""
            for seat in seats:
                incumbent = seat.get("current_holder", "Open Seat")
                seat_list += f"• **{seat['seat_id']}** ({seat['state']})\n  Current: {incumbent}\n"

            embed.add_field(
                name=f"🏛️ {office_type}",
                value=seat_list,
                inline=False
            )

        embed.add_field(
            name="ℹ️ Information",
            value=f"Total seats up for election: **{len(up_for_election)}**",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="toggle_seat_election",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="vacant_seat",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="modify_seat_term",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="election_stats",
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
                              (s.get("term_end") and s["term_end"].year <= current_year)])

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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="add_state",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="remove_seat",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="remove_state",
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="set_seat_term_year",
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
            "up_for_election": term_end_year <= datetime.now().year + 1  # Up for election if term ends this year or next
        })

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        await interaction.response.send_message(
            f"✅ Set term end year for **{seat_id}** ({seat['office']}, {seat['state']}) to **{term_end_year}**",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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
                        "up_for_election": year <= datetime.now().year + 1
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
        if updated_seats[:5]:  # Show first 5
            response += f":\n• {chr(10).join(updated_seats[:5])}"
            if len(updated_seats) > 5:
                response += f"\n• ... and {len(updated_seats) - 5} more"

        if errors:
            response += f"\n\n❌ Errors:\n• {chr(10).join(errors[:5])}"

        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

        # Sort by term end year
        seats_with_terms = []
        seats_without_terms = []

        for seat in seats:
            if seat.get("term_end"):
                seats_with_terms.append((seat, seat["term_end"].year))
            else:
                seats_without_terms.append(seat)

        seats_with_terms.sort(key=lambda x: x[1])  # Sort by year

        embed = discord.Embed(
            title="📅 Seat Term End Years",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Show seats with specific term end years
        if seats_with_terms:
            term_text = ""
            for seat, year in seats_with_terms:
                holder = seat.get("current_holder", "Vacant")
                up_indicator = " 🗳️" if seat.get("up_for_election") else ""
                term_text += f"**{seat['seat_id']}** - {year}{up_indicator}\n"
                term_text += f"  {seat['office']}, {seat['state']} ({holder})\n\n"

            embed.add_field(
                name="🗓️ Seats with Set Term End Years",
                value=term_text[:1024],  # Discord field limit
                inline=False
            )

        # Show seats without specific terms
        if seats_without_terms:
            no_term_text = ""
            for seat in seats_without_terms:
                holder = seat.get("current_holder", "Vacant")
                up_indicator = " 🗳️" if seat.get("up_for_election") else ""
                no_term_text += f"**{seat['seat_id']}**{up_indicator} - {seat['office']}, {seat['state']} ({holder})\n"

            embed.add_field(
                name="❓ Seats without Set Term Years",
                value=no_term_text[:1024],
                inline=False
            )

        embed.add_field(
            name="Legend",
            value="🗳️ = Up for election this cycle",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
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

async def setup(bot):
    await bot.add_cog(Elections(bot))
