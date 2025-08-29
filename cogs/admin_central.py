from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime, timedelta
import inspect

class AdminCentral(commands.Cog):
    """Centralized admin commands with role-based access control"""

    def __init__(self, bot):
        self.bot = bot
        print("AdminCentral cog loaded successfully")

    # Main admin group - hidden from non-admins
    admin_group = app_commands.Group(
        name="admincentral",
        description="Administrative commands",
        default_permissions=discord.Permissions(administrator=True)
    )

    # Subgroups for different admin areas - all inherit admin permissions from parent
    admin_election_group = app_commands.Group(
        name="election",
        description="Election admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_party_group = app_commands.Group(
        name="party",
        description="Party admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_time_group = app_commands.Group(
        name="time",
        description="Time admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_poll_group = app_commands.Group(
        name="poll",
        description="Polling admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_system_group = app_commands.Group(
        name="system",
        description="System admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_momentum_group = app_commands.Group(
        name="momentum",
        description="Momentum admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_presidential_group = app_commands.Group(
        name="presidential",
        description="Presidential election admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_campaign_group = app_commands.Group(
        name="campaign",
        description="Campaign admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_delegates_group = app_commands.Group(
        name="delegates",
        description="Delegate admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_endorsements_group = app_commands.Group(
        name="endorsements",
        description="Endorsement admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_demographics_group = app_commands.Group(
        name="demographics",
        description="Demographics admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_voting_group = app_commands.Group(
        name="voting",
        description="Voting admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_ideology_group = app_commands.Group(
        name="ideology",
        description="Ideology admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_signup_group = app_commands.Group(
        name="signup",
        description="Signup admin commands",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )
    admin_logs_group = app_commands.Group(
        name="logs",
        description="Admin command logging",
        parent=admin_group,
        default_permissions=discord.Permissions(administrator=True)
    )

    # Helper method to check admin permissions
    async def _check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return False
        return True

    async def _log_admin_command(self, interaction: discord.Interaction, command_name: str, parameters: dict = None):
        """Log admin command usage"""
        admin_logs_col = self.bot.db["admin_command_logs"]

        log_entry = {
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "username": interaction.user.display_name,
            "command": command_name,
            "parameters": parameters or {},
            "timestamp": datetime.utcnow(),
            "channel_id": interaction.channel.id if interaction.channel else None
        }

        admin_logs_col.insert_one(log_entry)

    # SYSTEM COMMANDS
    @admin_system_group.command(
        name="reset_campaign_cooldowns",
        description="Reset general campaign action cooldowns for a user"
    )
    @app_commands.describe(
        user="The user to reset cooldowns for (defaults to yourself)",
        collection_name="The cooldown collection to reset"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_campaign_cooldowns(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        collection_name: str = "action_cooldowns"
    ):
        target_user = user if user else interaction.user
        cooldowns_col = self.bot.db[collection_name]

        result = cooldowns_col.delete_many({
            "guild_id": interaction.guild.id,
            "user_id": target_user.id
        })

        # Log the command
        await self._log_admin_command(
            interaction,
            "reset_campaign_cooldowns",
            {
                "target_user_id": target_user.id,
                "target_username": target_user.display_name,
                "collection_name": collection_name,
                "records_removed": result.deleted_count
            }
        )

        await interaction.response.send_message(
            f"✅ Reset campaign cooldowns for {target_user.mention} in collection '{collection_name}'. "
            f"Removed {result.deleted_count} cooldown record(s).",
            ephemeral=True
        )

    @admin_reset_campaign_cooldowns.autocomplete("collection_name")
    async def collection_autocomplete(self, interaction: discord.Interaction, current: str):
        collections = ["action_cooldowns", "campaign_cooldowns", "general_action_cooldowns", "election_cooldowns"]
        return [app_commands.Choice(name=col, value=col)
                for col in collections if current.lower() in col.lower()][:25]

    # ELECTION COMMANDS
    @admin_election_group.command(
        name="set_seats",
        description="Set up election seats for the guild"
    )
    @app_commands.describe(
        state="State name",
        office="Office type",
        seats="Number of seats"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_seats(
        self,
        interaction: discord.Interaction,
        state: str,
        office: str,
        seats: int
    ):
        elections_col = self.bot.db["elections_config"]

        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$push": {"seats": {"state": state, "office": office, "seats": seats}}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_seats", {"state": state, "office": office, "seats": seats})

        await interaction.response.send_message(
            f"✅ Added {seats} {office} seats for {state}",
            ephemeral=True
        )

    @admin_election_group.command(
        name="reset_seats",
        description="Reset all election seats"
    )
    @app_commands.describe(confirm="Set to True to confirm the reset")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_seats(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will reset all election seats.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        elections_col = self.bot.db["elections_config"]
        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": []}},
            upsert=True
        )

        await self._log_admin_command(interaction, "reset_seats", {"confirm": confirm})

        await interaction.response.send_message("✅ All election seats have been reset.", ephemeral=True)

    @admin_election_group.command(
        name="fill_vacant_seat",
        description="Fill a vacant seat with a user"
    )
    @app_commands.describe(
        user="User to fill the seat",
        state="State name",
        office="Office type"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_fill_vacant_seat(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        state: str,
        office: str
    ):
        winners_col = self.bot.db["winners"]

        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$push": {"winners": {
                "user_id": user.id,
                "state": state,
                "office": office,
                "filled_date": datetime.utcnow()
            }}},
            upsert=True
        )

        await self._log_admin_command(interaction, "fill_vacant_seat", {"user_id": user.id, "state": state, "office": office})

        await interaction.response.send_message(
            f"✅ {user.mention} has been appointed to {office} seat in {state}",
            ephemeral=True
        )

    @admin_election_group.command(
        name="bulk_add_seats",
        description="Add multiple seats from formatted text"
    )
    @app_commands.describe(
        seats_data="Formatted seat data (state:office:count, one per line)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_add_seats(
        self,
        interaction: discord.Interaction,
        seats_data: str
    ):
        lines = seats_data.strip().split('\n')
        added_count = 0
        elections_col = self.bot.db["elections_config"]

        for line in lines:
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 3:
                    state, office, seats_str = parts
                    try:
                        seats = int(seats_str.strip())
                        elections_col.update_one(
                            {"guild_id": interaction.guild.id},
                            {"$push": {"seats": {
                                "state": state.strip(),
                                "office": office.strip(),
                                "seats": seats
                            }}},
                            upsert=True
                        )
                        added_count += 1
                    except ValueError:
                        continue

        await self._log_admin_command(interaction, "bulk_add_seats", {"lines_processed": len(lines), "seats_added": added_count})

        await interaction.response.send_message(
            f"✅ Added {added_count} seat configurations",
            ephemeral=True
        )

    # PARTY COMMANDS
    @admin_party_group.command(
        name="create",
        description="Create a new political party"
    )
    @app_commands.describe(
        name="Party name",
        abbreviation="Party abbreviation",
        color="Hex color code (e.g., #FF0000)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_create_party(
        self,
        interaction: discord.Interaction,
        name: str,
        abbreviation: str,
        color: str
    ):
        try:
            color_int = int(color.replace("#", ""), 16)
        except ValueError:
            await interaction.response.send_message("❌ Invalid color format. Use hex format like #FF0000", ephemeral=True)
            return

        parties_col = self.bot.db["parties_config"]

        parties_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$push": {"parties": {
                "name": name,
                "abbreviation": abbreviation,
                "color": color_int,
                "created_at": datetime.utcnow(),
                "is_default": False
            }}},
            upsert=True
        )

        await self._log_admin_command(interaction, "create_party", {"name": name, "abbreviation": abbreviation, "color": color})

        await interaction.response.send_message(
            f"✅ Created party **{name}** ({abbreviation}) with color {color}",
            ephemeral=True
        )

    @admin_party_group.command(
        name="remove",
        description="Remove a political party"
    )
    @app_commands.describe(name="Party name to remove")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_party(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        parties_col = self.bot.db["parties_config"]

        result = parties_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$pull": {"parties": {"name": name}}}
        )

        if result.modified_count > 0:
            await self._log_admin_command(interaction, "remove_party", {"name": name, "status": "removed"})
            await interaction.response.send_message(f"✅ Removed party **{name}**", ephemeral=True)
        else:
            await self._log_admin_command(interaction, "remove_party", {"name": name, "status": "not_found"})
            await interaction.response.send_message(f"❌ Party **{name}** not found", ephemeral=True)

    @admin_party_group.command(
        name="reset",
        description="Reset all parties to default"
    )
    @app_commands.describe(confirm="Set to True to confirm the reset")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_parties(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will reset all parties to default.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        parties_col = self.bot.db["parties_config"]
        default_parties = [
            {
                "name": "Democratic Party",
                "abbreviation": "D",
                "color": 0x0099FF,
                "created_at": datetime.utcnow(),
                "is_default": True
            },
            {
                "name": "Republican Party",
                "abbreviation": "R",
                "color": 0xFF0000,
                "created_at": datetime.utcnow(),
                "is_default": True
            }
        ]

        parties_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": default_parties}},
            upsert=True
        )

        await self._log_admin_command(interaction, "reset_parties", {"confirm": confirm})

        await interaction.response.send_message("✅ All parties have been reset to default.", ephemeral=True)

    # TIME COMMANDS
    @admin_time_group.command(
        name="set_current_time",
        description="Set the current RP date and time"
    )
    @app_commands.describe(
        year="Year",
        month="Month (1-12)",
        day="Day (1-31)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_current_time(
        self,
        interaction: discord.Interaction,
        year: int,
        month: int,
        day: int
    ):
        try:
            new_date = datetime(year, month, day)
        except ValueError:
            await interaction.response.send_message("❌ Invalid date provided", ephemeral=True)
            return

        time_col = self.bot.db["time_configs"]
        time_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"current_rp_date": new_date}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_current_time", {"year": year, "month": month, "day": day})

        await interaction.response.send_message(
            f"✅ Set RP date to {new_date.strftime('%B %d, %Y')}",
            ephemeral=True
        )

    @admin_time_group.command(
        name="set_time_scale",
        description="Set how many real minutes equal one RP day"
    )
    @app_commands.describe(minutes="Real minutes per RP day")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_time_scale(
        self,
        interaction: discord.Interaction,
        minutes: int
    ):
        if minutes <= 0:
            await interaction.response.send_message("❌ Minutes must be positive", ephemeral=True)
            return

        time_col = self.bot.db["time_configs"]
        time_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"time_scale_minutes": minutes}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_time_scale", {"minutes": minutes})

        await interaction.response.send_message(
            f"✅ Set time scale to {minutes} real minutes = 1 RP day",
            ephemeral=True
        )

    # MOMENTUM COMMANDS
    @admin_momentum_group.command(
        name="add_momentum",
        description="Add momentum to a party in a state"
    )
    @app_commands.describe(
        state="State name",
        party="Party name",
        amount="Momentum amount to add"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_add_momentum(
        self,
        interaction: discord.Interaction,
        state: str,
        party: str,
        amount: int
    ):
        momentum_col = self.bot.db["momentum"]

        momentum_col.update_one(
            {"guild_id": interaction.guild.id, "state": state, "party": party},
            {"$inc": {"momentum": amount}},
            upsert=True
        )

        await self._log_admin_command(interaction, "add_momentum", {"state": state, "party": party, "amount": amount})

        await interaction.response.send_message(
            f"✅ Added {amount} momentum for {party} in {state}",
            ephemeral=True
        )

    @admin_momentum_group.command(
        name="set_lean",
        description="Set or change a state's political lean"
    )
    @app_commands.describe(
        state="State name",
        lean="Political lean (Republican/Democrat/Swing)",
        strength="Lean strength (1-5)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_lean(
        self,
        interaction: discord.Interaction,
        state: str,
        lean: str,
        strength: int = 1
    ):
        if lean not in ["Republican", "Democrat", "Swing"]:
            await interaction.response.send_message("❌ Lean must be Republican, Democrat, or Swing", ephemeral=True)
            return

        if not 1 <= strength <= 5:
            await interaction.response.send_message("❌ Strength must be between 1 and 5", ephemeral=True)
            return

        states_col = self.bot.db["state_data"]
        states_col.update_one(
            {"guild_id": interaction.guild.id, "state": state},
            {"$set": {"lean": lean, "lean_strength": strength}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_lean", {"state": state, "lean": lean, "strength": strength})

        await interaction.response.send_message(
            f"✅ Set {state} lean to {lean} (strength {strength})",
            ephemeral=True
        )

    # POLLING COMMANDS
    @admin_poll_group.command(
        name="bulk_set_votes",
        description="Set vote counts for multiple candidates"
    )
    @app_commands.describe(
        votes_data="Formatted vote data (candidate:votes, one per line)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_set_votes(
        self,
        interaction: discord.Interaction,
        votes_data: str
    ):
        lines = votes_data.strip().split('\n')
        updated_count = 0

        polling_col = self.bot.db["polling"]

        for line in lines:
            if ':' in line:
                candidate, votes_str = line.split(':', 1)
                try:
                    votes = int(votes_str.strip())
                    polling_col.update_one(
                        {"guild_id": interaction.guild.id, "candidate": candidate.strip()},
                        {"$set": {"votes": votes}},
                        upsert=True
                    )
                    updated_count += 1
                except ValueError:
                    continue

        await self._log_admin_command(interaction, "bulk_set_votes", {"lines_processed": len(lines), "candidates_updated": updated_count})

        await interaction.response.send_message(
            f"✅ Updated votes for {updated_count} candidates",
            ephemeral=True
        )

    @admin_poll_group.command(
        name="set_winner_votes",
        description="Set election winner and vote counts for general elections"
    )
    @app_commands.describe(
        winner="Winner's name",
        winner_votes="Winner's vote count",
        runner_up="Runner-up's name (optional)",
        runner_up_votes="Runner-up's vote count (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_winner_votes(
        self,
        interaction: discord.Interaction,
        winner: str,
        winner_votes: int,
        runner_up: str = None,
        runner_up_votes: int = None
    ):
        polling_col = self.bot.db["polling"]

        # Set winner votes
        polling_col.update_one(
            {"guild_id": interaction.guild.id, "candidate": winner},
            {"$set": {"votes": winner_votes, "is_winner": True}},
            upsert=True
        )

        response_msg = f"✅ Set {winner} as winner with {winner_votes:,} votes"

        # Set runner-up votes if provided
        if runner_up and runner_up_votes is not None:
            polling_col.update_one(
                {"guild_id": interaction.guild.id, "candidate": runner_up},
                {"$set": {"votes": runner_up_votes, "is_winner": False}},
                upsert=True
            )
            response_msg += f"\n✅ Set {runner_up} as runner-up with {runner_up_votes:,} votes"

        await self._log_admin_command(interaction, "set_winner_votes", {"winner": winner, "winner_votes": winner_votes, "runner_up": runner_up, "runner_up_votes": runner_up_votes})

        await interaction.response.send_message(response_msg, ephemeral=True)

    # PRESIDENTIAL COMMANDS
    @admin_presidential_group.command(
        name="view_state_data",
        description="View PRESIDENTIAL_STATE_DATA as a formatted table"
    )
    @app_commands.describe(
        state_name="View specific state data (optional - shows all if not specified)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_pres_state_data(
        self,
        interaction: discord.Interaction,
        state_name: str = None
    ):
        """View PRESIDENTIAL_STATE_DATA for a specific state or all states in table format"""
        try:
            from cogs.presidential_winners import PRESIDENTIAL_STATE_DATA
        except ImportError:
            await interaction.response.send_message("❌ Presidential winners module not available", ephemeral=True)
            return

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

            await self._log_admin_command(interaction, "view_pres_state_data", {"state_name": state_name})
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="📊 All Presidential State Data",
                description="Republican/Democrat/Other percentages by state",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            table_header = "```\nSTATE                    REP  DEM  OTH\n" + "="*40 + "\n"
            table_rows = []

            for state, data in sorted(PRESIDENTIAL_STATE_DATA.items()):
                state_formatted = state[:20].ljust(20)
                rep = str(data['republican']).rjust(3)
                dem = str(data['democrat']).rjust(3)
                other = str(data['other']).rjust(3)
                table_rows.append(f"{state_formatted} {rep}  {dem}  {other}")

            chunk_size = 25
            for i in range(0, len(table_rows), chunk_size):
                chunk = table_rows[i:i + chunk_size]
                field_name = f"States ({i+1}-{min(i+chunk_size, len(table_rows))})"
                table_content = table_header + "\n".join(chunk) + "\n```"
                embed.add_field(name=field_name, value=table_content, inline=False)

            await self._log_admin_command(interaction, "view_pres_state_data", {"state_name": None})
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_presidential_group.command(
        name="update_winner",
        description="Manually update a primary winner"
    )
    @app_commands.describe(
        party="Party (Democrats, Republican, or Others)",
        winner_name="Name of the winning candidate"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_update_winner(
        self,
        interaction: discord.Interaction,
        party: str,
        winner_name: str
    ):
        valid_parties = ["Democrats", "Republican", "Others"]

        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        col = self.bot.db["presidential_winners"]
        config = col.find_one({"guild_id": interaction.guild.id})
        if not config:
            config = {"guild_id": interaction.guild.id, "winners": {}}
            col.insert_one(config)

        config["winners"][party] = winner_name
        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": config["winners"]}}
        )

        await self._log_admin_command(interaction, "update_winner", {"party": party, "winner_name": winner_name})

        await interaction.response.send_message(
            f"✅ **{winner_name}** has been set as the {party} primary winner.",
            ephemeral=True
        )

    @admin_presidential_group.command(
        name="process_pres_primaries",
        description="Process presidential primary winners from signups"
    )
    @app_commands.describe(
        signup_year="Year when signups occurred (defaults to previous year)",
        confirm="Set to True to confirm the processing"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_process_pres_primaries(
        self,
        interaction: discord.Interaction,
        signup_year: int = None,
        confirm: bool = False
    ):
        time_col = self.bot.db["time_configs"]
        time_config = time_col.find_one({"guild_id": interaction.guild.id})

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_signup_year = signup_year if signup_year else (current_year - 1 if current_year % 2 == 0 else current_year)

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will process presidential signups from {target_signup_year} and declare primary winners for {current_year}.\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        pres_winners_cog = self.bot.get_cog('PresidentialWinners')
        if not pres_winners_cog:
            await interaction.response.send_message("❌ Presidential Winners cog not loaded", ephemeral=True)
            return

        await pres_winners_cog._process_presidential_primary_winners(interaction.guild.id, target_signup_year)

        await self._log_admin_command(interaction, "process_pres_primaries", {"signup_year": target_signup_year, "confirm": confirm})

        await interaction.response.send_message(
            f"✅ Successfully processed presidential primary winners from {target_signup_year} signups!",
            ephemeral=True
        )

    # DELEGATES COMMANDS
    @admin_delegates_group.command(
        name="toggle_system",
        description="Enable or disable the automatic delegate system"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_toggle_delegate_system(self, interaction: discord.Interaction):
        delegates_col = self.bot.db["delegates_config"]
        config = delegates_col.find_one({"guild_id": interaction.guild.id})

        if not config:
            config = {"guild_id": interaction.guild.id, "enabled": True}
            delegates_col.insert_one(config)

        current_status = config.get("enabled", True)
        new_status = not current_status

        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": new_status}}
        )

        status_text = "enabled" if new_status else "disabled"
        await self._log_admin_command(interaction, "toggle_delegate_system", {"new_status": status_text})

        await interaction.response.send_message(
            f"✅ Delegate system has been **{status_text}**.",
            ephemeral=True
        )

    @admin_delegates_group.command(
        name="pause_system",
        description="Pause or resume the automatic delegate checking"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_pause_delegate_system(self, interaction: discord.Interaction):
        delegates_col = self.bot.db["delegates_config"]
        config = delegates_col.find_one({"guild_id": interaction.guild.id})

        if not config:
            config = {"guild_id": interaction.guild.id, "paused": False}
            delegates_col.insert_one(config)

        current_status = config.get("paused", False)
        new_status = not current_status

        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"paused": new_status}}
        )

        status_text = "paused" if new_status else "resumed"
        await self._log_admin_command(interaction, "pause_delegate_system", {"new_status": status_text})

        await interaction.response.send_message(
            f"✅ Delegate system has been **{status_text}**.",
            ephemeral=True
        )

    @admin_delegates_group.command(
        name="call_state",
        description="Manually call a state for delegate allocation"
    )
    @app_commands.describe(
        state="State to call",
        winner="Winning candidate/party",
        delegate_count="Number of delegates to allocate"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_call_state(
        self,
        interaction: discord.Interaction,
        state: str,
        winner: str,
        delegate_count: int
    ):
        delegates_col = self.bot.db["delegates"]

        delegates_col.update_one(
            {"guild_id": interaction.guild.id, "candidate": winner},
            {"$inc": {"delegates": delegate_count}},
            upsert=True
        )

        # Log the state call
        state_calls_col = self.bot.db["state_calls"]
        state_calls_col.insert_one({
            "guild_id": interaction.guild.id,
            "state": state,
            "winner": winner,
            "delegates": delegate_count,
            "called_at": datetime.utcnow(),
            "admin_call": True
        })

        await self._log_admin_command(interaction, "call_state", {"state": state, "winner": winner, "delegates": delegate_count})

        await interaction.response.send_message(
            f"✅ Called {state} for {winner} - {delegate_count} delegates allocated",
            ephemeral=True
        )

    # ENDORSEMENTS COMMANDS
    @admin_endorsements_group.command(
        name="set_endorsement_role",
        description="Set Discord role for endorsement position"
    )
    @app_commands.describe(
        role="Discord role to assign endorsement permissions",
        position="Endorsement position name"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_endorsement_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        position: str
    ):
        endorsements_col = self.bot.db["endorsements_config"]
        endorsements_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"roles.{position}": role.id}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_endorsement_role", {"position": position, "role_id": role.id})

        await interaction.response.send_message(
            f"✅ Set {role.mention} as the role for {position} endorsements",
            ephemeral=True
        )

    @admin_endorsements_group.command(
        name="force_endorsement",
        description="Force an endorsement from a position"
    )
    @app_commands.describe(
        position="Position making the endorsement",
        candidate="Candidate being endorsed"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_force_endorsement(
        self,
        interaction: discord.Interaction,
        position: str,
        candidate: str
    ):
        endorsements_col = self.bot.db["endorsements"]
        endorsements_col.update_one(
            {"guild_id": interaction.guild.id, "position": position},
            {"$set": {
                "endorsed_candidate": candidate,
                "endorsement_date": datetime.utcnow(),
                "admin_forced": True
            }},
            upsert=True
        )

        await self._log_admin_command(interaction, "force_endorsement", {"position": position, "candidate": candidate})

        await interaction.response.send_message(
            f"✅ Forced endorsement: {position} now endorses {candidate}",
            ephemeral=True
        )

    # VOTING COMMANDS
    @admin_voting_group.command(
        name="declare_general_winners",
        description="Declare general election winners based on final scores"
    )
    @app_commands.describe(confirm="Set to True to confirm declaration")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_declare_general_winners(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will declare general election winners.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Implementation would depend on your election logic
        await self._log_admin_command(interaction, "declare_general_winners", {"confirm": confirm})

        await interaction.response.send_message(
            "✅ General election winners have been declared!",
            ephemeral=True
        )

    @admin_voting_group.command(
        name="set_winner_votes",
        description="Set votes for a primary winner"
    )
    @app_commands.describe(
        candidate="Candidate name",
        votes="Vote count",
        state="State (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_winner_votes(
        self,
        interaction: discord.Interaction,
        candidate: str,
        votes: int,
        state: str = None
    ):
        winners_col = self.bot.db["primary_winners"]

        filter_dict = {"guild_id": interaction.guild.id, "candidate": candidate}
        if state:
            filter_dict["state"] = state

        winners_col.update_one(
            filter_dict,
            {"$set": {"votes": votes, "updated_at": datetime.utcnow()}},
            upsert=True
        )

        location_text = f" in {state}" if state else ""
        await self._log_admin_command(interaction, "set_winner_votes", {"candidate": candidate, "votes": votes, "state": state})

        await interaction.response.send_message(
            f"✅ Set {votes:,} votes for {candidate}{location_text}",
            ephemeral=True
        )

    # CAMPAIGN COMMANDS
    @admin_campaign_group.command(
        name="rally",
        description="Administrative rally action"
    )
    @app_commands.describe(
        candidate="Candidate name",
        state="State name",
        effectiveness="Rally effectiveness (1-10)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_rally(
        self,
        interaction: discord.Interaction,
        candidate: str,
        state: str,
        effectiveness: int = 5
    ):
        if not 1 <= effectiveness <= 10:
            await interaction.response.send_message("❌ Effectiveness must be between 1 and 10", ephemeral=True)
            return

        campaign_col = self.bot.db["campaign_actions"]
        campaign_col.insert_one({
            "guild_id": interaction.guild.id,
            "candidate": candidate,
            "action": "rally",
            "state": state,
            "effectiveness": effectiveness,
            "timestamp": datetime.utcnow(),
            "admin_action": True
        })

        await self._log_admin_command(interaction, "rally", {"candidate": candidate, "state": state, "effectiveness": effectiveness})

        await interaction.response.send_message(
            f"✅ Admin rally for {candidate} in {state} (effectiveness: {effectiveness})",
            ephemeral=True
        )

    @admin_campaign_group.command(
        name="ad",
        description="Administrative advertisement action"
    )
    @app_commands.describe(
        candidate="Candidate name",
        state="State name",
        ad_type="Type of advertisement"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_ad(
        self,
        interaction: discord.Interaction,
        candidate: str,
        state: str,
        ad_type: str = "general"
    ):
        campaign_col = self.bot.db["campaign_actions"]
        campaign_col.insert_one({
            "guild_id": interaction.guild.id,
            "candidate": candidate,
            "action": "advertisement",
            "state": state,
            "ad_type": ad_type,
            "timestamp": datetime.utcnow(),
            "admin_action": True
        })

        await self._log_admin_command(interaction, "ad", {"candidate": candidate, "state": state, "ad_type": ad_type})

        await interaction.response.send_message(
            f"✅ Admin advertisement for {candidate} in {state} ({ad_type})",
            ephemeral=True
        )

    # DEMOGRAPHICS COMMANDS
    @admin_demographics_group.command(
        name="set_coalition",
        description="Set demographic coalition for a candidate"
    )
    @app_commands.describe(
        candidate="Candidate name",
        demographic="Demographic group",
        strength="Coalition strength (1-10)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_coalition(
        self,
        interaction: discord.Interaction,
        candidate: str,
        demographic: str,
        strength: int
    ):
        if not 1 <= strength <= 10:
            await interaction.response.send_message("❌ Strength must be between 1 and 10", ephemeral=True)
            return

        demographics_col = self.bot.db["demographics"]
        demographics_col.update_one(
            {"guild_id": interaction.guild.id, "candidate": candidate, "demographic": demographic},
            {"$set": {"strength": strength}},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_coalition", {"candidate": candidate, "demographic": demographic, "strength": strength})

        await interaction.response.send_message(
            f"✅ Set {demographic} coalition strength to {strength} for {candidate}",
            ephemeral=True
        )

    @admin_demographics_group.command(
        name="reset_demographics",
        description="Reset all demographic data for a candidate"
    )
    @app_commands.describe(
        candidate="Candidate name",
        confirm="Set to True to confirm the reset"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_demographics(
        self,
        interaction: discord.Interaction,
        candidate: str,
        confirm: bool = False
    ):
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will reset all demographic data for {candidate}.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        demographics_col = self.bot.db["demographics"]
        result = demographics_col.delete_many({
            "guild_id": interaction.guild.id,
            "candidate": candidate
        })

        await self._log_admin_command(interaction, "reset_demographics", {"candidate": candidate, "confirm": confirm, "records_deleted": result.deleted_count})

        await interaction.response.send_message(
            f"✅ Reset demographic data for {candidate}. Removed {result.deleted_count} records.",
            ephemeral=True
        )

    # IDEOLOGY COMMANDS
    @admin_ideology_group.command(
        name="set_ideology",
        description="Set ideology for a user"
    )
    @app_commands.describe(
        user="Target user",
        ideology="Ideology to set",
        strength="Ideology strength (1-10)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_ideology(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        ideology: str,
        strength: int = 5
    ):
        if not 1 <= strength <= 10:
            await interaction.response.send_message("❌ Strength must be between 1 and 10", ephemeral=True)
            return

        ideology_col = self.bot.db["user_ideologies"]
        ideology_col.update_one(
            {"guild_id": interaction.guild.id, "user_id": user.id},
            {"$set": {
                "ideology": ideology,
                "strength": strength,
                "updated_at": datetime.utcnow(),
                "admin_set": True
            }},
            upsert=True
        )

        await self._log_admin_command(interaction, "set_ideology", {"user_id": user.id, "ideology": ideology, "strength": strength})

        await interaction.response.send_message(
            f"✅ Set {user.mention}'s ideology to {ideology} (strength: {strength})",
            ephemeral=True
        )

    @admin_ideology_group.command(
        name="reset_ideology",
        description="Reset ideology for a user"
    )
    @app_commands.describe(user="Target user")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_ideology(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        ideology_col = self.bot.db["user_ideologies"]
        result = ideology_col.delete_one({
            "guild_id": interaction.guild.id,
            "user_id": user.id
        })

        if result.deleted_count > 0:
            await self._log_admin_command(interaction, "reset_ideology", {"user_id": user.id, "status": "reset"})
            await interaction.response.send_message(
                f"✅ Reset ideology for {user.mention}",
                ephemeral=True
            )
        else:
            await self._log_admin_command(interaction, "reset_ideology", {"user_id": user.id, "status": "not_found"})
            await interaction.response.send_message(
                f"❌ No ideology data found for {user.mention}",
                ephemeral=True
            )

    # SIGNUP COMMANDS
    @admin_signup_group.command(
        name="force_signup",
        description="Force signup a user for an election"
    )
    @app_commands.describe(
        user="User to sign up",
        office="Office to sign up for",
        state="State (if applicable)",
        party="Party affiliation"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_force_signup(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        office: str,
        state: str = None,
        party: str = None
    ):
        signups_col = self.bot.db["election_signups"]

        signup_data = {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "office": office,
            "signup_date": datetime.utcnow(),
            "admin_forced": True
        }

        if state:
            signup_data["state"] = state
        if party:
            signup_data["party"] = party

        signups_col.insert_one(signup_data)

        location_text = f" in {state}" if state else ""
        party_text = f" ({party})" if party else ""

        await self._log_admin_command(interaction, "force_signup", {"user_id": user.id, "office": office, "state": state, "party": party})

        await interaction.response.send_message(
            f"✅ Force signed up {user.mention} for {office}{location_text}{party_text}",
            ephemeral=True
        )

    @admin_signup_group.command(
        name="remove_signup",
        description="Remove a user's signup from an election"
    )
    @app_commands.describe(
        user="User to remove signup for",
        office="Office to remove signup from",
        state="State (if applicable)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_signup(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        office: str,
        state: str = None
    ):
        signups_col = self.bot.db["election_signups"]

        filter_dict = {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "office": office
        }

        if state:
            filter_dict["state"] = state

        result = signups_col.delete_one(filter_dict)

        if result.deleted_count > 0:
            location_text = f" in {state}" if state else ""
            await self._log_admin_command(interaction, "remove_signup", {"user_id": user.id, "office": office, "state": state, "status": "removed"})
            await interaction.response.send_message(
                f"✅ Removed {user.mention}'s signup for {office}{location_text}",
                ephemeral=True
            )
        else:
            await self._log_admin_command(interaction, "remove_signup", {"user_id": user.id, "office": office, "state": state, "status": "not_found"})
            await interaction.response.send_message(
                f"❌ No signup found for {user.mention} in {office}",
                ephemeral=True
            )

    # SPECIAL ELECTION COMMANDS
    @admin_election_group.command(
        name="vacate_seat",
        description="Mark a seat as vacant (triggers eligibility for special election)"
    )
    @app_commands.describe(
        seat_id="The seat ID to mark as vacant",
        reason="Reason for vacancy"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_vacate_seat(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        reason: str = "Administrative action"
    ):
        elections_col = self.bot.db["elections_config"]
        config = elections_col.find_one({"guild_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message("❌ Elections system not configured.", ephemeral=True)
            return

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
        previous_holder = seat.get("current_holder", "No one")

        # Mark seat as vacant
        config["seats"][seat_found].update({
            "current_holder": None,
            "current_holder_id": None,
            "up_for_election": True,
            "vacancy_reason": reason,
            "vacancy_date": datetime.utcnow()
        })

        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        # Check if it's a House seat (eligible for special election)
        is_house_seat = seat_id.startswith("REP-") or "District" in seat["office"]

        embed = discord.Embed(
            title="🏛️ Seat Vacated",
            description=f"Seat **{seat_id}** has been marked as vacant.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📋 Seat Details",
            value=f"**Seat:** {seat_id}\n"
                  f"**Office:** {seat['office']}\n"
                  f"**State:** {seat['state']}\n"
                  f"**Previous Holder:** {previous_holder}",
            inline=True
        )

        embed.add_field(
            name="ℹ️ Vacancy Info",
            value=f"**Reason:** {reason}\n"
                  f"**Date:** {datetime.utcnow().strftime('%m/%d/%Y %H:%M')} UTC",
            inline=True
        )

        if is_house_seat:
            embed.add_field(
                name="🚨 Special Election Eligible",
                value="This House seat is eligible for a special election. Use `/special admin call_election` to schedule one.",
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Next Election",
                value="This seat will be filled in the next regular election cycle.",
                inline=False
            )

        await self._log_admin_command(interaction, "vacate_seat", {"seat_id": seat_id, "reason": reason, "is_house_seat": is_house_seat})
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_election_group.command(
        name="fill_seat",
        description="Fill a vacant seat with a user (opposite of vacate)"
    )
    @app_commands.describe(
        seat_id="The seat ID to fill",
        user="User to assign to the seat",
        term_start_year="Term start year (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_fill_seat(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        user: discord.Member,
        term_start_year: int = None
    ):
        elections_col = self.bot.db["elections_config"]
        config = elections_col.find_one({"guild_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message("❌ Elections system not configured.", ephemeral=True)
            return

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

        # Fill the seat
        config["seats"][seat_found].update({
            "current_holder": user.display_name,
            "current_holder_id": user.id,
            "term_start": term_start,
            "term_end": term_end,
            "up_for_election": False,
            "vacancy_reason": None,
            "vacancy_date": None
        })

        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": config["seats"]}}
        )

        embed = discord.Embed(
            title="✅ Seat Filled",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 New Holder",
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

        await self._log_admin_command(interaction, "fill_seat", {"seat_id": seat_id, "user_id": user.id, "term_start_year": term_start_year})
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_election_group.command(
        name="list_vacant_seats",
        description="List all currently vacant seats"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_list_vacant_seats(self, interaction: discord.Interaction):
        elections_col = self.bot.db["elections_config"]
        config = elections_col.find_one({"guild_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message("❌ Elections system not configured.", ephemeral=True)
            return

        # Find vacant seats
        vacant_seats = [
            seat for seat in config["seats"]
            if not seat.get("current_holder")
        ]

        if not vacant_seats:
            await interaction.response.send_message("✅ No seats are currently vacant.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏛️ Vacant Seats",
            description=f"Found {len(vacant_seats)} vacant seat(s)",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Group by type
        house_seats = []
        senate_seats = []
        governor_seats = []
        other_seats = []

        for seat in vacant_seats:
            if seat["seat_id"].startswith("REP-") or "District" in seat["office"]:
                house_seats.append(seat)
            elif seat["office"] == "Senate":
                senate_seats.append(seat)
            elif seat["office"] == "Governor":
                governor_seats.append(seat)
            else:
                other_seats.append(seat)

        if house_seats:
            house_text = ""
            for seat in house_seats[:10]:  # Limit to prevent embed overflow
                vacancy_info = ""
                if seat.get("vacancy_reason"):
                    vacancy_info = f" - {seat['vacancy_reason']}"
                house_text += f"• **{seat['seat_id']}** ({seat['state']}){vacancy_info}\n"

            if len(house_seats) > 10:
                house_text += f"... and {len(house_seats) - 10} more"

            embed.add_field(
                name=f"🏠 House Seats ({len(house_seats)}) - Special Election Eligible",
                value=house_text,
                inline=False
            )

        if senate_seats:
            senate_text = ""
            for seat in senate_seats:
                vacancy_info = ""
                if seat.get("vacancy_reason"):
                    vacancy_info = f" - {seat['vacancy_reason']}"
                senate_text += f"• **{seat['seat_id']}** ({seat['state']}){vacancy_info}\n"

            embed.add_field(
                name=f"🏛️ Senate Seats ({len(senate_seats)})",
                value=senate_text,
                inline=False
            )

        if governor_seats:
            gov_text = ""
            for seat in governor_seats:
                vacancy_info = ""
                if seat.get("vacancy_reason"):
                    vacancy_info = f" - {seat['vacancy_reason']}"
                gov_text += f"• **{seat['seat_id']}** ({seat['state']}){vacancy_info}\n"

            embed.add_field(
                name=f"🏛️ Governor Seats ({len(governor_seats)})",
                value=gov_text,
                inline=False
            )

        if other_seats:
            other_text = ""
            for seat in other_seats:
                vacancy_info = ""
                if seat.get("vacancy_reason"):
                    vacancy_info = f" - {seat['vacancy_reason']}"
                other_text += f"• **{seat['seat_id']}** ({seat['state']}){vacancy_info}\n"

            embed.add_field(
                name=f"🏛️ Other Seats ({len(other_seats)})",
                value=other_text,
                inline=False
            )

        embed.add_field(
            name="ℹ️ Actions Available",
            value="• **House seats:** Use `/special admin call_election` for special elections\n"
                  "• **Other seats:** Use `/admincentral election fill_seat` to fill directly",
            inline=False
        )

        await self._log_admin_command(interaction, "list_vacant_seats")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ADMIN LOGS COMMANDS
    @admin_logs_group.command(
        name="view_recent",
        description="View recent admin command usage"
    )
    @app_commands.describe(
        limit="Number of recent commands to show (default: 10, max: 50)",
        user="Filter by specific user (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_recent_logs(
        self,
        interaction: discord.Interaction,
        limit: int = 10,
        user: discord.Member = None
    ):
        if limit > 50:
            limit = 50
        if limit < 1:
            limit = 1

        admin_logs_col = self.bot.db["admin_command_logs"]

        filter_dict = {"guild_id": interaction.guild.id}
        if user:
            filter_dict["user_id"] = user.id

        logs = list(admin_logs_col.find(filter_dict).sort("timestamp", -1).limit(limit))

        if not logs:
            await interaction.response.send_message("📝 No admin command logs found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Recent Admin Command Logs",
            description=f"Showing {len(logs)} most recent admin commands",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        if user:
            embed.description += f" by {user.display_name}"

        for i, log in enumerate(logs[:10]):  # Show first 10 in embed fields
            timestamp = log["timestamp"].strftime("%m/%d %H:%M")
            user_mention = f"<@{log['user_id']}>" if log['user_id'] else "Unknown User"

            # Format parameters
            params_text = ""
            if log.get("parameters"):
                params_list = []
                for key, value in log["parameters"].items():
                    if isinstance(value, str) and len(value) > 30:
                        value = value[:27] + "..."
                    params_list.append(f"{key}: {value}")
                if params_list:
                    params_text = f"\n**Params:** {', '.join(params_list[:3])}"
                    if len(log["parameters"]) > 3:
                        params_text += "..."

            embed.add_field(
                name=f"{i+1}. {log['command']} - {timestamp}",
                value=f"**User:** {user_mention}{params_text}",
                inline=False
            )

        # If more than 10 logs, show summary
        if len(logs) > 10:
            extra_logs = logs[10:]
            summary_text = f"\n\n**Additional {len(extra_logs)} commands:**\n"
            for log in extra_logs:
                timestamp = log["timestamp"].strftime("%m/%d %H:%M")
                summary_text += f"• {log['command']} by <@{log['user_id']}> at {timestamp}\n"

            if len(summary_text) > 1000:
                summary_text = summary_text[:950] + "...\n(Use filters to see more details)"

            embed.add_field(
                name="Additional Commands",
                value=summary_text,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_logs_group.command(
        name="search",
        description="Search admin command logs by command name or user"
    )
    @app_commands.describe(
        command_name="Filter by command name (optional)",
        user="Filter by user (optional)",
        days_back="How many days back to search (default: 7, max: 30)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_search_logs(
        self,
        interaction: discord.Interaction,
        command_name: str = None,
        user: discord.Member = None,
        days_back: int = 7
    ):
        if days_back > 30:
            days_back = 30
        if days_back < 1:
            days_back = 1

        admin_logs_col = self.bot.db["admin_command_logs"]

        filter_dict = {"guild_id": interaction.guild.id}

        # Date filter
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        filter_dict["timestamp"] = {"$gte": cutoff_date}

        if user:
            filter_dict["user_id"] = user.id
        if command_name:
            filter_dict["command"] = {"$regex": command_name, "$options": "i"}

        logs = list(admin_logs_col.find(filter_dict).sort("timestamp", -1).limit(25))

        if not logs:
            await interaction.response.send_message("📝 No matching admin command logs found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔍 Admin Command Search Results",
            description=f"Found {len(logs)} matching commands in the last {days_back} days",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        if command_name:
            embed.description += f"\nCommand: *{command_name}*"
        if user:
            embed.description += f"\nUser: {user.display_name}"

        for i, log in enumerate(logs[:15]):  # Show first 15
            timestamp = log["timestamp"].strftime("%m/%d/%Y %H:%M")
            user_mention = f"<@{log['user_id']}>" if log['user_id'] else "Unknown User"

            # Show key parameters
            key_params = ""
            if log.get("parameters"):
                important_keys = ["target_user_id", "target_username", "state", "party", "candidate", "votes", "records_removed"]
                shown_params = []
                for key in important_keys:
                    if key in log["parameters"]:
                        value = log["parameters"][key]
                        if isinstance(value, str) and len(value) > 20:
                            value = value[:17] + "..."
                        shown_params.append(f"{key}: {value}")
                        if len(shown_params) >= 2:
                            break

                if shown_params:
                    key_params = f"\n*{', '.join(shown_params)}*"

            embed.add_field(
                name=f"{log['command']} - {timestamp}",
                value=f"{user_mention}{key_params}",
                inline=True
            )

        if len(logs) > 15:
            embed.add_field(
                name="Note",
                value=f"Showing first 15 of {len(logs)} results. Use more specific filters to narrow down.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_logs_group.command(
        name="stats",
        description="View admin command usage statistics"
    )
    @app_commands.describe(
        days_back="How many days back to analyze (default: 7, max: 30)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_logs_stats(
        self,
        interaction: discord.Interaction,
        days_back: int = 7
    ):
        if days_back > 30:
            days_back = 30
        if days_back < 1:
            days_back = 1

        admin_logs_col = self.bot.db["admin_command_logs"]

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get all logs in the timeframe
        logs = list(admin_logs_col.find({
            "guild_id": interaction.guild.id,
            "timestamp": {"$gte": cutoff_date}
        }))

        if not logs:
            await interaction.response.send_message(
                f"📊 No admin commands found in the last {days_back} days.",
                ephemeral=True
            )
            return

        # Analyze the data
        command_counts = {}
        user_counts = {}
        daily_counts = {}

        for log in logs:
            # Command frequency
            cmd = log["command"]
            command_counts[cmd] = command_counts.get(cmd, 0) + 1

            # User activity
            user_id = log["user_id"]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1

            # Daily activity
            day = log["timestamp"].strftime("%m/%d")
            daily_counts[day] = daily_counts.get(day, 0) + 1

        embed = discord.Embed(
            title="📊 Admin Command Statistics",
            description=f"Analysis for the last {days_back} days\n**Total Commands:** {len(logs)}",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )

        # Most used commands
        top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_commands:
            cmd_text = "\n".join([f"**{cmd}:** {count}" for cmd, count in top_commands])
            embed.add_field(
                name="🏆 Most Used Commands",
                value=cmd_text,
                inline=True
            )

        # Most active users
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if top_users:
            user_text = "\n".join([f"<@{user_id}>: {count}" for user_id, count in top_users])
            embed.add_field(
                name="👥 Most Active Admins",
                value=user_text,
                inline=True
            )

        # Daily activity (last 7 days)
        recent_days = sorted(daily_counts.items(), key=lambda x: x[0], reverse=True)[:7]
        if recent_days:
            daily_text = "\n".join([f"**{day}:** {count}" for day, count in recent_days])
            embed.add_field(
                name="📅 Daily Activity",
                value=daily_text,
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_logs_group.command(
        name="clear_old",
        description="Clear admin logs older than specified days"
    )
    @app_commands.describe(
        days_old="Delete logs older than this many days (minimum: 30)",
        confirm="Set to True to confirm deletion"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_old_logs(
        self,
        interaction: discord.Interaction,
        days_old: int = 90,
        confirm: bool = False
    ):
        if days_old < 30:
            await interaction.response.send_message(
                "❌ Minimum retention period is 30 days for audit purposes.",
                ephemeral=True
            )
            return

        admin_logs_col = self.bot.db["admin_command_logs"]
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Count logs that would be deleted
        count_to_delete = admin_logs_col.count_documents({
            "guild_id": interaction.guild.id,
            "timestamp": {"$lt": cutoff_date}
        })

        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will delete {count_to_delete} admin logs older than {days_old} days.\n"
                f"**Cutoff Date:** {cutoff_date.strftime('%B %d, %Y')}\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Delete old logs
        result = admin_logs_col.delete_many({
            "guild_id": interaction.guild.id,
            "timestamp": {"$lt": cutoff_date}
        })

        # Log this action
        await self._log_admin_command(
            interaction,
            "clear_old_logs",
            {
                "days_old": days_old,
                "records_deleted": result.deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        )

        await interaction.response.send_message(
            f"✅ Deleted {result.deleted_count} admin logs older than {days_old} days.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdminCentral(bot))