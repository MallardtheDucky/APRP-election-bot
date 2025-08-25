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


async def setup(bot):
    await bot.add_cog(AdminCentral(bot))