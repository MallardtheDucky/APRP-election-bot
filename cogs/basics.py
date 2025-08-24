from discord.ext import commands
import discord
from discord import app_commands

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="🎮 Basic Commands",
                description="Core bot commands",
                value="basic"
            ),
            discord.SelectOption(
                label="🏛️ Setup Commands", 
                description="Guild setup and configuration",
                value="setup"
            ),
            discord.SelectOption(
                label="🎉 Party Management",
                description="Political party commands",
                value="party"
            ),
            discord.SelectOption(
                label="📊 Polling Commands",
                description="Polling and survey commands", 
                value="polling"
            ),
            discord.SelectOption(
                label="🗳️ Election Management",
                description="Election seats and management",
                value="election"
            ),
            discord.SelectOption(
                label="⏰ Time Management",
                description="Election timing and phases",
                value="time"
            ),
            discord.SelectOption(
                label="📋 Election Signups",
                description="Candidate signup commands",
                value="signups"
            ),
            discord.SelectOption(
                label="🏛️ Presidential Elections",
                description="Presidential campaign commands",
                value="presidential"
            ),
            discord.SelectOption(
                label="🤝 Endorsements & Delegates",
                description="Endorsement and delegate commands",
                value="endorsements"
            ),
            discord.SelectOption(
                label="🗳️ Voting & Results",
                description="Voting and election results",
                value="voting"
            ),
            discord.SelectOption(
                label="🎯 Campaign Actions",
                description="Campaign and outreach actions",
                value="campaign"
            ),
            discord.SelectOption(
                label="🌊 Momentum & Demographics",
                description="Momentum and demographic commands",
                value="momentum"
            ),
            discord.SelectOption(
                label="🔧 Admin Commands",
                description="Administrator-only commands",
                value="admin"
            ),
            discord.SelectOption(
                label="📚 Handbook",
                description="Strategy guides and how-to tutorials",
                value="handbook"
            )
        ]
        super().__init__(placeholder="Select a command category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = self.view.get_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)

class HandbookDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📖 Getting Started", description="Initial setup and basic concepts", value="getting_started"),
            discord.SelectOption(label="🗳️ Election Management", description="Managing elections and phases", value="election_management"),
            discord.SelectOption(label="🎯 Campaign Strategies", description="Basic campaign tactics", value="campaign_strategies"),
            discord.SelectOption(label="👥 Demographics & Targeting", description="Voter demographic strategies", value="demographics"),
            discord.SelectOption(label="🌊 Momentum System", description="Understanding momentum mechanics", value="momentum"),
            discord.SelectOption(label="🏛️ Presidential Campaigns", description="Presidential election strategies", value="presidential"),
            discord.SelectOption(label="🎉 Party Management", description="Political party administration", value="party_management"),
            discord.SelectOption(label="🎓 Advanced Strategies", description="Complex campaign techniques", value="advanced"),
            discord.SelectOption(label="🔧 Admin Tools", description="Administrative commands guide", value="admin_tools"),
            discord.SelectOption(label="🛠️ Troubleshooting", description="Common issues and solutions", value="troubleshooting")
        ]
        super().__init__(placeholder="Select a handbook section...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = self.view.get_handbook_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)

class HandbookView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HandbookDropdown())

    def get_handbook_embed(self, section: str) -> discord.Embed:
        handbook_sections = {
            "getting_started": {
                "title": "📖 Getting Started",
                "content": """**Initial Setup:**
• `/setup add_region` - Add US states to your server
• `/setup set_start` - Set election start date
• `/setup set_announcement_channel` - Set update channel
• `/party admin create` - Create custom parties
• `/election admin set_seats` - Configure election seats

**Election Phases:**
• **Signup Phase** - Candidates register
• **Primary Campaign** - Campaign for party nominations
• **Primary Voting** - Vote in party primaries
• **General Campaign** - Campaign for general election
• **General Voting** - Final election voting
• **Governance** - Winners serve terms

**Key Commands:**
• `/time current_time` - Check current phase
• `/signup` - Register as candidate
• `/commands` - View all commands"""
            },
            "election_management": {
                "title": "🗳️ Election Management",
                "content": """**Setting Up Elections:**
1. Configure seats with `/election admin set_seats`
2. Set timing with `/time` commands
3. Configure parties and colors
4. Set announcement channels

**Candidate Registration:**
• `/signup` - General election signup
• `/pres_signup` - Presidential campaigns
• `/vp_signup` - Vice President signup
• `/withdraw_signup` - Withdraw from race

**Managing Process:**
• Elections progress automatically through phases
• Admins can manually set vote counts if needed
• Results announced automatically
• Use `/time set_time_scale` to control pacing"""
            },
            "campaign_strategies": {
                "title": "🎯 Campaign Strategies",
                "content": """**Basic Campaign Actions:**
• **Speeches** (`/speech`) - Build general support
• **Canvassing** (`/canvassing`) - Target specific regions
• **Ads** (`/ad`) - Wide reach, costs more stamina
• **Posters** (`/poster`) - Cheap name recognition
• **Donor Appeals** (`/donor`) - Fundraising

**Effectiveness Tips:**
• Actions have cooldowns to prevent spam
• Different actions work better in different states
• Consider your party's base when choosing regions

**Resource Management:**
• All actions cost stamina
• Plan campaign timeline carefully
• Don't exhaust stamina early in long campaigns"""
            },
            "demographics": {
                "title": "👥 Demographics & Targeting",
                "content": """**20+ Demographic Groups:**
• Urban vs Rural voters
• Age groups (Young 18-29, Seniors 65+)
• Ethnic groups (African American, Latino, Asian, etc.)
• Economic groups (Wealthy, Low-Income, Blue-Collar)
• Ideological groups (Evangelical, LGBTQ+, Environmental)

**State Multipliers:**
• **Strong (1.75x)** - Very influential in state
• **Moderate (0.75x)** - Average influence
• **Small (0.3x)** - Limited influence

**Strategy:**
1. Research state demographic strengths first
2. Use `/demographic_appeal` in favorable states
3. Avoid over-appealing (125%+ triggers backlash)
4. Balance different demographic appeals"""
            },
            "momentum": {
                "title": "🌊 Momentum System",
                "content": """**Understanding Momentum:**
• Parties gain momentum through successful campaigns
• High momentum makes future actions more effective
• Low momentum can lead to "collapse" penalties

**Building Momentum:**
• Consistent campaigning in states
• Successful demographic appeals
• Endorsements from local figures

**Momentum Collapse:**
• Triggered when party becomes vulnerable
• Use `/momentum trigger_collapse` on opponents
• Results in major momentum loss and penalties

**Strategy:**
• Don't neglect states - momentum decays
• Protect strong states from collapse attempts
• Target opponent's vulnerable states"""
            },
            "presidential": {
                "title": "🏛️ Presidential Campaigns",
                "content": """**Presidential Primaries:**
• Sign up with `/pres_signup`
• Choose running mates with `/vp_signup` and `/accept_vp`
• Compete for delegates through state campaigns
• Early primary states matter more

**Special Presidential Actions:**
• `/pres_speech` - Enhanced speeches with broader reach
• `/pres_canvassing` - State-targeted canvassing
• `/pres_ad` - Expensive but very effective
• `/pres_poster` - Build national name recognition
• `/pres_donor` - Major fundraising appeals

**Electoral Strategy:**
• Focus on swing states during general election
• Don't neglect base states entirely
• Consider regional balance with VP pick"""
            },
            "party_management": {
                "title": "🎉 Party Management",
                "content": """**Default Parties:**
• Democratic Party (Blue)
• Republican Party (Red)
• Independent (Purple)
• Green Party (Green)
• Libertarian Party (Yellow)

**Custom Parties:**
• Admins can create with `/party admin create`
• Set colors, abbreviations, descriptions
• Useful for role-playing scenarios

**Party Strategy:**
• Each party has traditional strongholds
• Consider party when choosing regions
• Some demographics align better with certain parties

**Management Commands:**
• `/party info list` - View all parties
• `/party admin edit` - Modify existing parties
• `/party admin remove` - Delete parties"""
            },
            "advanced": {
                "title": "🎓 Advanced Strategies",
                "content": """**Coalition Building:**
1. Identify 3-4 core demographic groups
2. Avoid targeting opposing groups
3. Focus on regions where demos are strong
4. Space out appeals to avoid backlash

**Regional Specialization:**
• Focus heavily on 2-3 states you can dominate
• Maintain presence in swing states
• Don't waste resources on opponent strongholds

**Opponent Disruption:**
• Monitor opponent momentum for collapse opportunities
• Time attacks when opponents are vulnerable
• Use endorsements strategically

**Late Campaign Surges:**
• Save stamina for final pushes
• Target undecided voters in swing regions
• Use high-impact actions like ads in final phases"""
            },
            "admin_tools": {
                "title": "🔧 Admin Tools",
                "content": """**Essential Admin Commands:**
• `/election admin set_seats` - Configure elections
• `/time set_current_time` - Control timing
• `/momentum admin add_momentum` - Adjust momentum
• `/party admin create` - Create custom parties
• `/poll admin bulk_set_votes` - Set voting results

**Managing Elections:**
• Monitor campaign activity for violations
• Adjust time scales for appropriate pacing
• Use polling commands for realistic scenarios
• Manually resolve disputes if needed

**Balancing Gameplay:**
• Ensure no single strategy is overpowered
• Monitor momentum system for fairness
• Adjust demographic thresholds if needed
• Create interesting scenarios with admin tools"""
            },
            "troubleshooting": {
                "title": "🛠️ Troubleshooting",
                "content": """**Common Issues:**
• **"Command on cooldown"** - Wait for cooldown to expire
• **"Not in correct phase"** - Check current election phase
• **"Insufficient permissions"** - Admin commands need admin role
• **"Region not found"** - Use correct state abbreviations

**Campaign Problems:**
• **Low effectiveness** - Check regions for your demographics
• **Momentum not building** - Increase campaign frequency
• **Demographic backlash** - Reduce appeals to conflicting groups

**Best Practices:**
• Plan campaign strategy before starting
• Monitor cooldowns and manage stamina
• Study demographic conflicts before appeals
• Keep track of momentum in key states
• Coordinate with running mates and endorsers"""
            }
        }

        section_data = handbook_sections.get(section, handbook_sections["getting_started"])
        embed = discord.Embed(
            title=section_data["title"],
            description=section_data["content"],
            color=discord.Colour.green()
        )
        embed.set_footer(text="Use the dropdown below to navigate between handbook sections")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpDropdown())

    def get_embed(self, category: str) -> discord.Embed:
        categories = {
            "basic": {
                "title": "🎮 Basic Commands",
                "content": """/commands - Show this help menu with pagination
/credits - Lists the people that made this bot"""
            },
            "setup": {
                "title": "🏛️ Setup Commands", 
                "content": """/setup add_region - Add a US state (by abbreviation) to this guild's election regions
/setup remove_region - Remove a US state from this guild's regions
/setup show_config - Show current election configuration
/setup list_regions - List all the US states you've added as regions
/setup set_start - Set the start date & time for your election (format: YYYY-MM-DD HH:MM)
/setup set_announcement_channel - Set the channel for election announcements
/setup remove_announcement_channel - Remove the announcement channel setting"""
            },
            "party": {
                "title": "🎉 Party Management Commands",
                "content": """/party admin create - Create a new political party (Admin only)
/party admin remove - Remove a political party (Admin only)
/party admin edit - Edit an existing political party (Admin only)
/party admin reset - Reset all parties to default (Admin only - DESTRUCTIVE)
/party admin bulk_create - Create multiple parties at once (Admin only)
/party admin remove_all_custom - Remove all custom parties (keep defaults) (Admin only)
/party admin export - Export party configuration as text (Admin only)
/party admin modify_color - Change the color of multiple parties at once (Admin only)
/party info list - List all available political parties"""
            },
            "polling": {
                "title": "📊 Polling Commands",
                "content": """/poll candidate - Conduct an NPC poll for a specific candidate (shows polling with 7% margin of error)
/poll info state - Conduct an NPC poll for all parties in a specific state, showing Rep/Dem/Independent support
/poll admin bulk_set_votes - Set vote counts for multiple candidates (Admin only)
/poll admin set_winner_votes - Set election winner and vote counts for general elections (Admin only)
/poll vote admin_bulk_set_votes - Set vote counts for multiple candidates (Admin only)
/poll vote admin_set_winner_votes - Set election winner and vote counts for general elections (Admin only)"""
            },
            "election": {
                "title": "🗳️ Election Management",
                "content": """/election admin set_seats - Set up election seats for the guild (Admin only)
/election admin reset_seats - Reset all election seats (Admin only)
/election admin view_seats - View all configured election seats (Admin only)
/election admin bulk_add_seats - Add multiple seats from formatted text (Admin only)
/election admin fill_vacant_seat - Fill a vacant seat with a user (Admin only)
/election seat view - View details of a specific election seat
/election seat list - List all election seats
/election seat assign - Assign a user to an election seat
/election seat admin_update - Update a specific election seat (Admin only)
/election seat admin_reset_term - Reset term for a specific seat (Admin only)
/election info phases - Show current election phase information
/election info winners - View election winners"""
            },
            "time": {
                "title": "⏰ Time Management",
                "content": """/time current_time - Show the current RP date and election phase
/time set_current_time - Set the current RP date and time (Admin only)
/time set_time_scale - Set how many real minutes equal one RP day (Admin only)
/time reset_cycle - Reset the election cycle to the beginning (Admin only)
/time set_voice_channel - Set which voice channel to update with RP date (Admin only)
/time toggle_voice_updates - Toggle automatic voice channel name updates (Admin only)
/time update_voice_channel - Manually update the configured voice channel with current RP date (Admin only)"""
            },
            "signups": {
                "title": "📋 Election Signups",
                "content": """/signup - Sign up as a candidate for election (only during signup phase)
/view_signups - View all current candidate signups
/withdraw_signup - Withdraw your candidacy from the current election
/my_signup - View your current signup details"""
            },
            "presidential": {
                "title": "🏛️ Presidential Elections",
                "content": """/pres_signup - Sign up to run for President
/vp_signup - Sign up to run for Vice President under a specific presidential candidate
/accept_vp - Accept a VP candidate for your presidential campaign
/decline_vp - Decline a VP candidate request
/view_pres_signups - View all current presidential signups
/my_pres_signup - View your current presidential signup details"""
            },
            "endorsements": {
                "title": "🤝 Endorsements & Delegates",
                "content": """/endorse - Endorse a candidate (value based on your Discord role)
/admin_set_endorsement_role - Set Discord role for endorsement position (Admin only)
/view_endorsement_roles - View current endorsement role mappings (Admin only)
/view_endorsements - View all endorsements made in current cycle
/my_endorsement - View your current endorsement status
/view_delegates - View current delegate count for presidential candidates
/admin_call_state - Manually call a state for delegate allocation (Admin only)"""
            },
            "voting": {
                "title": "🗳️ Voting & Results",
                "content": """/vote admin_bulk_set_votes - Set vote counts for multiple candidates (Admin only)
/vote admin_set_winner_votes - Set election winner and vote counts for general elections (Admin only)
/view_primary_winners - View all primary election winners for the current year
/admin_set_winner_votes - Set votes for a primary winner (Admin only)
/admin_declare_general_winners - Declare general election winners based on final scores (Admin only)"""
            },
            "campaign": {
                "title": "🎯 Campaign Actions",
                "content": """/pres_speech - Give a presidential campaign speech
/pres_donor - Make a presidential donor appeal
/pres_canvassing - Conduct presidential canvassing in a state
/pres_ad - Run a presidential campaign ad
/pres_poster - Put up presidential campaign posters

/speech - Give a campaign speech for any candidate
/donor - Make a donor fundraising appeal
/canvassing - Conduct door-to-door canvassing in a region
/ad - Run a campaign advertisement
/poster - Put up campaign posters

/demographic_appeal - Target specific demographic groups with campaign appeals
/voter_registration - Conduct voter registration drives
/town_hall - Host town hall meetings
/grassroots - Organize grassroots campaign events"""
            },
            "momentum": {
                "title": "🌊 Momentum & State Dynamics",
                "content": """/momentum status - View momentum status for a specific state
/momentum overview - View momentum overview for all states
/momentum trigger_collapse - Attempt to trigger momentum collapse for a vulnerable party
/momentum admin add_momentum - Add momentum to a party in a state (Admin only)
/momentum admin set_lean - Set or change a state's political lean (Admin only)
/momentum admin settings - View or modify momentum system settings (Admin only)

/show_regions - Show all available election regions
/show_phases - Show all election phases and their timing
/admin_view_pres_state_data - View PRESIDENTIAL_STATE_DATA as a formatted table (Admin only)
/show_primary_winners - Show current presidential primary winners
/admin_update_winner - Manually update a primary winner (Admin only)
/admin_reset_winners - Reset all primary winners (Admin only)
/admin_view_state_percentages - View state-by-state voting percentages for general election (Admin only)"""
            },
            "admin": {
                "title": "🔧 Admin Commands",
                "content": """/admin reset_campaign_cooldowns - Reset general campaign action cooldowns for a user (Admin only)

All admin commands from other categories are also available with admin permissions."""
            },
            "handbook": {
                "title": "📚 Election Bot Handbook",
                "content": """/handbook - Access the comprehensive election bot handbook with strategies and guides

The handbook includes detailed guides on:
• Getting started with elections
• Campaign strategies and tactics
• Demographics and voter targeting
• Momentum system mechanics
• Presidential campaign management
• Party management and customization
• Advanced strategic techniques
• Administrative tools and commands
• Troubleshooting common issues

Use the handbook dropdown to navigate between different strategy guides and tutorials."""
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

    @discord.app_commands.command(name="handbook", description="Access the comprehensive election bot handbook")
    async def handbook_command(self, interaction: discord.Interaction):
        view = HandbookView()
        embed = view.get_handbook_embed("getting_started")
        await interaction.response.send_message(embed=embed, view=view)

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