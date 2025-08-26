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

        # Validate party role if configured
        party_cog = self.bot.get_cog("PartyManagement")
        if party_cog:
            is_valid, error_msg = party_cog.validate_user_party_role(interaction.user, party, interaction.guild.id)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return

        # Check if user already signed up
        for candidate in pres_config["candidates"]:
            if candidate["user_id"] == interaction.user.id:
                await interaction.response.send_message(
                    f"❌ You are already registered as **{candidate['name']}** ({candidate['party']})",
                    ephemeral=True
                )
                return

        # Check if user has a regular election signup
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": interaction.guild.id})
        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if (candidate["user_id"] == interaction.user.id and
                    candidate["year"] == current_year):
                    await interaction.response.send_message(
                        f"❌ You are already signed up for a regular election as **{candidate['name']}** ({candidate['seat_id']}) in {current_year}. You cannot sign up as a presidential candidate while running for another office.",
                        ephemeral=True
                    )
                    return

        # Check if user has pending VP requests
        for vp_request in pres_config.get("pending_vp_requests", []):
            if (vp_request["user_id"] == interaction.user.id and
                vp_request["year"] == current_year and
                vp_request["status"] == "pending"):
                await interaction.response.send_message(
                    f"❌ You have a pending VP request with **{vp_request['presidential_candidate']}** for {current_year}. You cannot sign up as a presidential candidate while you have pending VP requests.",
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

        # Validate party role if configured
        party_cog = self.bot.get_cog("PartyManagement")
        if party_cog:
            is_valid, error_msg = party_cog.validate_user_party_role(interaction.user, party, interaction.guild.id)
            if not is_valid:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return

        # Check if user already signed up for VP
        for candidate in pres_config["candidates"]:
            if candidate["user_id"] == interaction.user.id:
                await interaction.response.send_message(
                    f"❌ You are already registered as VP candidate **{candidate['name']}** ({candidate['party']})",
                    ephemeral=True
                )
                return

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

        # Check if user is trying to select themselves as VP
        if presidential_candidate_data["user_id"] == interaction.user.id:
            await interaction.response.send_message(
                f"❌ You cannot select yourself as your own running mate. Please choose a different presidential candidate.",
                ephemeral=True
            )
            return

        # Check if user already has ANY presidential campaign signup (President or VP)
        existing_signup = None
        for candidate in pres_config["candidates"]:
            if (candidate["user_id"] == interaction.user.id and
                candidate["year"] == current_year and
                candidate["office"] in ["President", "Vice President"]):
                existing_signup = candidate
                break

        if existing_signup:
            await interaction.response.send_message(
                f"❌ You are already signed up as **{existing_signup['name']}** ({existing_signup['party']}) for {existing_signup['office']} in {current_year}.",
                ephemeral=True
            )
            return

        # Check if user has a regular election signup
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": interaction.guild.id})
        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if (candidate["user_id"] == interaction.user.id and
                    candidate["year"] == current_year):
                    await interaction.response.send_message(
                        f"❌ You are already signed up for a regular election as **{candidate['name']}** ({candidate['seat_id']}) in {current_year}. You cannot sign up as a VP candidate while running for another office.",
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

        # Check if this presidential candidate already has a VP
        if user_pres_campaign.get("vp_candidate"):
            await interaction.response.send_message(
                f"❌ You already have a VP candidate: **{user_pres_campaign['vp_candidate']}**. You cannot accept another VP request.",
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
                # Find and remove VP candidate from the candidates list
                candidates_to_keep = []
                for candidate in pres_config["candidates"]:
                    if not (candidate["user_id"] == vp_candidate_id and
                           candidate["year"] == current_year and
                           candidate["office"] == "Vice President" and
                           candidate.get("presidential_candidate_id") == interaction.user.id):
                        candidates_to_keep.append(candidate)
                pres_config["candidates"] = candidates_to_keep

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
        name="admin_cleanup_duplicates",
        description="Remove duplicate presidential campaign entries (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_cleanup_duplicates(self, interaction: discord.Interaction):
        """Remove duplicate presidential campaign entries"""
        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Track users we've seen
        seen_users = {}
        cleaned_candidates = []
        duplicates_removed = 0

        for candidate in pres_config["candidates"]:
            user_id = candidate["user_id"]
            year = candidate["year"]
            office = candidate["office"]

            # Create a unique key for each user-year combination
            user_key = f"{user_id}_{year}"

            if user_key in seen_users:
                # This is a duplicate
                duplicates_removed += 1
                continue
            else:
                # First time seeing this user for this year
                seen_users[user_key] = candidate
                cleaned_candidates.append(candidate)

        if duplicates_removed > 0:
            # Update the database
            pres_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"candidates": cleaned_candidates}}
            )

            await interaction.response.send_message(
                f"✅ Cleanup complete! Removed **{duplicates_removed}** duplicate entries.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ No duplicate entries found.",
                ephemeral=True
            )

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
        current_phase = time_config.get("current_phase", "")
        target_year = year if year else current_year

        # Handle different phases differently
        if current_phase in ["General Campaign", "General Election"]:
            # During general campaign/election, show only the nominees who won their primaries

            # Get primary winners who advanced to general election
            winners_col = self.bot.db["presidential_winners"]
            winners_config = winners_col.find_one({"guild_id": interaction.guild.id})

            # Also check delegate system for primary winners
            delegates_col = self.bot.db["delegates_config"] 
            delegates_config = delegates_col.find_one({"guild_id": interaction.guild.id})

            # For general election, look for primary winners from the signup year
            primary_year = target_year - 1 if target_year % 2 == 0 else target_year
            general_candidates = []

            pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

            # First, check presidential_winners collection (primary source)
            if winners_config and winners_config.get("winners"):
                party_winners = winners_config.get("winners", {})
                print(f"Debug: Found presidential winners: {party_winners}")
                
                for party, winner_name in party_winners.items():
                    if pres_config:
                        for candidate in pres_config.get("candidates", []):
                            if (candidate["name"] == winner_name and 
                                candidate["year"] == primary_year and 
                                candidate["office"] == "President"):
                                general_candidates.append(candidate)
                                print(f"Debug: Added general candidate: {candidate['name']}")
                                break

            # Fallback: get winners from delegates system
            if not general_candidates and delegates_config and "primary_winners" in delegates_config:
                primary_winners = delegates_config["primary_winners"]
                for key, winner_name in primary_winners.items():
                    if f"_{primary_year}" in key:  # Winner from the right year
                        party = key.replace(f"_{primary_year}", "")
                        
                        # Find the full candidate data
                        if pres_config:
                            for candidate in pres_config.get("candidates", []):
                                if (candidate["name"] == winner_name and 
                                    candidate["year"] == primary_year and 
                                    candidate["office"] == "President"):
                                    general_candidates.append(candidate)
                                    break

            # Also include qualified independents from delegates system
            if delegates_config:
                delegate_totals = delegates_config.get("delegate_totals", {})
                delegate_threshold = 50  # Threshold for independents to qualify

                # Find independent candidates with enough delegates
                if pres_config:
                    for candidate in pres_config.get("candidates", []):
                        if (candidate.get("year") == primary_year and 
                            candidate.get("office") == "President"):
                            
                            candidate_party = candidate.get("party", "").lower()
                            is_independent = not ("democrat" in candidate_party or "republican" in candidate_party)
                            
                            if is_independent:
                                candidate_delegates = delegate_totals.get(candidate["name"], 0)
                                if candidate_delegates >= delegate_threshold:
                                    # Check if already added
                                    if not any(gc["name"] == candidate["name"] for gc in general_candidates):
                                        general_candidates.append(candidate)

            # If no primary winners found, show all presidential candidates as a fallback
            if not general_candidates and pres_config:
                print(f"Debug: No primary winners found, showing all presidential candidates for year {primary_year}")
                all_presidential_candidates = [
                    c for c in pres_config.get("candidates", [])
                    if c.get("year") == primary_year and c.get("office") == "President"
                ]
                
                if all_presidential_candidates:
                    # Show warning that these are all candidates, not confirmed primary winners
                    embed = discord.Embed(
                        title=f"⚠️ {target_year} Presidential Candidates (All Registered)",
                        description=f"Primary winners may not have been declared yet. Showing all registered presidential candidates from {primary_year}:",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )

                    for candidate in all_presidential_candidates:
                        vp_name = candidate.get("vp_candidate", "No VP selected")
                        points = candidate.get("points", 0)

                        # Party color
                        party_emoji = "🔴" if "republican" in candidate["party"].lower() else "🔵" if "democrat" in candidate["party"].lower() else "🟣"

                        ticket_info = f"{party_emoji} **Party:** {candidate['party']}\n"
                        ticket_info += f"**Running Mate:** {vp_name}\n"
                        ticket_info += f"**Primary Points:** {points:.2f}\n"
                        ticket_info += f"**Status:** {'🏆 Likely Winner' if points > 0 else 'Registered Candidate'}\n\n"
                        ticket_info += f"**Ideology:** {candidate['ideology']} ({candidate['axis']})\n"
                        ticket_info += f"**Economic:** {candidate['economic']}\n"
                        ticket_info += f"**Social:** {candidate['social']}\n"
                        ticket_info += f"**Government:** {candidate['government']}"

                        embed.add_field(
                            name=f"🇺🇸 {candidate['name']}",
                            value=ticket_info,
                            inline=False
                        )

                    embed.add_field(
                        name="💡 Note",
                        value="If these candidates should be primary winners, use `/admin_process_pres_primaries` to declare winners.",
                        inline=False
                    )

                    await interaction.response.send_message(embed=embed)
                    return

            if not general_candidates:
                await interaction.response.send_message(
                    f"❌ No general election candidates found for {target_year}.\n"
                    f"Primary winners may not have been declared yet.\n"
                    f"Use `/admin_process_pres_primaries signup_year:{primary_year} confirm:True` to process primary winners.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"🗳️ {target_year} General Election Candidates",
                description=f"Primary winners advancing to the general election",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            # Note: For polling percentages, we'll use a simple placeholder since 
            # the calculation method isn't fully implemented in the provided code
            total_candidates = len(general_candidates)
            base_percentage = 100.0 / total_candidates if total_candidates > 0 else 0

            for i, candidate in enumerate(general_candidates):
                vp_name = candidate.get("vp_candidate", "No VP selected")
                
                # Simple polling calculation (you can improve this)
                polling_percentage = base_percentage + ((-1) ** i) * (i * 2)  # Slight variation

                # Party color
                party_emoji = "🔴" if "republican" in candidate["party"].lower() else "🔵" if "democrat" in candidate["party"].lower() else "🟣"

                ticket_info = f"{party_emoji} **Party:** {candidate['party']}\n"
                ticket_info += f"**Running Mate:** {vp_name}\n"
                ticket_info += f"**Estimated Polling:** {polling_percentage:.1f}%\n\n"
                ticket_info += f"**Ideology:** {candidate['ideology']} ({candidate['axis']})\n"
                ticket_info += f"**Economic:** {candidate['economic']}\n"
                ticket_info += f"**Social:** {candidate['social']}\n"
                ticket_info += f"**Government:** {candidate['government']}"

                # Show delegate count if available
                if delegates_config:
                    delegate_totals = delegates_config.get("delegate_totals", {})
                    candidate_delegates = delegate_totals.get(candidate["name"], 0)
                    if candidate_delegates > 0:
                        ticket_info += f"\n**Primary Delegates:** {candidate_delegates}"

                embed.add_field(
                    name=f"🇺🇸 {candidate['name']}",
                    value=ticket_info,
                    inline=False
                )

        else:
            # During primary phases, show all registered candidates
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
                title=f"🇺🇸 {target_year} Presidential Primary Race",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )

            for president in presidents:
                vp_name = president.get("vp_candidate", "No VP selected")

                ticket_info = f"**Party:** {president['party']}\n"
                ticket_info += f"**Running Mate:** {vp_name}\n"
                ticket_info += f"**Points:** {president.get('points', 0):.2f}\n"
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

    @app_commands.command(
        name="admin_force_withdraw",
        description="Force withdraw a presidential or VP candidate (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        candidate_name="Name of the candidate to withdraw",
        reason="Reason for withdrawal (optional)"
    )
    async def admin_force_withdraw(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        reason: Optional[str] = None
    ):
        """Force withdraw a presidential or VP candidate"""
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        user_campaign = None
        campaign_index = None
        for i, candidate in enumerate(pres_config["candidates"]):
            if (candidate["name"].lower() == candidate_name.lower() and
                candidate["year"] == current_year and
                candidate["office"] in ["President", "Vice President"]):
                user_campaign = candidate
                campaign_index = i
                break

        if not user_campaign:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found for the current year.",
                ephemeral=True
            )
            return

        # If withdrawing from presidential campaign, handle VP candidate
        if user_campaign["office"] == "President":
            vp_candidate_name = user_campaign.get("vp_candidate")
            vp_candidate_id = user_campaign.get("vp_candidate_id")

            if vp_candidate_id:
                candidates_to_keep = []
                for candidate in pres_config["candidates"]:
                    if not (candidate["user_id"] == vp_candidate_id and
                           candidate["year"] == current_year and
                           candidate["office"] == "Vice President" and
                           candidate.get("presidential_candidate_id") == user_campaign["user_id"]):
                        candidates_to_keep.append(candidate)
                pres_config["candidates"] = candidates_to_keep

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

        # Remove any pending VP requests associated with this candidate
        if "pending_vp_requests" in pres_config:
            pres_config["pending_vp_requests"] = [
                req for req in pres_config["pending_vp_requests"]
                if not (req["presidential_candidate_id"] == withdrawn_candidate["user_id"] and req["year"] == current_year)
            ]

        pres_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "candidates": pres_config["candidates"],
                "pending_vp_requests": pres_config["pending_vp_requests"]
            }}
        )

        embed = discord.Embed(
            title="👢 Forced Withdrawal",
            description=f"**{withdrawn_candidate['name']}** has been force withdrawn from the {current_year} {withdrawn_candidate['office']}ial race.",
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

        if reason:
            embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )

        if withdrawn_candidate["office"] == "President" and withdrawn_candidate.get("vp_candidate"):
            embed.add_field(
                name="⚠️ Impact",
                value=f"VP candidate **{withdrawn_candidate['vp_candidate']}** has also been removed from the ticket.",
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

    @admin_view_state_data.autocomplete("state_name")
    async def state_name_autocomplete(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

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

    @app_commands.command(
        name="admin_view_pres_primary_points",
        description="View all presidential candidate points during primaries (Admin only)"
    )
    @app_commands.describe(
        filter_party="Filter by party (optional)",
        year="Year to view points for (optional - uses current year if not specified)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_pres_primary_points(
        self,
        interaction: discord.Interaction,
        filter_party: str = None,
        year: int = None
    ):
        """View all presidential candidate points during primaries"""
        time_col, time_config = self._get_time_config(interaction.guild.id)

        if not time_config:
            await interaction.response.send_message("❌ Election system not configured.", ephemeral=True)
            return

        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year

        pres_col, pres_config = self._get_presidential_config(interaction.guild.id)

        # Get candidates for target year
        candidates = [c for c in pres_config["candidates"] if c["year"] == target_year]

        if filter_party:
            candidates = [c for c in candidates if filter_party.lower() in c["party"].lower()]

        if not candidates:
            await interaction.response.send_message(
                f"❌ No presidential candidates found for {target_year}" + 
                (f" with party filter '{filter_party}'" if filter_party else "") + ".",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🔍 Admin: Presidential Primary Points ({target_year})",
            description=f"Detailed view of all presidential candidate points" + 
                       (f" - Filtered by: {filter_party}" if filter_party else ""),
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Separate by office
        presidents = [c for c in candidates if c["office"] == "President"]
        vice_presidents = [c for c in candidates if c["office"] == "Vice President"]

        # Sort by points (highest first)
        presidents.sort(key=lambda x: x.get("points", 0), reverse=True)
        vice_presidents.sort(key=lambda x: x.get("points", 0), reverse=True)

        # Display Presidential candidates
        if presidents:
            president_text = ""
            for i, candidate in enumerate(presidents, 1):
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else f"User {candidate['user_id']}"

                president_text += f"**{i}. {candidate['name']}** ({candidate['party']})\n"
                president_text += f"   Points: {candidate.get('points', 0):.2f}\n"
                president_text += f"   Stamina: {candidate.get('stamina', 200)}\n"
                president_text += f"   Corruption: {candidate.get('corruption', 0)}\n"
                president_text += f"   User: {user_mention}\n"
                if candidate.get('vp_candidate'):
                    president_text += f"   VP: {candidate['vp_candidate']}\n"
                president_text += "\n"

            # Split into chunks if too long
            if len(president_text) > 1024:
                chunks = [president_text[i:i+1020] for i in range(0, len(president_text), 1020)]
                for i, chunk in enumerate(chunks):
                    field_name = f"🇺🇸 Presidential Candidates" + (f" (Part {i+1})" if len(chunks) > 1 else "")
                    embed.add_field(
                        name=field_name,
                        value=chunk,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🇺🇸 Presidential Candidates",
                    value=president_text,
                    inline=False
                )

        # Display Vice Presidential candidates
        if vice_presidents:
            vp_text = ""
            for i, candidate in enumerate(vice_presidents, 1):
                user = interaction.guild.get_member(candidate["user_id"])
                user_mention = user.mention if user else f"User {candidate['user_id']}"

                vp_text += f"**{i}. {candidate['name']}** ({candidate['party']})\n"
                vp_text += f"   Points: {candidate.get('points', 0):.2f}\n"
                vp_text += f"   Stamina: {candidate.get('stamina', 200)}\n"
                vp_text += f"   Corruption: {candidate.get('corruption', 0)}\n"
                vp_text += f"   User: {user_mention}\n"
                if candidate.get('presidential_candidate'):
                    vp_text += f"   Running with: {candidate['presidential_candidate']}\n"
                vp_text += "\n"

            if len(vp_text) > 1024:
                chunks = [vp_text[i:i+1020] for i in range(0, len(vp_text), 1020)]
                for i, chunk in enumerate(chunks):
                    field_name = f"🤝 Vice Presidential Candidates" + (f" (Part {i+1})" if len(chunks) > 1 else "")
                    embed.add_field(
                        name=field_name,
                        value=chunk,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🤝 Vice Presidential Candidates",
                    value=vp_text,
                    inline=False
                )

        # Add summary statistics
        total_candidates = len(candidates)
        avg_points = sum(c.get('points', 0) for c in candidates) / total_candidates if total_candidates > 0 else 0
        highest_points = max(c.get('points', 0) for c in candidates) if candidates else 0

        embed.add_field(
            name="📊 Statistics",
            value=f"**Total Candidates:** {total_candidates}\n"
                  f"**Average Points:** {avg_points:.2f}\n"
                  f"**Highest Points:** {highest_points:.2f}\n"
                  f"**Year:** {target_year}",
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

    @admin_view_pres_primary_points.autocomplete("filter_party")
    async def admin_primary_points_party_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for party filter in admin primary points command"""
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

async def setup(bot):
    await bot.add_cog(PresidentialSignups(bot))