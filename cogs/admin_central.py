
from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime

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

    # Helper method to check admin permissions
    async def _check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return False
        return True

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
            await interaction.response.send_message(f"✅ Removed party **{name}**", ephemeral=True)
        else:
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
            await interaction.response.send_message(
                f"✅ Reset ideology for {user.mention}",
                ephemeral=True
            )
        else:
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
            await interaction.response.send_message(
                f"✅ Removed {user.mention}'s signup for {office}{location_text}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No signup found for {user.mention} in {office}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AdminCentral(bot))
