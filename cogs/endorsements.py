import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional

class Endorsements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Endorsements cog loaded successfully")

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_endorsement_config(self, guild_id: int):
        """Get or create endorsement configuration"""
        col = self.bot.db["endorsement_config"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "role_mappings": {
                    "President": None,
                    "Vice President": None,
                    "Governor": None,
                    "Senator": None,
                    "House": None,
                    "Mayor": None,
                    "State Legislator": None,
                    "Other": None
                }
            }
            col.insert_one(config)
        return col, config

    def _get_endorsement_history(self, guild_id: int):
        """Get or create endorsement history"""
        col = self.bot.db["endorsement_history"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "endorsements": []
            }
            col.insert_one(config)
        return col, config

    def _check_duplicate_endorsement(self, guild_id: int, user_id: int, candidate_name: str):
        """Check if user has already endorsed this specific candidate"""
        history_col, history_config = self._get_endorsement_history(guild_id)

        # Check if user has already endorsed this specific candidate
        for endorsement in history_config.get("endorsements", []):
            if (endorsement["endorser_id"] == user_id and 
                endorsement["candidate_name"].lower() == candidate_name.lower()):
                return True  # Already endorsed

        return False  # Not yet endorsed

    def _get_user_endorsement_value(self, guild_id: int, user: discord.Member):
        """Get endorsement value based on user's Discord roles"""
        config_col, config = self._get_endorsement_config(guild_id)
        role_mappings = config.get("role_mappings", {})
        
        # Check roles in order of priority (highest value first)
        role_priorities = [
            ("President", 1.0),
            ("Vice President", 0.5),
            ("Governor", 0.5),
            ("Senator", 0.5),
            ("House", 0.5),
            ("Mayor", 0.1),
            ("State Legislator", 0.1),
            ("Other", 0.1)
        ]
        
        for role_type, value in role_priorities:
            role_id = role_mappings.get(role_type)
            if role_id:
                role = discord.utils.get(user.roles, id=role_id)
                if role:
                    return value, role_type, role.name
        
        return 0.0, None, None

    def _find_candidate_in_all_systems(self, guild_id: int, candidate_name: str):
        """Find candidate in all possible systems (signups, winners, presidential)"""
        time_col, time_config = self._get_time_config(guild_id)
        current_year = time_config["current_rp_date"].year if time_config else 2024
        current_phase = time_config.get("current_phase", "") if time_config else ""
        
        candidates_found = []
        
        # Check general signups
        signups_col = self.bot.db["signups"]
        signups_config = signups_col.find_one({"guild_id": guild_id})
        if signups_config:
            for candidate in signups_config.get("candidates", []):
                if (candidate["name"].lower() == candidate_name.lower() and 
                    candidate["year"] == current_year):
                    candidates_found.append({
                        "collection": signups_col,
                        "candidate": candidate,
                        "system": "general_signups"
                    })
        
        # Check general winners
        winners_col = self.bot.db["winners"]
        winners_config = winners_col.find_one({"guild_id": guild_id})
        if winners_config:
            # For general campaign, look for primary winners
            primary_year = current_year - 1 if current_year % 2 == 0 else current_year
            for winner in winners_config.get("winners", []):
                if (winner["candidate"].lower() == candidate_name.lower() and 
                    winner.get("primary_winner", False) and
                    winner["year"] == primary_year):
                    candidates_found.append({
                        "collection": winners_col,
                        "candidate": winner,
                        "system": "general_winners"
                    })
        
        # Check presidential signups
        pres_signups_col = self.bot.db["presidential_signups"]
        pres_signups_config = pres_signups_col.find_one({"guild_id": guild_id})
        if pres_signups_config:
            for candidate in pres_signups_config.get("candidates", []):
                if (candidate["name"].lower() == candidate_name.lower() and 
                    candidate["year"] == current_year):
                    candidates_found.append({
                        "collection": pres_signups_col,
                        "candidate": candidate,
                        "system": "presidential_signups"
                    })
        
        # Check presidential winners
        pres_winners_col = self.bot.db["presidential_winners"]
        pres_winners_config = pres_winners_col.find_one({"guild_id": guild_id})
        if pres_winners_config:
            for winner in pres_winners_config.get("winners", []):
                if (winner["name"].lower() == candidate_name.lower() and 
                    winner["year"] == current_year):
                    candidates_found.append({
                        "collection": pres_winners_col,
                        "candidate": winner,
                        "system": "presidential_winners"
                    })
        
        return candidates_found

    def _update_candidate_with_endorsement(self, candidate_data, endorsement_value: float):
        """Update candidate with endorsement points"""
        collection = candidate_data["collection"]
        candidate = candidate_data["candidate"]
        system = candidate_data["system"]
        
        if system == "general_signups":
            # Update in signups collection
            collection.update_one(
                {"guild_id": candidate["guild_id"] if "guild_id" in candidate else collection.find_one({"candidates.user_id": candidate["user_id"]})["guild_id"], 
                 "candidates.user_id": candidate["user_id"]},
                {"$inc": {"candidates.$.points": endorsement_value}}
            )
        elif system == "general_winners":
            # Update in winners collection
            collection.update_one(
                {"guild_id": candidate.get("guild_id", collection.find_one({"winners.user_id": candidate["user_id"]})["guild_id"]),
                 "winners.user_id": candidate["user_id"]},
                {"$inc": {"winners.$.points": endorsement_value}}
            )
        elif system == "presidential_signups":
            # Update in presidential signups
            collection.update_one(
                {"guild_id": candidate.get("guild_id", collection.find_one({"candidates.user_id": candidate["user_id"]})["guild_id"]),
                 "candidates.user_id": candidate["user_id"]},
                {"$inc": {"candidates.$.points": endorsement_value}}
            )
        elif system == "presidential_winners":
            # Update in presidential winners
            collection.update_one(
                {"guild_id": candidate.get("guild_id", collection.find_one({"winners.user_id": candidate["user_id"]})["guild_id"]),
                 "winners.user_id": candidate["user_id"]},
                {"$inc": {"winners.$.total_points": endorsement_value}}
            )

    def _record_endorsement(self, guild_id: int, endorser_id: int, candidate_name: str, 
                           endorsement_value: float, role_type: str, role_name: str):
        """Record endorsement in history"""
        history_col, history_config = self._get_endorsement_history(guild_id)

        # Add new endorsement (no duplicates should reach here due to check)
        new_endorsement = {
            "endorser_id": endorser_id,
            "candidate_name": candidate_name,
            "endorsement_value": endorsement_value,
            "role_type": role_type,
            "role_name": role_name,
            "timestamp": datetime.utcnow()
        }

        history_config["endorsements"].append(new_endorsement)

        history_col.update_one(
            {"guild_id": guild_id},
            {"$set": {"endorsements": history_config["endorsements"]}}
        )

    @app_commands.command(
        name="endorse",
        description="Endorse a candidate (value based on your Discord role)"
    )
    @app_commands.describe(candidate_name="Name of the candidate you want to endorse")
    async def endorse(self, interaction: discord.Interaction, candidate_name: str):
        # Check if we're in a campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config:
            await interaction.response.send_message(
                "❌ Election system not configured.",
                ephemeral=True
            )
            return
        
        current_phase = time_config.get("current_phase", "")
        if current_phase not in ["Primary Campaign", "General Campaign"]:
            await interaction.response.send_message(
                f"❌ Endorsements can only be made during campaign phases. Current phase: **{current_phase}**",
                ephemeral=True
            )
            return
        
        # Check if user has already endorsed this specific candidate
        already_endorsed = self._check_duplicate_endorsement(interaction.guild.id, interaction.user.id, candidate_name)
        if already_endorsed:
            await interaction.response.send_message(
                f"❌ You have already endorsed **{candidate_name}**. You can't endorse the same candidate multiple times.",
                ephemeral=True
            )
            return
        
        # Get user's endorsement value based on Discord roles
        endorsement_value, role_type, role_name = self._get_user_endorsement_value(interaction.guild.id, interaction.user)
        
        if endorsement_value == 0.0:
            await interaction.response.send_message(
                "❌ You don't have a role that allows endorsements. Contact an administrator to set up endorsement roles.",
                ephemeral=True
            )
            return
        
        # Find candidate in all systems
        candidates_found = self._find_candidate_in_all_systems(interaction.guild.id, candidate_name)
        
        if not candidates_found:
            await interaction.response.send_message(
                f"❌ Candidate '{candidate_name}' not found in any active campaigns.",
                ephemeral=True
            )
            return
        
        if len(candidates_found) > 1:
            # Multiple candidates found - show selection
            candidate_list = ""
            for i, candidate_data in enumerate(candidates_found, 1):
                candidate = candidate_data["candidate"]
                system = candidate_data["system"]
                office = candidate.get("office", "Unknown")
                party = candidate.get("party", "Unknown")
                candidate_list += f"{i}. **{candidate['name']}** ({party}) - {office} ({system})\n"
            
            await interaction.response.send_message(
                f"⚠️ Multiple candidates named '{candidate_name}' found:\n\n{candidate_list}\n"
                f"Please be more specific or contact an administrator.",
                ephemeral=True
            )
            return
        
        # Single candidate found - proceed with endorsement
        candidate_data = candidates_found[0]
        candidate = candidate_data["candidate"]
        
        # Update candidate with endorsement points
        self._update_candidate_with_endorsement(candidate_data, endorsement_value)
        
        # Record endorsement
        self._record_endorsement(
            interaction.guild.id, 
            interaction.user.id, 
            candidate_name, 
            endorsement_value, 
            role_type, 
            role_name
        )
        
        # Create success embed
        embed = discord.Embed(
            title="✅ Endorsement Successful!",
            description=f"**{interaction.user.display_name}** has endorsed **{candidate['name']}**!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Candidate Details",
            value=f"**Name:** {candidate['name']}\n"
                  f"**Party:** {candidate.get('party', 'Unknown')}\n"
                  f"**Office:** {candidate.get('office', 'Unknown')}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Endorsement Details",
            value=f"**Endorser Role:** {role_name} ({role_type})\n"
                  f"**Points Added:** +{endorsement_value}\n"
                  f"**System:** {candidate_data['system'].replace('_', ' ').title()}",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ Note",
            value=f"You can endorse other candidates, but you can only endorse **{candidate['name']}** once.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="admin_set_endorsement_role",
        description="Set Discord role for endorsement position (Admin only)"
    )
    @app_commands.describe(
        position="Political position for endorsements",
        role="Discord role to assign to this position"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_endorsement_role(
        self,
        interaction: discord.Interaction,
        position: str,
        role: discord.Role
    ):
        valid_positions = [
            "President", "Vice President", "Governor", "Senator", 
            "House", "Mayor", "State Legislator", "Other"
        ]
        
        if position not in valid_positions:
            await interaction.response.send_message(
                f"❌ Invalid position. Valid options: {', '.join(valid_positions)}",
                ephemeral=True
            )
            return
        
        config_col, config = self._get_endorsement_config(interaction.guild.id)
        
        config["role_mappings"][position] = role.id
        
        config_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"role_mappings": config["role_mappings"]}}
        )
        
        # Get endorsement value for this position
        position_values = {
            "President": "1.0%",
            "Vice President": "0.5%",
            "Governor": "0.5%",
            "Senator": "0.5%",
            "House": "0.5%",
            "Mayor": "0.1%",
            "State Legislator": "0.1%",
            "Other": "0.1%"
        }
        
        await interaction.response.send_message(
            f"✅ Set **{role.name}** role for **{position}** endorsements.\n"
            f"Endorsement value: **{position_values.get(position, '0.1%')}** points",
            ephemeral=True
        )

    @admin_set_endorsement_role.autocomplete("position")
    async def position_autocomplete(self, interaction: discord.Interaction, current: str):
        positions = [
            "President", "Vice President", "Governor", "Senator", 
            "House", "Mayor", "State Legislator", "Other"
        ]
        return [app_commands.Choice(name=pos, value=pos) 
                for pos in positions if current.lower() in pos.lower()][:25]

    @app_commands.command(
        name="view_endorsement_roles",
        description="View current endorsement role mappings (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def view_endorsement_roles(self, interaction: discord.Interaction):
        config_col, config = self._get_endorsement_config(interaction.guild.id)
        role_mappings = config.get("role_mappings", {})
        
        embed = discord.Embed(
            title="🎯 Endorsement Role Mappings",
            description="Discord roles assigned to endorsement positions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        position_values = {
            "President": "1.0%",
            "Vice President": "0.5%",
            "Governor": "0.5%",
            "Senator": "0.5%",
            "House": "0.5%",
            "Mayor": "0.1%",
            "State Legislator": "0.1%",
            "Other": "0.1%"
        }
        
        for position, role_id in role_mappings.items():
            if role_id:
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Role not found (ID: {role_id})"
            else:
                role_name = "Not set"
            
            embed.add_field(
                name=f"{position} ({position_values.get(position, '0.1%')})",
                value=role_name,
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="view_endorsements",
        description="View all endorsements made in current cycle"
    )
    async def view_endorsements(self, interaction: discord.Interaction):
        history_col, history_config = self._get_endorsement_history(interaction.guild.id)
        endorsements = history_config.get("endorsements", [])
        
        if not endorsements:
            await interaction.response.send_message(
                "📋 No endorsements have been made yet.",
                ephemeral=True
            )
            return
        
        # Sort by timestamp (most recent first)
        endorsements.sort(key=lambda x: x["timestamp"], reverse=True)
        
        embed = discord.Embed(
            title="🎖️ Campaign Endorsements",
            description=f"Recent endorsements ({len(endorsements)} total)",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        # Show up to 15 most recent endorsements
        for endorsement in endorsements[:15]:
            endorser = interaction.guild.get_member(endorsement["endorser_id"])
            endorser_name = endorser.display_name if endorser else f"User {endorsement['endorser_id']}"
            
            timestamp = endorsement["timestamp"].strftime("%m/%d %H:%M")
            
            embed.add_field(
                name=f"🎯 {endorsement['candidate_name']}",
                value=f"**Endorsed by:** {endorser_name}\n"
                      f"**Role:** {endorsement['role_name']} ({endorsement['role_type']})\n"
                      f"**Value:** +{endorsement['endorsement_value']} points\n"
                      f"**Date:** {timestamp}",
                inline=True
            )
        
        if len(endorsements) > 15:
            embed.set_footer(text=f"Showing 15 of {len(endorsements)} endorsements")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="my_endorsements",
        description="View all your current endorsements"
    )
    async def my_endorsements(self, interaction: discord.Interaction):
        # Check endorsement value
        endorsement_value, role_type, role_name = self._get_user_endorsement_value(interaction.guild.id, interaction.user)

        # Find all current endorsements
        history_col, history_config = self._get_endorsement_history(interaction.guild.id)
        user_endorsements = [
            e for e in history_config.get("endorsements", []) 
            if e["endorser_id"] == interaction.user.id
        ]

        embed = discord.Embed(
            title="🎖️ Your Endorsements",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        if endorsement_value > 0:
            embed.add_field(
                name="💪 Endorsement Power",
                value=f"**Role:** {role_name} ({role_type})\n"
                      f"**Value:** {endorsement_value} points per endorsement",
                inline=True
            )
        else:
            embed.add_field(
                name="❌ No Endorsement Power",
                value="You don't have a role that allows endorsements",
                inline=True
            )

        if user_endorsements:
            # Sort by most recent first
            user_endorsements.sort(key=lambda x: x["timestamp"], reverse=True)

            endorsements_text = ""
            for i, endorsement in enumerate(user_endorsements[:10], 1):  # Show up to 10
                date_str = endorsement["timestamp"].strftime("%m/%d %H:%M")
                endorsements_text += f"{i}. **{endorsement['candidate_name']}** (+{endorsement['endorsement_value']}) - {date_str}\n"

            embed.add_field(
                name=f"✅ Active Endorsements ({len(user_endorsements)})",
                value=endorsements_text or "None",
                inline=False
            )

            if len(user_endorsements) > 10:
                embed.set_footer(text=f"Showing 10 of {len(user_endorsements)} endorsements")
        else:
            embed.add_field(
                name="📋 Active Endorsements",
                value="You haven't endorsed anyone yet",
                inline=False
            )

        embed.add_field(
            name="ℹ️ How It Works",
            value="• You can endorse multiple different candidates\n• You can only endorse each candidate once\n• Each endorsement adds points to that candidate",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Endorsements(bot))