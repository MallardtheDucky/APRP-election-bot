from discord.ext import commands
import discord
from discord import app_commands

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="🎮 Basic Campaign Commands",
                description="Core campaign actions",
                value="basic"
            ),
            discord.SelectOption(
                label="🏛️ Presidential Commands",
                description="Presidential campaign actions",
                value="presidential"
            ),
            discord.SelectOption(
                label="🏛️ PAC Commands",
                description="Political Action Committee commands",
                value="pac"
            ),
            discord.SelectOption(
                label="📊 Polling Commands",
                description="Polling and survey commands",
                value="polling"
            ),
            discord.SelectOption(
                label="⏰ Time & Phase Commands",
                description="Election timing and phases",
                value="time"
            ),
            discord.SelectOption(
                label="🏛️ Election Seat Management",
                description="Managing election seats",
                value="seats"
            ),
            discord.SelectOption(
                label="🔧 Admin - Election Management",
                description="Admin election tools",
                value="admin_election"
            ),
            discord.SelectOption(
                label="🔧 Admin - Time & Cycle Management",
                description="Admin time controls",
                value="admin_time"
            ),
            discord.SelectOption(
                label="🔧 Admin - Seat & State Management",
                description="Admin seat/state tools",
                value="admin_seats"
            ),
            discord.SelectOption(
                label="🔧 Admin - Setup & Configuration",
                description="Admin setup commands",
                value="admin_setup"
            ),
            discord.SelectOption(
                label="ℹ️ General Info",
                description="General information commands",
                value="info"
            )
        ]
        super().__init__(placeholder="Select a command category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = self.view.get_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpDropdown())

    def get_embed(self, category: str) -> discord.Embed:
        categories = {
            "basic": {
                "title": "🎮 Basic Campaign Commands",
                "content": """/signup - Sign up for an election
/withdraw - Withdraw from an election
/speech - Hold a speech to earn % points (1200 characters = 1%)
/canvassing - Go door-to-door canvassing (0.1% points, 1 stamina)
/donor - Accept donor funds (1000 characters = 1% points, 5 corruption)
/ad - Submit a campaign video ad (0.3-0.5% points, 1.5 stamina)
/poster - Submit a campaign poster image (0.2-0.4% points, 1 stamina)
/endorse - Endorse another candidate (gives them points, no cost to you)"""
            },
            "presidential": {
                "title": "🏛️ Presidential Commands",
                "content": """/pres_signup - Sign up for President with detailed platform information
/pres_canvassing - Presidential canvassing in a U.S. state (0.1% points, 1 stamina)
/pres_donor - Presidential donor meeting in a U.S. state (1000 characters = 1% points, 5 corruption)
/pres_ad - Presidential campaign video ad in a U.S. state (0.3-0.5% points, 1.5 stamina)
/pres_poster - Presidential campaign poster in a U.S. state (0.2-0.4% points, 1 stamina)
/pres_polling - Show presidential polling data for a specific U.S. state
/pres_primary - Show current/upcoming primaries for a party"""
            },
            "pac": {
                "title": "🏛️ PAC Commands",
                "content": """/pac - Start PAC endorsement process for a candidate
/speech_pac - Give a speech to a PAC for endorsement points
/view_pac_progress - View PAC endorsement progress for all candidates
/view_pacs - View all available PACs and their operating states"""
            },
            "polling": {
                "title": "📊 Polling Commands",
                "content": """/regionpoll - Simulate a regional poll for Senate or Governor races
/housepoll - Simulate a poll for House races in a U.S. state
/region_poll - Show polling results for a specific region
/poll_comparison - Compare polling between multiple regions or states
/list_signups - List all candidates by phase, race, and party
/show_primarywinners - Display all candidates who have won a primary election"""
            },
            "time": {
                "title": "⏰ Time & Phase Commands",
                "content": """/current_time - Show the current RP date and election phase
/show_phases - Show all election phases and their timing
/show_regions - Show all available election regions
/time - Display the current game time (year, month, cycle, and phase)
/current_date - Display the current RP date
/current_phase - Display the current election phase with detailed schedule"""
            },
            "seats": {
                "title": "🏛️ Election Seat Management",
                "content": """/show_seats - Show all election seats by state or office type
/seats_up_for_election - Show all seats that are up for election this cycle
/assign_seat - Assign a user to an election seat
/vacant_seat - Mark a seat as vacant (remove current holder)
/toggle_seat_election - Toggle whether a seat is up for election
/bulk_assign_election - Mark all seats of a specific type or state as up for election
/election_stats - Show statistics about current elections and seats
/show_seat_terms - Show term end years for all seats or filter by state/office
/list_states - List all states/regions and their seat counts"""
            },
            "admin_election": {
                "title": "🔧 Admin - Election Management",
                "content": """/tally_primarywinners - Tally up points and determine primary winners
/tally_generalwinners - Tally general election winners based on Points + Votes
/transfer_winners - Transfer declared winners to All Winners sheet
/pres_delegate_tally - Process delegate allocation for a primary state
/pres_delegate - Complete presidential primary: winners, transfer, ideology"""
            },
            "admin_time": {
                "title": "🔧 Admin - Time & Cycle Management",
                "content": """/set_current_time - Set the current RP date and time
/set_time_scale - Set how many real minutes equal one RP day
/reset_cycle - Reset the election cycle to the beginning (Signups phase)
/set_voice_channel - Set which voice channel to update with RP date
/toggle_voice_updates - Toggle automatic voice channel name updates
/update_voice_channel - Manually update the configured voice channel with current RP date
/pause - Pause or resume the cycle timer
/change_date - Change the current year, cycle, or month
/set_date - Set the current RP date manually
/time_ticker - Manually advance time by one month
/cycle - Advance the election cycle (1→2, 2→3, 3→1)
/reversecycle - Reverse the election cycle (1→3, 2→1, 3→2)"""
            },
            "admin_seats": {
                "title": "🔧 Admin - Seat & State Management",
                "content": """/add_state - Add a new state/region with configurable seats
/add_districts - Add additional house districts to an existing state
/add_senate_seats - Add additional senate seats to an existing state
/remove_seat - Remove a specific seat from the election system
/remove_state - Remove an entire state/region and all its seats
/modify_seat_term - Modify the term length for a specific seat type
/set_seat_term_year - Set a specific term end year for a seat
/bulk_set_term_years - Bulk set term end years for multiple seats
/shift_all_term_years_negative - Shift all seat term end years by subtracting years
/advance_all_terms - Manually advance all seat terms that were up for election"""
            },
            "admin_setup": {
                "title": "🔧 Admin - Setup & Configuration",
                "content": """/setup_announcement_channel - Set the channel for election announcements
/show_config - Show current election configuration"""
            },
            "info": {
                "title": "ℹ️ General Info",
                "content": """/commands - Show this help menu
/credits - Lists the people that made this bot"""
            }
        }

        cat_data = categories.get(category, categories["basic"])
        embed = discord.Embed(
            title=cat_data["title"],
            description=cat_data["content"],
            color=discord.Colour.blurple()
        )
        embed.set_footer(text="Use the dropdown below to navigate between categories")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class Basics(commands.Cog):  # Capitalized as per style
    def __init__(self, bot):
        self.bot = bot
        print("Basics cog loaded successfully.")

    @discord.app_commands.command(name="commands", description="Lists all the commands in the bot") #commands command
    async def help_command(self, interaction: discord.Interaction):
        view = HelpView()
        embed = view.get_embed("basic")
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="credits", description="Lists the people that made this bot")
    async def credits_command(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title='To the people who made me possible:',
            description="""
            Mallard - original creator
            Sixteen - 16bysixteen - maintainer
            Yuri - deftvessel2.0 - maintainer
            """,
            color=discord.Colour.blurple()
        )

        await interaction.response.send_message(embed=embed)

    # Create admin command group
    admin_group = app_commands.Group(name="admin", description="Admin-only commands")

    @admin_group.command(
        name="reset_campaign_cooldowns",
        description="Reset general campaign action cooldowns for a user (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_campaign_cooldowns(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        collection_name: str = "action_cooldowns"
    ):
        target_user = user if user else interaction.user

        # Common cooldown collection names that might exist
        possible_collections = [
            "action_cooldowns",
            "campaign_cooldowns",
            "general_action_cooldowns",
            "election_cooldowns"
        ]

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

async def setup(bot):
    await bot.add_cog(Basics(bot))