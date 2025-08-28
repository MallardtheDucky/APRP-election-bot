import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional

class SpecialElections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Special Elections cog loaded successfully")

    # Main special election group
    special_group = app_commands.Group(name="special", description="Special election commands")

    # Admin subgroup for special elections
    special_admin_group = app_commands.Group(
        name="admin",
        description="Special election admin commands",
        parent=special_group,
        default_permissions=discord.Permissions(administrator=True)
    )

    def _get_special_config(self, guild_id: int):
        """Get or create special elections configuration"""
        col = self.bot.db["special_elections"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "active_elections": [],
                "completed_elections": []
            }
            col.insert_one(config)
        return col, config

    def _get_elections_config(self, guild_id: int):
        """Get elections configuration to access seats"""
        col = self.bot.db["elections_config"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _is_house_seat(self, seat_id: str) -> bool:
        """Check if seat is a House seat (eligible for special elections)"""
        return seat_id.startswith("REP-") or "District" in seat_id

    def _get_active_special_election(self, guild_id: int, seat_id: str = None):
        """Get active special election for a seat or any active election"""
        col, config = self._get_special_config(guild_id)

        for election in config.get("active_elections", []):
            if seat_id is None or election["seat_id"] == seat_id:
                return election
        return None

    def _calculate_special_poll_result(self, actual_percentage: float, margin_of_error: float = 7.0) -> float:
        """Calculate poll result with margin of error for special elections"""
        variation = random.uniform(-margin_of_error, margin_of_error)
        poll_result = actual_percentage + variation
        return max(0.1, min(99.9, poll_result))

    # Autocomplete methods for admin commands
    async def _get_house_seats_autocomplete(self, interaction: discord.Interaction, current: str):
        """Get House seats for autocomplete"""
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)
        if not elections_config:
            return []
        
        choices = []
        for seat in elections_config.get("seats", []):
            if self._is_house_seat(seat["seat_id"]) and current.lower() in seat["seat_id"].lower():
                choices.append(app_commands.Choice(name=seat["seat_id"], value=seat["seat_id"]))
        return choices[:25]

    async def _get_active_special_elections_autocomplete(self, interaction: discord.Interaction, current: str):
        """Get active special elections for autocomplete"""
        col, config = self._get_special_config(interaction.guild.id)
        
        choices = []
        for election in config.get("active_elections", []):
            if current.lower() in election["seat_id"].lower():
                choices.append(app_commands.Choice(name=election["seat_id"], value=election["seat_id"]))
        return choices[:25]

    @special_group.command(
        name="signup",
        description="Sign up for an active special election"
    )
    @app_commands.describe(
        candidate_name="Your candidate name",
        party="Your party affiliation"
    )
    async def special_signup(
        self,
        interaction: discord.Interaction,
        candidate_name: str,
        party: str
    ):
        # Check if there's an active special election
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently taking signups.",
                ephemeral=True
            )
            return

        # Check if we're in signup phase
        current_time = datetime.utcnow()
        signup_end = active_election["signup_end"]

        if current_time > signup_end:
            await interaction.response.send_message(
                "❌ Signup period for this special election has ended.",
                ephemeral=True
            )
            return

        # Check if user is already signed up
        for candidate in active_election.get("candidates", []):
            if candidate["user_id"] == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You are already signed up for this special election.",
                    ephemeral=True
                )
                return

        # Get seat information
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)
        seat_info = None
        for seat in elections_config.get("seats", []):
            if seat["seat_id"] == active_election["seat_id"]:
                seat_info = seat
                break

        if not seat_info:
            await interaction.response.send_message(
                "❌ Seat information not found.",
                ephemeral=True
            )
            return

        # Create candidate entry
        new_candidate = {
            "user_id": interaction.user.id,
            "name": candidate_name,
            "party": party,
            "points": 0.0,
            "seat_id": active_election["seat_id"],
            "office": seat_info["office"],
            "state": seat_info["state"],
            "signup_date": current_time,
            "stamina": 100
        }

        # Add candidate to election
        col, config = self._get_special_config(interaction.guild.id)

        for i, election in enumerate(config["active_elections"]):
            if election["seat_id"] == active_election["seat_id"]:
                if "candidates" not in election:
                    election["candidates"] = []
                election["candidates"].append(new_candidate)
                config["active_elections"][i] = election
                break

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"active_elections": config["active_elections"]}}
        )

        # Calculate time remaining
        time_remaining = signup_end - current_time
        hours_remaining = int(time_remaining.total_seconds() // 3600)
        minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)

        embed = discord.Embed(
            title="✅ Special Election Signup Successful!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 Candidate Info",
            value=f"**Name:** {candidate_name}\n"
                  f"**Party:** {party}\n"
                  f"**User:** {interaction.user.mention}",
            inline=True
        )

        embed.add_field(
            name="🏛️ Seat Details",
            value=f"**Seat:** {active_election['seat_id']}\n"
                  f"**Office:** {seat_info['office']}\n"
                  f"**State:** {seat_info['state']}",
            inline=True
        )

        embed.add_field(
            name="⏰ Timeline",
            value=f"**Signups End:** {hours_remaining}h {minutes_remaining}m\n"
                  f"**Campaign Starts:** After signup period\n"
                  f"**Election Ends:** {active_election['election_end'].strftime('%m/%d %H:%M')} UTC",
            inline=False
        )

        embed.add_field(
            name="📊 Starting Stats",
            value=f"**Points:** {new_candidate['points']:.2f}\n"
                  f"**Stamina:** {new_candidate['stamina']}",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Helper function to get candidate autocomplete choices
    async def _get_special_candidate_choices(self, interaction: discord.Interaction, current: str):
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            return []
        
        choices = []
        for candidate in active_election.get("candidates", []):
            if current.lower() in candidate["name"].lower():
                choices.append(app_commands.Choice(name=candidate["name"], value=candidate["name"]))
        return choices

    @special_group.command(
        name="speech",
        description="Give a campaign speech in the special election (reply with your speech)"
    )
    @app_commands.describe(target="The candidate you want to target with your speech")
    @app_commands.autocomplete(target=_get_special_candidate_choices)
    async def special_speech(
        self,
        interaction: discord.Interaction,
        target: Optional[str] = None
    ):
        # Check if user is in an active special election
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently running.",
                ephemeral=True
            )
            return

        # Check if campaign period is active
        current_time = datetime.utcnow()
        if current_time <= active_election["signup_end"] or current_time >= active_election["election_end"]:
            await interaction.response.send_message(
                "❌ Campaign period is not currently active.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        user_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["user_id"] == interaction.user.id:
                user_candidate = candidate
                break

        # Use candidate name if registered, otherwise use display name
        speaker_name = user_candidate["name"] if user_candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if user_candidate:
                target = user_candidate["name"]
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists in this special election
        target_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["name"].lower() == target.lower():
                target_candidate = candidate
                break

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' is not signed up for this special election.",
                ephemeral=True
            )
            return
        
        # Check stamina
        if user_candidate and user_candidate["stamina"] < 20:
            await interaction.response.send_message(
                f"❌ Not enough stamina! You need 20 stamina but only have {user_candidate['stamina']}.",
                ephemeral=True
            )
            return

        # Check cooldown
        cooldowns_col = self.bot.db["special_election_cooldowns"]
        last_action = cooldowns_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "action": "speech"
        })

        if last_action:
            time_since_last = (current_time - last_action["timestamp"]).total_seconds() / 3600
            if time_since_last < 1:  # 1 hour cooldown
                hours_remaining = 1 - time_since_last
                await interaction.response.send_message(
                    f"❌ You must wait {hours_remaining:.1f} more hours before giving another speech.",
                    ephemeral=True
                )
                return

        # Send initial message asking for speech
        await interaction.response.send_message(
            f"🎤 **{speaker_name}**, please reply to this message with your campaign speech!\n\n"
            f"**Targeting:** {target_candidate['name']}\n"
            f"**Running for:** {active_election['seat_id']}\n"
            f"**Requirements:**\n"
            f"• Speech content (700-3000 characters)\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 2-4 points, -20 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id)

        try:
            # Wait for user to reply with speech
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            speech_content = reply_message.content
            char_count = len(speech_content)

            # Check character limits
            if char_count < 700 or char_count > 3000:
                await reply_message.reply(f"❌ Speech must be 700-3000 characters. You wrote {char_count} characters.")
                return

            # Set cooldown after successful validation
            cooldowns_col.update_one(
                {
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id,
                    "action": "speech"
                },
                {
                    "$set": {
                        "timestamp": current_time,
                        "seat_id": active_election["seat_id"]
                    }
                },
                upsert=True
            )

            # Calculate points gained (2-4 points)
            points_gained = random.uniform(2.0, 4.0)

            # Update candidate points and stamina
            col, config = self._get_special_config(interaction.guild.id)

            for i, election in enumerate(config["active_elections"]):
                if election["seat_id"] == active_election["seat_id"]:
                    for j, candidate in enumerate(election["candidates"]):
                        if candidate["user_id"] == interaction.user.id:
                            election["candidates"][j]["points"] += points_gained
                            election["candidates"][j]["stamina"] -= 20
                            config["active_elections"][i] = election
                            break
                    break

            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"active_elections": config["active_elections"]}}
            )

            embed = discord.Embed(
                title="🎤 Special Election Campaign Speech",
                description=f"**{speaker_name}** delivers a speech targeting **{target_candidate['name']}**!",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            # Truncate speech for display if too long
            display_speech = speech_content
            if len(display_speech) > 1000:
                display_speech = display_speech[:997] + "..."

            embed.add_field(
                name="📜 Speech Content",
                value=display_speech,
                inline=False
            )

            embed.add_field(
                name="📊 Campaign Impact",
                value=f"**Points Gained:** +{points_gained:.2f}\n"
                      f"**Stamina Used:** -20\n"
                      f"**Remaining Stamina:** {user_candidate['stamina'] - 20 if user_candidate else 'N/A'}\n"
                      f"**Characters:** {char_count:,}",
                inline=True
            )

            embed.add_field(
                name="🏛️ Running for",
                value=f"**{active_election['seat_id']}**\n{target_candidate['office']} ({target_candidate['state']})",
                inline=True
            )

            embed.set_footer(text="Next speech available in 1 hour")

            await reply_message.reply(embed=embed)

        except Exception as e:
            await interaction.edit_original_response(
                content=f"⏰ **{speaker_name}**, your speech timed out. Please use `/special speech` again and reply with your speech within 5 minutes."
            )

    @special_group.command(
        name="poster",
        description="Put up campaign posters in the special election (upload image)"
    )
    @app_commands.describe(image="Upload your campaign poster image", target="The candidate you want to target with your poster")
    @app_commands.autocomplete(target=_get_special_candidate_choices)
    async def special_poster(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        target: Optional[str] = None
    ):
        # Check if user is in an active special election
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently running.",
                ephemeral=True
            )
            return

        # Check if campaign period is active
        current_time = datetime.utcnow()
        if current_time <= active_election["signup_end"] or current_time >= active_election["election_end"]:
            await interaction.response.send_message(
                "❌ Campaign period is not currently active.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        user_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["user_id"] == interaction.user.id:
                user_candidate = candidate
                break

        # Use candidate name if registered, otherwise use display name
        poster_creator = user_candidate["name"] if user_candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if user_candidate:
                target = user_candidate["name"]
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists in this special election
        target_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["name"].lower() == target.lower():
                target_candidate = candidate
                break

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' is not signed up for this special election.",
                ephemeral=True
            )
            return

        # Check stamina
        if user_candidate and user_candidate["stamina"] < 15:
            await interaction.response.send_message(
                f"❌ Not enough stamina! You need 15 stamina but only have {user_candidate['stamina']}.",
                ephemeral=True
            )
            return

        # Check cooldown
        cooldowns_col = self.bot.db["special_election_cooldowns"]
        last_action = cooldowns_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "action": "poster"
        })

        if last_action:
            time_since_last = (current_time - last_action["timestamp"]).total_seconds() / 3600
            if time_since_last < 1:  # 1 hour cooldown
                hours_remaining = 1 - time_since_last
                await interaction.response.send_message(
                    f"❌ You must wait {hours_remaining:.1f} more hours before putting up more posters.",
                    ephemeral=True
                )
                return

        # Check if attachment is an image
        if not image or not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "❌ Please upload an image file (PNG, JPG, GIF, etc.).",
                ephemeral=True
            )
            return

        # Check file size
        if image.size > 10 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image file too large! Maximum size is 10MB.",
                ephemeral=True
            )
            return

        # Set cooldown after successful validation
        cooldowns_col.update_one(
            {
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id,
                "action": "poster"
            },
            {
                "$set": {
                    "timestamp": current_time,
                    "seat_id": active_election["seat_id"]
                }
            },
            upsert=True
        )

        # Calculate points gained (1-3 points)
        points_gained = random.uniform(1.0, 3.0)

        # Update candidate points and stamina
        col, config = self._get_special_config(interaction.guild.id)

        for i, election in enumerate(config["active_elections"]):
            if election["seat_id"] == active_election["seat_id"]:
                for j, candidate in enumerate(election["candidates"]):
                    if candidate["user_id"] == interaction.user.id:
                        election["candidates"][j]["points"] += points_gained
                        election["candidates"][j]["stamina"] -= 15
                        config["active_elections"][i] = election
                        break
                break

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"active_elections": config["active_elections"]}}
        )

        embed = discord.Embed(
            title="📋 Special Election Campaign Posters",
            description=f"**{poster_creator}** puts up campaign posters targeting **{target_candidate['name']}**!",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Campaign Impact",
            value=f"**Points Gained:** +{points_gained:.2f}\n"
                  f"**Stamina Used:** -15\n"
                  f"**Remaining Stamina:** {user_candidate['stamina'] - 15 if user_candidate else 'N/A'}",
            inline=True
        )

        embed.add_field(
            name="🏛️ Running for",
            value=f"**{active_election['seat_id']}**\n{target_candidate['office']} ({target_candidate['state']})",
            inline=True
        )

        embed.add_field(
            name="📍 Distribution",
            value=f"Posted throughout the district\nat key locations and online",
            inline=True
        )

        embed.set_image(url=image.url)
        embed.set_footer(text="Next poster available in 1 hour")

        await interaction.response.send_message(embed=embed)

    @special_group.command(
        name="ad",
        description="Run campaign video advertisements in the special election (reply with video)"
    )
    @app_commands.describe(target="The candidate you want to target with your ad")
    @app_commands.autocomplete(target=_get_special_candidate_choices)
    async def special_ad(
        self,
        interaction: discord.Interaction,
        target: Optional[str] = None
    ):
        # Check if user is in an active special election
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently running.",
                ephemeral=True
            )
            return

        # Check if campaign period is active
        current_time = datetime.utcnow()
        if current_time <= active_election["signup_end"] or current_time >= active_election["election_end"]:
            await interaction.response.send_message(
                "❌ Campaign period is not currently active.",
                ephemeral=True
            )
            return

        # Check if user has a registered candidate (optional)
        user_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["user_id"] == interaction.user.id:
                user_candidate = candidate
                break

        # Use candidate name if registered, otherwise use display name
        ad_creator = user_candidate["name"] if user_candidate else interaction.user.display_name

        # If no target specified, require one when user is not a candidate
        if target is None:
            if user_candidate:
                target = user_candidate["name"]
            else:
                await interaction.response.send_message(
                    "❌ You must specify a target candidate to perform this action.",
                    ephemeral=True
                )
                return

        # Verify target candidate exists in this special election
        target_candidate = None
        for candidate in active_election.get("candidates", []):
            if candidate["name"].lower() == target.lower():
                target_candidate = candidate
                break

        if not target_candidate:
            await interaction.response.send_message(
                f"❌ Target candidate '{target}' is not signed up for this special election.",
                ephemeral=True
            )
            return

        # Check stamina
        if user_candidate and user_candidate["stamina"] < 25:
            await interaction.response.send_message(
                f"❌ Not enough stamina! You need 25 stamina but only have {user_candidate['stamina']}.",
                ephemeral=True
            )
            return

        # Check cooldown
        cooldowns_col = self.bot.db["special_election_cooldowns"]
        last_action = cooldowns_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "action": "ad"
        })

        if last_action:
            time_since_last = (current_time - last_action["timestamp"]).total_seconds() / 3600
            if time_since_last < 1:  # 1 hour cooldown
                hours_remaining = 1 - time_since_last
                await interaction.response.send_message(
                    f"❌ You must wait {hours_remaining:.1f} more hours before running another ad.",
                    ephemeral=True
                )
                return

        # Send initial message asking for video
        await interaction.response.send_message(
            f"📺 **{ad_creator}**, please reply to this message with your campaign video!\n\n"
            f"**Targeting:** {target_candidate['name']}\n"
            f"**Running for:** {active_election['seat_id']}\n"
            f"**Requirements:**\n"
            f"• Video file (MP4, MOV, AVI, etc.)\n"
            f"• Maximum size: 25MB\n"
            f"• Reply within 5 minutes\n\n"
            f"**Effect:** 3-6 points, -25 stamina",
            ephemeral=False
        )

        # Get the response message
        response_message = await interaction.original_response()

        def check(message):
            return (message.author.id == interaction.user.id and 
                    message.reference and 
                    message.reference.message_id == response_message.id and
                    len(message.attachments) > 0)

        try:
            # Wait for user to reply with attachment
            reply_message = await self.bot.wait_for('message', timeout=300.0, check=check)

            video = reply_message.attachments[0]

            # Check if attachment is a video
            if not video.content_type or not video.content_type.startswith('video/'):
                await reply_message.reply("❌ Please upload a video file (MP4 format preferred).")
                return

            # Check file size
            if video.size > 25 * 1024 * 1024:
                await reply_message.reply("❌ Video file too large! Maximum size is 25MB.")
                return

            # Set cooldown after successful validation
            cooldowns_col.update_one(
                {
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id,
                    "action": "ad"
                },
                {
                    "$set": {
                        "timestamp": current_time,
                        "seat_id": active_election["seat_id"]
                    }
                },
                upsert=True
            )

            # Calculate points gained (3-6 points)
            points_gained = random.uniform(3.0, 6.0)

            # Update candidate points and stamina
            col, config = self._get_special_config(interaction.guild.id)

            for i, election in enumerate(config["active_elections"]):
                if election["seat_id"] == active_election["seat_id"]:
                    for j, candidate in enumerate(election["candidates"]):
                        if candidate["user_id"] == interaction.user.id:
                            election["candidates"][j]["points"] += points_gained
                            election["candidates"][j]["stamina"] -= 25
                            config["active_elections"][i] = election
                            break
                    break

            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"active_elections": config["active_elections"]}}
            )

            embed = discord.Embed(
                title="📺 Special Election Campaign Advertisement",
                description=f"**{ad_creator}** creates a powerful campaign advertisement targeting **{target_candidate['name']}**!",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="📊 Campaign Impact",
                value=f"**Points Gained:** +{points_gained:.2f}\n"
                      f"**Stamina Used:** -25\n"
                      f"**Remaining Stamina:** {user_candidate['stamina'] - 25 if user_candidate else 'N/A'}",
                inline=True
            )

            embed.add_field(
                name="🏛️ Running for",
                value=f"**{active_election['seat_id']}**\n{target_candidate['office']} ({target_candidate['state']})",
                inline=True
            )

            embed.add_field(
                name="📱 Reach",
                value=f"Broadcast across the district\non TV, social media, and digital platforms",
                inline=True
            )

            embed.set_footer(text="Next ad available in 1 hour")

            await reply_message.reply(embed=embed)

        except Exception as e:
            await interaction.edit_original_response(
                content=f"⏰ **{ad_creator}**, your ad creation timed out. Please use `/special ad` again and reply with your video within 5 minutes."
            )

    @special_group.command(
        name="calendar",
        description="View the current special election timeline and status"
    )
    async def special_calendar(self, interaction: discord.Interaction):
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently running.",
                ephemeral=True
            )
            return

        current_time = datetime.utcnow()
        signup_end = active_election["signup_end"]
        election_end = active_election["election_end"]

        # Determine current phase
        if current_time <= signup_end:
            current_phase = "Signup Phase"
            time_remaining = signup_end - current_time
            next_phase = "Campaign Phase"
        elif current_time <= election_end:
            current_phase = "Campaign Phase"
            time_remaining = election_end - current_time
            next_phase = "Election Complete"
        else:
            current_phase = "Election Complete"
            time_remaining = timedelta(0)
            next_phase = "Results Declared"

        embed = discord.Embed(
            title="📅 Special Election Calendar",
            description=f"Timeline for **{active_election['seat_id']}** Special Election",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🕒 Current Phase",
            value=f"**{current_phase}**",
            inline=True
        )

        if time_remaining.total_seconds() > 0:
            hours_remaining = int(time_remaining.total_seconds() // 3600)
            minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
            embed.add_field(
                name="⏰ Time Remaining",
                value=f"{hours_remaining}h {minutes_remaining}m",
                inline=True
            )
            embed.add_field(
                name="⏭️ Next Phase",
                value=next_phase,
                inline=True
            )

        # Timeline
        timeline_text = f"**Election Start:** {active_election['election_start'].strftime('%m/%d %H:%M')} UTC\n"
        timeline_text += f"**Signups End:** {signup_end.strftime('%m/%d %H:%M')} UTC\n"
        timeline_text += f"**Campaign Period:** {signup_end.strftime('%m/%d %H:%M')} - {election_end.strftime('%m/%d %H:%M')} UTC\n"
        timeline_text += f"**Election End:** {election_end.strftime('%m/%d %H:%M')} UTC"

        embed.add_field(
            name="📋 Full Timeline",
            value=timeline_text,
            inline=False
        )

        # Candidate count
        candidate_count = len(active_election.get("candidates", []))
        embed.add_field(
            name="👥 Candidates",
            value=f"{candidate_count} registered",
            inline=True
        )

        # Seat info
        embed.add_field(
            name="🏛️ Seat Information",
            value=f"**Seat:** {active_election['seat_id']}\n**Reason:** {active_election.get('reason', 'Vacant seat')}",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @special_group.command(
        name="poll",
        description="Conduct an NPC poll for the special election with 7% margin of error"
    )
    @app_commands.describe(candidate_name="Specific candidate to highlight (leave blank to highlight yourself)")
    async def special_poll(
        self,
        interaction: discord.Interaction,
        candidate_name: Optional[str] = None
    ):
        active_election = self._get_active_special_election(interaction.guild.id)
        if not active_election:
            await interaction.response.send_message(
                "❌ No active special elections are currently running.",
                ephemeral=True
            )
            return

        candidates = active_election.get("candidates", [])
        if not candidates:
            await interaction.response.send_message(
                "❌ No candidates have signed up for the special election yet.",
                ephemeral=True
            )
            return

        # Find highlighted candidate
        highlighted_candidate = None
        if not candidate_name:
            # Check if user is a candidate
            for candidate in candidates:
                if candidate["user_id"] == interaction.user.id:
                    highlighted_candidate = candidate
                    candidate_name = candidate["name"]
                    break
        else:
            # Find by name
            for candidate in candidates:
                if candidate["name"].lower() == candidate_name.lower():
                    highlighted_candidate = candidate
                    break

        # Calculate poll percentages
        total_points = sum(c.get("points", 0) for c in candidates)
        poll_results = []

        for candidate in candidates:
            if total_points == 0:
                actual_percentage = 100.0 / len(candidates)  # Even split if no points
            else:
                candidate_points = candidate.get("points", 0)
                actual_percentage = (candidate_points / total_points) * 100.0
                actual_percentage = max(5.0, actual_percentage)  # Minimum 5%

            poll_result = self._calculate_special_poll_result(actual_percentage)

            poll_results.append({
                "candidate": candidate,
                "name": candidate["name"],
                "actual": actual_percentage,
                "poll": poll_result,
                "is_highlighted": candidate == highlighted_candidate
            })

        # Sort by poll results
        poll_results.sort(key=lambda x: x["poll"], reverse=True)

        # Generate polling details
        polling_orgs = [
            "District Polling Institute", "Local News Survey", "Special Election Research",
            "Constituency Analytics", "Emergency Poll Center"
        ]
        polling_org = random.choice(polling_orgs)
        sample_size = random.randint(300, 800)  # Smaller for special elections
        days_ago = random.randint(0, 2)

        embed = discord.Embed(
            title=f"📊 Special Election Poll: {active_election['seat_id']}",
            description=f"Latest polling for the **{active_election['seat_id']}** special election",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        # Create visual progress bar
        def create_progress_bar(percentage, width=20):
            filled = int((percentage / 100) * width)
            empty = width - filled
            return "█" * filled + "░" * empty

        # Add poll results
        results_text = ""
        for i, result in enumerate(poll_results, 1):
            highlight = "👑 " if result["is_highlighted"] else ""
            party_abbrev = result['candidate']['party'][0] if result['candidate']['party'] else "I"
            progress_bar = create_progress_bar(result['poll'])

            results_text += f"**{i}. {highlight}{result['name']}**\n"
            results_text += f"**{party_abbrev} - {result['candidate']['party']}**\n"
            results_text += f"{progress_bar} **{result['poll']:.1f}%**\n\n"

        embed.add_field(
            name="🗳️ Poll Results",
            value=results_text,
            inline=False
        )

        # Add highlighted candidate info if applicable
        if highlighted_candidate:
            highlighted_result = next((r for r in poll_results if r["is_highlighted"]), None)
            if highlighted_result:
                embed.add_field(
                    name="🎯 Highlighted Candidate",
                    value=f"**{highlighted_result['name']}** ({highlighted_result['candidate']['party']})\n"
                          f"Polling at: **{highlighted_result['poll']:.1f}%**",
                    inline=True
                )

        embed.add_field(
            name="📋 Poll Details",
            value=f"**Polling Organization:** {polling_org}\n"
                  f"**Sample Size:** {sample_size:,} likely voters\n"
                  f"**Margin of Error:** ±7.0%\n"
                  f"**Field Period:** {days_ago} day{'s' if days_ago > 1 else ''} ago",
            inline=False
        )

        embed.add_field(
            name="🔍 Election Context",
            value=f"**Total Candidates:** {len(candidates)}\n"
                  f"**Election Type:** Special Election\n"
                  f"**Duration:** 4 days total",
            inline=True
        )

        embed.add_field(
            name="⚠️ Disclaimer",
            value="This is a simulated poll with a ±7% margin of error. Results may not reflect actual campaign performance.",
            inline=False
        )

        embed.set_footer(text=f"Poll conducted by {polling_org}")

        await interaction.response.send_message(embed=embed)

    # Admin commands
    @special_admin_group.command(
        name="call_election",
        description="Call a special election for a vacant House seat"
    )
    @app_commands.describe(
        seat_id="The House seat ID to hold a special election for",
        reason="Reason for the special election"
    )
    @app_commands.autocomplete(seat_id=_get_house_seats_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_call_election(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        reason: str = "Seat became vacant"
    ):
        # Check if seat exists and is a House seat
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)
        if not elections_config:
            await interaction.response.send_message(
                "❌ Elections system not configured.",
                ephemeral=True
            )
            return

        seat_info = None
        for seat in elections_config.get("seats", []):
            if seat["seat_id"].upper() == seat_id.upper():
                seat_info = seat
                break

        if not seat_info:
            await interaction.response.send_message(
                f"❌ Seat '{seat_id}' not found.",
                ephemeral=True
            )
            return

        if not self._is_house_seat(seat_id):
            await interaction.response.send_message(
                "❌ Special elections can only be called for House seats.",
                ephemeral=True
            )
            return

        # Check if there's already an active special election for this seat
        active_election = self._get_active_special_election(interaction.guild.id, seat_id)
        if active_election:
            await interaction.response.send_message(
                f"❌ There is already an active special election for seat '{seat_id}'.",
                ephemeral=True
            )
            return

        # Create special election timeline
        current_time = datetime.utcnow()
        signup_end = current_time + timedelta(days=1)  # 1 day signup
        election_end = signup_end + timedelta(days=3)  # 3 day campaign

        new_election = {
            "seat_id": seat_id,
            "reason": reason,
            "election_start": current_time,
            "signup_end": signup_end,
            "election_end": election_end,
            "candidates": [],
            "called_by": interaction.user.id
        }

        # Add to database
        col, config = self._get_special_config(interaction.guild.id)
        if "active_elections" not in config:
            config["active_elections"] = []
        config["active_elections"].append(new_election)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"active_elections": config["active_elections"]}}
        )

        # Mark seat as vacant in elections config
        for i, seat in enumerate(elections_config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                elections_config["seats"][i].update({
                    "current_holder": None,
                    "current_holder_id": None,
                    "up_for_election": True,
                    "special_election": True
                })
                break

        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": elections_config["seats"]}}
        )

        embed = discord.Embed(
            title="🚨 Special Election Called!",
            description=f"A special election has been called for **{seat_id}**",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🏛️ Seat Information",
            value=f"**Seat:** {seat_id}\n"
                  f"**Office:** {seat_info['office']}\n"
                  f"**State:** {seat_info['state']}\n"
                  f"**Reason:** {reason}",
            inline=True
        )

        embed.add_field(
            name="📅 Election Timeline",
            value=f"**Signups:** {current_time.strftime('%m/%d %H:%M')} - {signup_end.strftime('%m/%d %H:%M')} UTC\n"
                  f"**Campaign:** {signup_end.strftime('%m/%d %H:%M')} - {election_end.strftime('%m/%d %H:%M')} UTC\n"
                  f"**Duration:** 4 days total",
            inline=True
        )

        embed.add_field(
            name="📝 How to Participate",
            value="Candidates can sign up using `/special signup` during the signup period.",
            inline=False
        )

        embed.add_field(
            name="ℹ️ Special Election Rules",
            value="• House seats only\n• 1 day signup period\n• 3 day campaign period\n• No primary election\n• Highest points wins",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @special_admin_group.command(
        name="end_election",
        description="End a special election and declare the winner"
    )
    @app_commands.describe(seat_id="The seat ID for the special election to end")
    @app_commands.autocomplete(seat_id=_get_active_special_elections_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_end_election(
        self,
        interaction: discord.Interaction,
        seat_id: str
    ):
        # Find the active special election
        col, config = self._get_special_config(interaction.guild.id)

        active_election = None
        election_index = None
        for i, election in enumerate(config.get("active_elections", [])):
            if election["seat_id"].upper() == seat_id.upper():
                active_election = election
                election_index = i
                break

        if not active_election:
            await interaction.response.send_message(
                f"❌ No active special election found for seat '{seat_id}'.",
                ephemeral=True
            )
            return

        candidates = active_election.get("candidates", [])
        if not candidates:
            await interaction.response.send_message(
                "❌ No candidates participated in this special election.",
                ephemeral=True
            )
            return

        # Determine winner (highest points)
        winner = max(candidates, key=lambda x: x.get("points", 0))

        # Update seat with winner
        elections_col, elections_config = self._get_elections_config(interaction.guild.id)

        for i, seat in enumerate(elections_config["seats"]):
            if seat["seat_id"].upper() == seat_id.upper():
                elections_config["seats"][i].update({
                    "current_holder": winner["name"],
                    "current_holder_id": winner["user_id"],
                    "up_for_election": False,
                    "special_election": False,
                    "term_start": datetime.utcnow(),
                    "term_end": datetime.utcnow() + timedelta(days=365 * 2)  # 2 year term
                })
                break

        elections_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"seats": elections_config["seats"]}}
        )

        # Move election to completed
        completed_election = active_election.copy()
        completed_election["completed_date"] = datetime.utcnow()
        completed_election["winner"] = winner

        if "completed_elections" not in config:
            config["completed_elections"] = []
        config["completed_elections"].append(completed_election)

        # Remove from active elections
        config["active_elections"].pop(election_index)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "active_elections": config["active_elections"],
                "completed_elections": config["completed_elections"]
            }}
        )

        # Create results embed
        embed = discord.Embed(
            title="🏆 Special Election Results",
            description=f"**{seat_id}** Special Election Complete!",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎉 Winner",
            value=f"**{winner['name']}** ({winner['party']})\n"
                  f"User: <@{winner['user_id']}>\n"
                  f"Points: {winner.get('points', 0):.2f}",
            inline=True
        )

        # Show all results
        sorted_candidates = sorted(candidates, key=lambda x: x.get("points", 0), reverse=True)
        results_text = ""
        for i, candidate in enumerate(sorted_candidates, 1):
            crown = "👑 " if candidate == winner else ""
            results_text += f"**{i}. {crown}{candidate['name']}** ({candidate['party']})\n"
            results_text += f"Points: {candidate.get('points', 0):.2f}\n\n"

        embed.add_field(
            name="📊 Final Results",
            value=results_text[:1024],
            inline=False
        )

        embed.add_field(
            name="🏛️ Seat Assignment",
            value=f"**{winner['name']}** has been assigned to seat **{seat_id}**\n"
                  f"Term: 2 years from today",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @special_admin_group.command(
        name="view_points",
        description="View real campaign points for all candidates in a special election"
    )
    @app_commands.describe(seat_id="The seat ID for the special election")
    @app_commands.autocomplete(seat_id=_get_active_special_elections_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_points(
        self,
        interaction: discord.Interaction,
        seat_id: str = None
    ):
        col, config = self._get_special_config(interaction.guild.id)

        if seat_id:
            # View specific election
            active_election = None
            for election in config.get("active_elections", []):
                if election["seat_id"].upper() == seat_id.upper():
                    active_election = election
                    break

            if not active_election:
                await interaction.response.send_message(
                    f"❌ No active special election found for seat '{seat_id}'.",
                    ephemeral=True
                )
                return

            candidates = active_election.get("candidates", [])
            if not candidates:
                await interaction.response.send_message(
                    "❌ No candidates in this special election yet.",
                    ephemeral=True
                )
                return

            # Sort by points
            sorted_candidates = sorted(candidates, key=lambda x: x.get("points", 0), reverse=True)

            embed = discord.Embed(
                title=f"📊 Special Election Points: {seat_id}",
                description="Real campaign points (Admin View Only)",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            points_text = ""
            for i, candidate in enumerate(sorted_candidates, 1):
                points_text += f"**{i}. {candidate['name']}** ({candidate['party']})\n"
                points_text += f"Points: {candidate.get('points', 0):.2f} | Stamina: {candidate.get('stamina', 100)}\n"
                points_text += f"User: <@{candidate['user_id']}>\n\n"

            embed.add_field(
                name="🎯 Candidate Rankings",
                value=points_text[:1024],
                inline=False
            )

            # Timeline info
            current_time = datetime.utcnow()
            if current_time <= active_election["signup_end"]:
                phase = "Signup Phase"
                time_remaining = active_election["signup_end"] - current_time
            elif current_time <= active_election["election_end"]:
                phase = "Campaign Phase"
                time_remaining = active_election["election_end"] - current_time
            else:
                phase = "Election Complete"
                time_remaining = timedelta(0)

            embed.add_field(
                name="⏰ Election Status",
                value=f"**Phase:** {phase}\n"
                      f"**Time Remaining:** {int(time_remaining.total_seconds() // 3600)}h {int((time_remaining.total_seconds() % 3600) // 60)}m",
                inline=True
            )

        else:
            # View all active special elections
            active_elections = config.get("active_elections", [])
            if not active_elections:
                await interaction.response.send_message(
                    "❌ No active special elections found.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="📊 All Active Special Elections",
                description="Campaign points overview (Admin View Only)",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            for election in active_elections:
                candidates = election.get("candidates", [])
                if candidates:
                    sorted_candidates = sorted(candidates, key=lambda x: x.get("points", 0), reverse=True)
                    top_candidate = sorted_candidates[0]

                    election_text = f"**Leader:** {top_candidate['name']} ({top_candidate.get('points', 0):.2f} pts)\n"
                    election_text += f"**Candidates:** {len(candidates)}\n"

                    current_time = datetime.utcnow()
                    if current_time <= election["signup_end"]:
                        phase = "Signup"
                    elif current_time <= election["election_end"]:
                        phase = "Campaign"
                    else:
                        phase = "Complete"

                    election_text += f"**Phase:** {phase}"
                else:
                    election_text = "No candidates yet"

                embed.add_field(
                    name=f"🏛️ {election['seat_id']}",
                    value=election_text,
                    inline=True
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @special_admin_group.command(
        name="cancel_election",
        description="Cancel an active special election"
    )
    @app_commands.describe(
        seat_id="The seat ID for the special election to cancel",
        reason="Reason for cancellation"
    )
    @app_commands.autocomplete(seat_id=_get_active_special_elections_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_cancel_election(
        self,
        interaction: discord.Interaction,
        seat_id: str,
        reason: str = "Administrative decision"
    ):
        col, config = self._get_special_config(interaction.guild.id)

        # Find and remove the election
        election_index = None
        cancelled_election = None
        for i, election in enumerate(config.get("active_elections", [])):
            if election["seat_id"].upper() == seat_id.upper():
                election_index = i
                cancelled_election = election
                break

        if not cancelled_election:
            await interaction.response.send_message(
                f"❌ No active special election found for seat '{seat_id}'.",
                ephemeral=True
            )
            return

        # Remove from active elections
        config["active_elections"].pop(election_index)

        # Add to completed elections as cancelled
        cancelled_election["cancelled"] = True
        cancelled_election["cancellation_reason"] = reason
        cancelled_election["cancelled_date"] = datetime.utcnow()

        if "completed_elections" not in config:
            config["completed_elections"] = []
        config["completed_elections"].append(cancelled_election)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "active_elections": config["active_elections"],
                "completed_elections": config["completed_elections"]
            }}
        )

        candidate_count = len(cancelled_election.get("candidates", []))

        embed = discord.Embed(
            title="❌ Special Election Cancelled",
            description=f"The special election for **{seat_id}** has been cancelled.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📋 Election Details",
            value=f"**Seat:** {seat_id}\n"
                  f"**Candidates:** {candidate_count}\n"
                  f"**Reason:** {reason}",
            inline=True
        )

        embed.add_field(
            name="👥 Affected Candidates",
            value=f"{candidate_count} candidates were registered for this election.",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(SpecialElections(bot))