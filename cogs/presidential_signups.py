import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional
from .ideology import STATE_DATA

class PresidentialSignups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Presidential Signups cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration for a guild"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_config(self, guild_id: int):
        """Get or create presidential signups configuration for a guild"""
        col = self.bot.db["presidential_signups"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "candidates": [],  # Presidential and VP candidates
                "pending_vp_requests": []  # VP requests pending acceptance
            }
            col.insert_one(config)
        return col, config

    def _get_available_choices(self):
        """Get all available ideology choices from STATE_DATA"""
        ideologies = set()
        economics = set()
        socials = set()
        governments = set()
        axes = set()

        for state_data in STATE_DATA.values():
            if "ideology" in state_data:
                ideologies.add(state_data["ideology"])
            if "economic" in state_data:
                economics.add(state_data["economic"])
            if "social" in state_data:
                socials.add(state_data["social"])
            if "government" in state_data:
                governments.add(state_data["government"])
            if "axis" in state_data:
                axes.add(state_data["axis"])

        return {
            "ideology": sorted(list(ideologies)),
            "economic": sorted(list(economics)),
            "social": sorted(list(socials)),
            "government": sorted(list(governments)),
            "axis": sorted(list(axes))
        }

    @app_commands.command(
        name="pres_signup",
        description="Sign up to run for President"
    )
    @app_commands.describe(
        name="Your candidate's name",
        party="Your political party",
        ideology="Your ideological position",
        economic="Your economic position", 
        social="Your social position",
        government="Your government size preference",
        axis="Your political axis"
    )
    async def pres_signup(
        self,
        interaction: discord.Interaction,
        name: str,
        party: str,
        ideology: str,
        economic: str,
        social: str,
        government: str,
        axis: str
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")

        # Check if we're in a presidential election cycle (every 4 years)
        # Presidential cycles: 1999-2000, 2003-2004, 2007-2008, etc.
        # The cycle starts in odd years (1999, 2003, 2007) and elections happen in even years (2000, 2004, 2008)
        if current_year % 4 == 3:  # 1999, 2003, 2007, 2011, 2015 (signup years)
            is_presidential_cycle = True
        elif current_year % 4 == 0:  # 2000, 2004, 2008, 2012, 2016 (election years)
            is_presidential_cycle = True
        else:  # 2001, 2002, 2005, 2006 (midterm years)
            is_presidential_cycle = False

        if not is_presidential_cycle:
            next_presidential_signup = ((current_year // 4) + 1) * 4 - 1  # Next cycle start year
            await interaction.response.send_message(
                f"❌ Presidential signups are only available during presidential election cycles.\n"
                f"The next presidential cycle begins in **{next_presidential_signup}**.\n"
                f"Current year **{current_year}** is a midterm year.",
                ephemeral=True
            )
            return

        if current_phase not in ["Signups", "Primary Campaign"]:
            await interaction.response.send_message(
                f"❌ Presidential signups are not open during the {current_phase} phase.",
                ephemeral=True
            )
            return

        # Validate ideology choices
        available_choices = self._get_available_choices()

        if ideology not in available_choices["ideology"]:
            await interaction.response.send_message(
                f"❌ Invalid ideology. Available options: {', '.join(available_choices['ideology'])}",
                ephemeral=True
            )
            return

        if economic not in available_choices["economic"]:
            await interaction.response.send_message(
                f"❌ Invalid economic type. Available options: {', '.join(available_choices['economic'])}",
                ephemeral=True
            )
            return

        if social not in available_choices["social"]:
            await interaction.response.send_message(
                f"❌ Invalid social type. Available options: {', '.join(available_choices['social'])}",
                ephemeral=True
            )
            return

        if government not in available_choices["government"]:
            await interaction.response.send_message(
                f"❌ Invalid government type. Available options: {', '.join(available_choices['government'])}",
                ephemeral=True
            )
            return

        if axis not in available_choices["axis"]:
            await interaction.response.send_message(
                f"❌ Invalid axis type. Available options: {', '.join(available_choices['axis'])}",
                ephemeral=True
            )
            return

        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Check if user already has a presidential signup
        existing_signup = None
        for candidate in pres_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year and
                candidate["office"] == "President"):
                existing_signup = candidate
                break

        if existing_signup:
            await interaction.response.send_message(
                f"❌ You are already signed up as **{existing_signup['name']}** ({existing_signup['party']}) for President in {current_year}.",
                ephemeral=True
            )
            return

        # Create presidential candidate entry
        new_candidate = {
            "user_id": interaction.user.id,
            "name": name,
            "party": party,
            "office": "President",
            "seat_id": "US-PRES",
            "region": "National",
            "year": current_year,
            "ideology": ideology,
            "economic": economic,
            "social": social,
            "government": government,
            "axis": axis,
            "vp_candidate": None,  # Will be set when VP is chosen
            "vp_candidate_id": None,
            "signup_date": datetime.utcnow(),
            "points": 0.0,
            "stamina": 200,
            "corruption": 0,
            "phase": "Primary Campaign" if current_phase in ["Primary Campaign", "Primary Election"] else "Primary Campaign"
        }

        pres_config["candidates"].append(new_candidate)

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"candidates": pres_config["candidates"]}}
        )

        embed = discord.Embed(
            title="🇺🇸 Presidential Campaign Launched!",
            description=f"**{name}** has officially entered the race for President!",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 Candidate Details",
            value=f"**Name:** {name}\n"
                  f"**Party:** {party}\n"
                  f"**Office:** President of the United States",
            inline=True
        )

        embed.add_field(
            name="🎯 Political Profile",
            value=f"**Ideology:** {ideology}\n"
                  f"**Economic:** {economic}\n"
                  f"**Social:** {social}\n"
                  f"**Government:** {government}\n"
                  f"**Axis:** {axis}",
            inline=True
        )

        embed.add_field(
            name="📊 Starting Stats",
            value=f"**Points:** {new_candidate['points']:.2f}\n"
                  f"**Stamina:** {new_candidate['stamina']}\n"
                  f"**Corruption:** {new_candidate['corruption']}",
            inline=True
        )

        embed.add_field(
            name="📅 Campaign Info",
            value=f"**Year:** {current_year}\n"
                  f"**Phase:** {current_phase}\n"
                  f"**VP Candidate:** Not selected",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="vp_signup",
        description="Sign up to run for Vice President under a specific presidential candidate"
    )
    @app_commands.describe(
        name="Your candidate's name",
        party="Your political party",
        ideology="Your ideological position",
        economic="Your economic position", 
        social="Your social position",
        government="Your government size preference",
        axis="Your political axis",
        presidential_candidate="Name of the presidential candidate you want to run with"
    )
    async def vp_signup(
        self,
        interaction: discord.Interaction,
        name: str,
        party: str,
        ideology: str,
        economic: str,
        social: str,
        government: str,
        axis: str,
        presidential_candidate: str
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")

        # Check if we're in a presidential election cycle (every 4 years)
        if current_year % 4 == 3:  # 1999, 2003, 2007, 2011, 2015 (signup years)
            is_presidential_cycle = True
        elif current_year % 4 == 0:  # 2000, 2004, 2008, 2012, 2016 (election years)
            is_presidential_cycle = True
        else:  # 2001, 2002, 2005, 2006 (midterm years)
            is_presidential_cycle = False

        if not is_presidential_cycle:
            next_presidential_signup = ((current_year // 4) + 1) * 4 - 1  # Next cycle start year
            await interaction.response.send_message(
                f"❌ VP signups are only available during presidential election cycles.\n"
                f"The next presidential cycle begins in **{next_presidential_signup}**.\n"
                f"Current year **{current_year}** is a midterm year.",
                ephemeral=True
            )
            return

        if current_phase not in ["Signups", "Primary Campaign"]:
            await interaction.response.send_message(
                f"❌ VP signups are not open during the {current_phase} phase.",
                ephemeral=True
            )
            return

        # Validate ideology choices
        available_choices = self._get_available_choices()

        ideology_errors = []
        if ideology not in available_choices["ideology"]:
            ideology_errors.append(f"Invalid ideology. Available: {', '.join(available_choices['ideology'])}")
        if economic not in available_choices["economic"]:
            ideology_errors.append(f"Invalid economic. Available: {', '.join(available_choices['economic'])}")
        if social not in available_choices["social"]:
            ideology_errors.append(f"Invalid social. Available: {', '.join(available_choices['social'])}")
        if government not in available_choices["government"]:
            ideology_errors.append(f"Invalid government. Available: {', '.join(available_choices['government'])}")
        if axis not in available_choices["axis"]:
            ideology_errors.append(f"Invalid axis. Available: {', '.join(available_choices['axis'])}")

        if ideology_errors:
            await interaction.response.send_message(
                f"❌ {'; '.join(ideology_errors)}",
                ephemeral=True
            )
            return

        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Find the presidential candidate
        presidential_candidate_data = None
        for candidate in pres_config["candidates"]:
            if (candidate["name"].lower() == presidential_candidate.lower() and
                candidate["year"] == current_year and
                candidate["office"] == "President"):
                presidential_candidate_data = candidate
                break

        if not presidential_candidate_data:
            available_presidents = [c["name"] for c in pres_config["candidates"] 
                                  if c["year"] == current_year and c["office"] == "President"]
            await interaction.response.send_message(
                f"❌ Presidential candidate '{presidential_candidate}' not found.\n"
                f"Available candidates: {', '.join(available_presidents) if available_presidents else 'None'}",
                ephemeral=True
            )
            return

        # Check if user already has a VP signup
        existing_signup = None
        for candidate in pres_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year and
                candidate["office"] == "Vice President"):
                existing_signup = candidate
                break

        if existing_signup:
            await interaction.response.send_message(
                f"❌ You are already signed up as **{existing_signup['name']}** for Vice President in {current_year}.",
                ephemeral=True
            )
            return

        # Check if this presidential candidate already has a VP
        if presidential_candidate_data.get("vp_candidate"):
            await interaction.response.send_message(
                f"❌ {presidential_candidate} already has a VP candidate: {presidential_candidate_data['vp_candidate']}",
                ephemeral=True
            )
            return

        # Create VP request entry
        vp_request = {
            "user_id": interaction.user.id,
            "name": name,
            "party": party,
            "office": "Vice President",
            "seat_id": "US-VP",
            "region": "National",
            "year": current_year,
            "ideology": ideology,
            "economic": economic,
            "social": social,
            "government": government,
            "axis": axis,
            "presidential_candidate": presidential_candidate,
            "presidential_candidate_id": presidential_candidate_data["user_id"],
            "request_date": datetime.utcnow(),
            "status": "pending"
        }

        if "pending_vp_requests" not in pres_config:
            pres_config["pending_vp_requests"] = []

        pres_config["pending_vp_requests"].append(vp_request)

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"pending_vp_requests": pres_config["pending_vp_requests"]}}
        )

        # Notify the presidential candidate
        guild = interaction.guild
        president_user = guild.get_member(presidential_candidate_data["user_id"])

        if president_user:
            try:
                embed = discord.Embed(
                    title="🤝 Vice Presidential Request",
                    description=f"**{name}** wants to be your running mate!",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="👤 VP Candidate",
                    value=f"**Name:** {name}\n**Party:** {party}",
                    inline=True
                )

                embed.add_field(
                    name="🎯 Political Profile",
                    value=f"**Ideology:** {ideology}\n"
                          f"**Economic:** {economic}\n"
                          f"**Social:** {social}\n"
                          f"**Government:** {government}\n"
                          f"**Axis:** {axis}",
                    inline=True
                )

                embed.add_field(
                    name="📋 Next Steps",
                    value="Use `/accept_vp` or `/decline_vp` to respond to this request.",
                    inline=False
                )

                await president_user.send(embed=embed)
            except discord.Forbidden:
                pass  # Couldn't DM the user

        await interaction.response.send_message(
            f"🤝 VP request sent to **{presidential_candidate}**! They will need to accept you as their running mate using `/accept_vp`.",
            ephemeral=True
        )

    @app_commands.command(
        name="accept_vp",
        description="Accept a VP candidate for your presidential campaign"
    )
    async def accept_vp(self, interaction: discord.Interaction, vp_candidate_name: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Find user's presidential campaign
        user_pres_campaign = None
        for candidate in pres_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year and
                candidate["office"] == "President"):
                user_pres_campaign = candidate
                break

        if not user_pres_campaign:
            await interaction.response.send_message(
                "❌ You don't have an active presidential campaign.",
                ephemeral=True
            )
            return

        # Find the VP request
        vp_request = None
        for i, request in enumerate(pres_config.get("pending_vp_requests", [])):
            if (request["name"].lower() == vp_candidate_name.lower() and
                request["presidential_candidate_id"] == interaction.user.id and
                request["year"] == current_year and
                request["status"] == "pending"):
                vp_request = request
                request_index = i
                break

        if not vp_request:
            pending_requests = [r["name"] for r in pres_config.get("pending_vp_requests", [])
                              if r["presidential_candidate_id"] == interaction.user.id 
                              and r["status"] == "pending"]
            await interaction.response.send_message(
                f"❌ No pending VP request from '{vp_candidate_name}'.\n"
                f"Pending requests: {', '.join(pending_requests) if pending_requests else 'None'}",
                ephemeral=True
            )
            return

        # Create VP candidate entry
        vp_candidate = {
            "user_id": vp_request["user_id"],
            "name": vp_request["name"],
            "party": vp_request["party"],
            "office": "Vice President",
            "seat_id": "US-VP",
            "region": "National",
            "year": current_year,
            "ideology": vp_request["ideology"],
            "economic": vp_request["economic"],
            "social": vp_request["social"],
            "government": vp_request["government"],
            "axis": vp_request["axis"],
            "presidential_candidate": user_pres_campaign["name"],
            "presidential_candidate_id": interaction.user.id,
            "signup_date": datetime.utcnow(),
            "points": 0.0,
            "stamina": 200,
            "corruption": 0,
            "phase": "Primary Campaign"
        }

        # Add VP to candidates and update president's record
        pres_config["candidates"].append(vp_candidate)

        for i, candidate in enumerate(pres_config["candidates"]):
            if candidate["user_id"] == interaction.user.id and candidate["office"] == "President":
                pres_config["candidates"][i]["vp_candidate"] = vp_request["name"]
                pres_config["candidates"][i]["vp_candidate_id"] = vp_request["user_id"]
                break

        # Remove the request
        pres_config["pending_vp_requests"][request_index]["status"] = "accepted"

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "candidates": pres_config["candidates"],
                "pending_vp_requests": pres_config["pending_vp_requests"]
            }}
        )

        embed = discord.Embed(
            title="🤝 Ticket Formed!",
            description=f"The **{user_pres_campaign['name']}-{vp_request['name']}** ticket is now official!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🇺🇸 Presidential Candidate",
            value=f"**{user_pres_campaign['name']}** ({user_pres_campaign['party']})",
            inline=True
        )

        embed.add_field(
            name="🤝 Vice Presidential Candidate", 
            value=f"**{vp_request['name']}** ({vp_request['party']})",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="decline_vp",
        description="Decline a VP candidate for your presidential campaign"
    )
    async def decline_vp(self, interaction: discord.Interaction, vp_candidate_name: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Find the VP request
        vp_request = None
        for i, request in enumerate(pres_config.get("pending_vp_requests", [])):
            if (request["name"].lower() == vp_candidate_name.lower() and
                request["presidential_candidate_id"] == interaction.user.id and
                request["year"] == current_year and
                request["status"] == "pending"):
                vp_request = request
                request_index = i
                break

        if not vp_request:
            await interaction.response.send_message(
                f"❌ No pending VP request from '{vp_candidate_name}'.",
                ephemeral=True
            )
            return

        # Mark request as declined
        pres_config["pending_vp_requests"][request_index]["status"] = "declined"

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"pending_vp_requests": pres_config["pending_vp_requests"]}}
        )

        await interaction.response.send_message(
            f"❌ Declined VP request from **{vp_candidate_name}**.",
            ephemeral=True
        )

    @app_commands.command(
        name="pres_withdraw",
        description="Withdraw from your presidential or VP campaign"
    )
    async def pres_withdraw(self, interaction: discord.Interaction):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return

        current_year = time_config["current_rp_date"].year
        current_phase = time_config.get("current_phase", "")

        if current_phase not in ["Signups", "Primary Campaign"]:
            await interaction.response.send_message(
                f"❌ Withdrawals are not allowed during the {current_phase} phase.",
                ephemeral=True
            )
            return

        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Find user's campaign
        user_campaign = None
        campaign_index = None
        for i, candidate in enumerate(pres_config["candidates"]):
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year and
                candidate["office"] in ["President", "Vice President"]):
                user_campaign = candidate
                campaign_index = i
                break

        if not user_campaign:
            await interaction.response.send_message(
                "❌ You don't have an active presidential or VP campaign to withdraw from.",
                ephemeral=True
            )
            return

        # If withdrawing from presidential campaign, handle VP candidate
        if user_campaign["office"] == "President":
            vp_candidate_name = user_campaign.get("vp_candidate")
            vp_candidate_id = user_campaign.get("vp_candidate_id")

            # Remove VP candidate if exists
            if vp_candidate_id:
                vp_removed = False
                for i, candidate in enumerate(pres_config["candidates"]):
                    if (candidate["user_id"] == vp_candidate_id and
                        candidate["year"] == current_year and
                        candidate["office"] == "Vice President"):
                        pres_config["candidates"].pop(i)
                        vp_removed = True
                        break

        # If withdrawing from VP campaign, update presidential candidate
        elif user_campaign["office"] == "Vice President":
            presidential_candidate_id = user_campaign.get("presidential_candidate_id")
            if presidential_candidate_id:
                for i, candidate in enumerate(pres_config["candidates"]):
                    if (candidate["user_id"] == presidential_candidate_id and
                        candidate["year"] == current_year and
                        candidate["office"] == "President"):
                        pres_config["candidates"][i]["vp_candidate"] = None
                        pres_config["candidates"][i]["vp_candidate_id"] = None
                        break

        # Remove the candidate
        withdrawn_candidate = pres_config["candidates"].pop(campaign_index)

        # Also remove any pending VP requests for this user
        if "pending_vp_requests" not in pres_config:
            pres_config["pending_vp_requests"] = []

        pres_config["pending_vp_requests"] = [
            req for req in pres_config["pending_vp_requests"] 
            if not (req["user_id"] == interaction.user.id or req["presidential_candidate_id"] == interaction.user.id)
        ]

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "candidates": pres_config["candidates"],
                "pending_vp_requests": pres_config["pending_vp_requests"]
            }}
        )

        embed = discord.Embed(
            title="🚪 Campaign Withdrawal",
            description=f"**{withdrawn_candidate['name']}** has withdrawn from the {current_year} {withdrawn_candidate['office']}ial race.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📋 Withdrawn Candidate",
            value=f"**Name:** {withdrawn_candidate['name']}\n"
                  f"**Party:** {withdrawn_candidate['party']}\n"
                  f"**Office:** {withdrawn_candidate['office']}",
            inline=True
        )

        if withdrawn_candidate["office"] == "President" and withdrawn_candidate.get("vp_candidate"):
            embed.add_field(
                name="⚠️ Impact",
                value=f"VP candidate **{withdrawn_candidate['vp_candidate']}** has also been removed from the ticket.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="show_presidential_candidates",
        description="Show all presidential and VP candidates"
    )
    async def show_presidential_candidates(
        self,
        interaction: discord.Interaction,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Get candidates for target year
        candidates = [c for c in pres_config["candidates"] if c["year"] == target_year]

        presidents = [c for c in candidates if c["office"] == "President"]
        vps = [c for c in candidates if c["office"] == "Vice President"]

        if not presidents and not vps:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for {target_year}.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🇺🇸 {target_year} Presidential Race",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        for president in presidents:
            vp_name = president.get("vp_candidate", "No VP selected")

            ticket_info = f"**Party:** {president['party']}\n"
            ticket_info += f"**Running Mate:** {vp_name}\n"
            ticket_info += f"**Ideology:** {president['ideology']} ({president['axis']})\n"
            ticket_info += f"**Economic:** {president['economic']}\n"
            ticket_info += f"**Social:** {president['social']}\n"
            ticket_info += f"**Government:** {president['government']}"

            embed.add_field(
                name=f"🇺🇸 {president['name']}",
                value=ticket_info,
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @pres_signup.autocomplete("ideology")
    async def ideology_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["ideology"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @pres_signup.autocomplete("economic")
    async def economic_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["economic"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @pres_signup.autocomplete("social")
    async def social_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["social"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @pres_signup.autocomplete("government")
    async def government_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["government"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @pres_signup.autocomplete("axis")
    async def axis_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["axis"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("ideology")
    async def vp_ideology_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["ideology"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("economic")
    async def vp_economic_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["economic"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("social")
    async def vp_social_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["social"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("government")
    async def vp_government_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["government"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("axis")
    async def vp_axis_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()["axis"]
        return [app_commands.Choice(name=choice, value=choice) 
                for choice in choices if current.lower() in choice.lower()][:25]

    @vp_signup.autocomplete("presidential_candidate")
    async def vp_presidential_candidate_autocomplete(self, interaction: discord.Interaction, current: str):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            return []

        current_year = time_config["current_rp_date"].year
        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        available_presidents = [c["name"] for c in pres_config["candidates"] 
                              if c["year"] == current_year and c["office"] == "President"]

        return [app_commands.Choice(name=name, value=name) 
                for name in available_presidents if current.lower() in name.lower()][:25]

    @pres_signup.autocomplete("party")
    async def pres_party_autocomplete(self, interaction: discord.Interaction, current: str):
        # Get party choices from party management
        try:
            from .party_management import PartyManagement
            party_cog = self.bot.get_cog("PartyManagement")
            if party_cog:
                parties_col = self.bot.db["parties_config"]
                config = parties_col.find_one({"guild_id": interaction.guild.id})
                if config and "parties" in config:
                    party_names = [party["name"] for party in config["parties"]]
                    return [app_commands.Choice(name=name, value=name) 
                            for name in party_names if current.lower() in name.lower()][:25]
        except:
            pass

        # Fallback to default parties if party management not available
        default_parties = ["Democratic Party", "Republican Party", "Independent"]
        return [app_commands.Choice(name=name, value=name) 
                for name in default_parties if current.lower() in name.lower()][:25]

    @vp_signup.autocomplete("party")
    async def vp_party_autocomplete(self, interaction: discord.Interaction, current: str):
        # Get party choices from party management
        try:
            from .party_management import PartyManagement
            party_cog = self.bot.get_cog("PartyManagement")
            if party_cog:
                parties_col = self.bot.db["parties_config"]
                config = parties_col.find_one({"guild_id": interaction.guild.id})
                if config and "parties" in config:
                    party_names = [party["name"] for party in config["parties"]]
                    return [app_commands.Choice(name=name, value=name) 
                            for name in party_names if current.lower() in name.lower()][:25]
        except:
            pass

        # Fallback to default parties if party management not available
        default_parties = ["Democratic Party", "Republican Party", "Independent"]
        return [app_commands.Choice(name=name, value=name) 
                for name in default_parties if current.lower() in name.lower()][:25]


    @app_commands.command(
        name="admin_view_state_data",
        description="View STATE_DATA for a specific state (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_state_data(
        self,
        interaction: discord.Interaction,
        state_name: str = None
    ):
        """View STATE_DATA for a specific state or all states"""
        if state_name:
            state_name = state_name.upper()
            if state_name not in STATE_DATA:
                await interaction.response.send_message(
                    f"❌ State '{state_name}' not found in STATE_DATA.",
                    ephemeral=True
                )
                return

            data = STATE_DATA[state_name]
            embed = discord.Embed(
                title=f"📊 State Data: {state_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="🗳️ Party Support",
                value=f"**Republican:** {data.get('republican', 'N/A')}%\n"
                      f"**Democrat:** {data.get('democrat', 'N/A')}%\n"
                      f"**Other:** {data.get('other', 'N/A')}%",
                inline=True
            )

            embed.add_field(
                name="🎯 Political Profile",
                value=f"**Ideology:** {data.get('ideology', 'N/A')}\n"
                      f"**Economic:** {data.get('economic', 'N/A')}\n"
                      f"**Social:** {data.get('social', 'N/A')}\n"
                      f"**Government:** {data.get('government', 'N/A')}\n"
                      f"**Axis:** {data.get('axis', 'N/A')}",
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Show summary of all states
            embed = discord.Embed(
                title="📊 All STATE_DATA Summary",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            states_list = list(STATE_DATA.keys())
            states_per_field = 20

            # Split states into chunks for display
            for i in range(0, len(states_list), states_per_field):
                chunk = states_list[i:i + states_per_field]
                field_name = f"States ({i+1}-{min(i+states_per_field, len(states_list))})"
                embed.add_field(
                    name=field_name,
                    value=", ".join(chunk),
                    inline=False
                )

            embed.add_field(
                name="📈 Total States",
                value=str(len(states_list)),
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_ideology_modifications_log",
        description="View log of ideology modifications made (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_ideology_modifications_log(
        self,
        interaction: discord.Interaction,
        limit: int = 10
    ):
        """View recent ideology modifications"""
        if limit > 25:
            limit = 25

        ideology_col = self.bot.db["ideology_modifications"]

        modifications = list(ideology_col.find(
            {"guild_id": interaction.guild.id}
        ).sort("timestamp", -1).limit(limit))

        if not modifications:
            await interaction.response.send_message(
                "📝 No ideology modifications found for this server.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📝 Ideology Modifications Log",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        for mod in modifications:
            user = interaction.guild.get_member(mod.get("user_id"))
            user_name = user.display_name if user else f"User {mod.get('user_id', 'Unknown')}"

            timestamp = mod["timestamp"].strftime("%Y-%m-%d %H:%M")

            if mod["action"] == "add_state":
                value = f"**Added state:** {mod['state_name']}\n"
                value += f"**Data:** {mod['data']}\n"
                value += f"**By:** {user_name} on {timestamp}"
            elif mod["action"] == "modify_state":
                value = f"**Modified:** {mod['state_name']}\n"
                value += f"**Field:** {mod['field']}\n"
                value += f"**Changed:** {mod['old_value']} → {mod['new_value']}\n"
                value += f"**By:** {user_name} on {timestamp}"
            elif mod["action"] == "remove_state":
                value = f"**Removed state:** {mod['state_name']}\n"
                value += f"**Data:** {mod['removed_data']}\n"
                value += f"**By:** {user_name} on {timestamp}"
            else:
                value = f"**Action:** {mod['action']}\n**By:** {user_name} on {timestamp}"

            embed.add_field(
                name=f"🔄 {mod['action'].replace('_', ' ').title()}",
                value=value,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PresidentialSignups(bot))