from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime

class AdminCentral(commands.Cog):
    """Centralized admin commands to reduce total command count"""

    def __init__(self, bot):
        self.bot = bot
        print("AdminCentral cog loaded successfully")

    # Main admin group - this replaces individual admin groups in other cogs
    admin_group = app_commands.Group(
        name="central",
        description="Centralized admin commands",
        default_permissions=discord.Permissions(administrator=True)
    )

    # Subgroups for different admin areas
    admin_election_group = app_commands.Group(name="election", description="Election admin commands", parent=admin_group)
    admin_party_group = app_commands.Group(name="party", description="Party admin commands", parent=admin_group)
    admin_time_group = app_commands.Group(name="time", description="Time admin commands", parent=admin_group)
    admin_poll_group = app_commands.Group(name="poll", description="Polling admin commands", parent=admin_group)
    admin_system_group = app_commands.Group(name="system", description="System admin commands", parent=admin_group)
    admin_momentum_group = app_commands.Group(name="momentum", description="Momentum admin commands", parent=admin_group)
    admin_presidential_group = app_commands.Group(name="presidential", description="Presidential election admin commands", parent=admin_group)


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

        # Reset all cooldowns for the user in the specified collection
        result = cooldowns_col.delete_many({
            "guild_id": interaction.guild.id,
            "user_id": target_user.id
        })

        await interaction.response.send_message(
            f"✅ Reset general campaign cooldowns for {target_user.mention} in collection '{collection_name}'. "
            f"Removed {result.deleted_count} cooldown record(s).",
            ephemeral=True
        )

    @admin_reset_campaign_cooldowns.autocomplete("collection_name")
    async def collection_autocomplete(self, interaction: discord.Interaction, current: str):
        collections = ["action_cooldowns", "campaign_cooldowns", "general_action_cooldowns", "election_cooldowns"]
        return [app_commands.Choice(name=col, value=col)
                for col in collections if current.lower() in col.lower()][:25]

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
        from cogs.presidential_winners import PRESIDENTIAL_STATE_DATA


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
            # Show all states in a formatted table
            embed = discord.Embed(
                title="📊 All Presidential State Data",
                description="Republican/Democrat/Other percentages by state",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Create table header
            table_header = "```\nSTATE                    REP  DEM  OTH\n" + "="*40 + "\n"
            table_rows = []

            for state, data in sorted(PRESIDENTIAL_STATE_DATA.items()):
                # Format state name to be consistent width
                state_formatted = state[:20].ljust(20)
                rep = str(data['republican']).rjust(3)
                dem = str(data['democrat']).rjust(3)
                other = str(data['other']).rjust(3)

                table_rows.append(f"{state_formatted} {rep}  {dem}  {other}")

            # Split into chunks to avoid Discord message limits
            chunk_size = 25
            for i in range(0, len(table_rows), chunk_size):
                chunk = table_rows[i:i + chunk_size]
                field_name = f"States ({i+1}-{min(i+chunk_size, len(table_rows))})"

                table_content = table_header + "\n".join(chunk) + "\n```"

                embed.add_field(
                    name=field_name,
                    value=table_content,
                    inline=False
                )

            embed.add_field(
                name="📈 Summary",
                value=f"**Total States:** {len(PRESIDENTIAL_STATE_DATA)}",
                inline=True
            )

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
        """Manually set a primary winner"""
        valid_parties = ["Democrats", "Republican", "Others"]

        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Must be one of: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        # Get or create presidential winners configuration
        col = self.bot.db["presidential_winners"]
        config = col.find_one({"guild_id": interaction.guild.id})
        if not config:
            config = {
                "guild_id": interaction.guild.id,
                "winners": {}
            }
            col.insert_one(config)

        # Update winner
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
        name="reset_winners",
        description="Reset all primary winners"
    )
    @app_commands.describe(
        confirm="Set to True to confirm the reset"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_winners(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """Reset all primary winners"""
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will reset all primary winners.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        winners_col = self.bot.db["presidential_winners"]
        winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": {}}}
        )

        # Also reset delegate primary winners
        delegates_col = self.bot.db["delegates_config"]
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"primary_winners": {}}}
        )

        await interaction.response.send_message(
            "✅ All primary winners have been reset.",
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
        """Process presidential primary winners from signups"""
        # Get time config to determine current year
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

        # Get the presidential winners cog to use its methods
        pres_winners_cog = self.bot.get_cog('PresidentialWinners')
        if not pres_winners_cog:
            await interaction.response.send_message("❌ Presidential Winners cog not loaded", ephemeral=True)
            return

        await pres_winners_cog._process_presidential_primary_winners(interaction.guild.id, target_signup_year)

        await interaction.response.send_message(
            f"✅ Successfully processed presidential primary winners from {target_signup_year} signups!",
            ephemeral=True
        )

    @admin_presidential_group.command(
        name="end_election",
        description="End presidential election and apply ideology shifts"
    )
    @app_commands.describe(
        confirm="Set to True to confirm ending the election"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_end_presidential_election(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """End presidential election, apply ideology shifts, and reset for next cycle"""
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will:\n"
                "• Apply permanent ideology shifts to all states\n"
                "• Reset all candidate points to 0\n"
                "• Update PRESIDENTIAL_STATE_DATA with current STATE_DATA values\n\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Get the presidential winners cog to use its methods
        pres_winners_cog = self.bot.get_cog('PresidentialWinners')
        if not pres_winners_cog:
            await interaction.response.send_message(
                "❌ Presidential Winners cog not loaded",
                ephemeral=True
            )
            return

        # Apply ideology shift
        changes = pres_winners_cog._apply_post_election_ideology_shift(interaction.guild.id)

        # Reset candidate points
        points_reset = pres_winners_cog._reset_all_candidate_points(interaction.guild.id)

        # Clear any incomplete text from the file

        # Also clear presidential winners to prepare for next cycle
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"winners": {}}}
        )

        # Create response embed
        embed = discord.Embed(
            title="🗳️ Presidential Election Cycle Ended",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Ideology Shifts Applied",
            value=f"**{len(changes)} states** had their baseline ideology updated\nPRESIDENTIAL_STATE_DATA now reflects current STATE_DATA values",
            inline=False
        )

        if changes:
            changes_text = ""
            for change in changes[:5]:  # Show first 5 changes
                old = change["old"]
                new = change["new"]
                changes_text += f"**{change['state']}:**\n"
                changes_text += f"  R: {old['republican']}% → {new['republican']}%\n"
                changes_text += f"  D: {old['democrat']}% → {new['democrat']}%\n"
                changes_text += f"  O: {old['other']}% → {new['other']}%\n\n"

            if len(changes) > 5:
                changes_text += f"... and {len(changes) - 5} more states"

            embed.add_field(
                name="📈 Sample Changes",
                value=changes_text[:1024],
                inline=False
            )

        embed.add_field(
            name="🔄 Points Reset",
            value=f"All candidate points reset to 0" + (" ✅" if points_reset else " ❌"),
            inline=True
        )

        embed.add_field(
            name="🎯 Next Steps",
            value="• New election cycle can now begin\n• Fresh candidates can register\n• State ideologies permanently updated",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_presidential_group.command(
        name="debug_winners_data",
        description="Debug command to view raw presidential winners data"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_debug_winners_data(
        self,
        interaction: discord.Interaction
    ):
        """Debug command to view what's stored in presidential_winners collection"""
        # Check presidential_winners collection
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_config = pres_winners_col.find_one({"guild_id": interaction.guild.id})

        # Check all_winners collection
        all_winners_col = self.bot.db["winners"]
        all_winners_config = all_winners_col.find_one({"guild_id": interaction.guild.id})

        # Check presidential_signups collection
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": interaction.guild.id})

        embed = discord.Embed(
            title="🔍 Debug: Presidential Winners Data",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Presidential winners collection
        if pres_winners_config:
            winners_data = pres_winners_config.get("winners", {})
            election_year = pres_winners_config.get("election_year", "N/A")
            embed.add_field(
                name="📊 Presidential Winners Collection",
                value=f"**Winners:** {winners_data}\n**Election Year:** {election_year}",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Presidential Winners Collection",
                value="❌ No data found",
                inline=False
            )

        # All winners collection (presidential only)
        if all_winners_config:
            presidential_all_winners = [
                w for w in all_winners_config.get("winners", [])
                if w.get("office") == "President" and w.get("primary_winner", False)
            ]
            if presidential_all_winners:
                winners_summary = []
                for w in presidential_all_winners[:3]:  # Show first 3
                    winners_summary.append(f"{w.get('candidate')} ({w.get('party')}) - Year {w.get('year')}")
                embed.add_field(
                    name="🏆 All Winners Collection (Presidential)",
                    value=f"**Count:** {len(presidential_all_winners)}\n**Sample:** {', '.join(winners_summary)}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🏆 All Winners Collection (Presidential)",
                    value="❌ No presidential primary winners found",
                    inline=False
                )
        else:
            embed.add_field(
                name="🏆 All Winners Collection",
                value="❌ No data found",
                inline=False
            )

        # Presidential signups collection
        if pres_signups_config:
            current_candidates = pres_signups_config.get("candidates", [])
            president_count = len([c for c in current_candidates if c.get("office") == "President"])
            embed.add_field(
                name="🇺🇸 Presidential Signups Collection",
                value=f"**Total Candidates:** {len(current_candidates)}\n**Presidential Candidates:** {president_count}",
                inline=False
            )
        else:
            embed.add_field(
                name="🇺🇸 Presidential Signups Collection",
                value="❌ No data found",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCentral(bot))