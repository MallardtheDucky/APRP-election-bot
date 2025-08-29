from discord.ext import commands
import discord
from discord import app_commands
from datetime import datetime
from typing import List, Optional

class PartyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Party Management cog loaded successfully")

    # Simplified party command structure
    party_group = app_commands.Group(name="party", description="Party management commands")

    # Combine admin and member commands into single subgroup
    party_manage_group = app_commands.Group(name="manage", description="Party management commands", parent=party_group)
    party_info_group = app_commands.Group(name="info", description="Party information commands", parent=party_group)

    def _get_parties_config(self, guild_id: int):
        """Get or create parties configuration for a guild"""
        col = self.bot.db["parties_config"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            # Initialize with default parties
            config = {
                "guild_id": guild_id,
                "parties": [
                    {
                        "name": "Democratic Party",
                        "abbreviation": "D",
                        "color": 0x0099FF,  # Blue
                        "created_at": datetime.utcnow(),
                        "is_default": True
                    },
                    {
                        "name": "Republican Party",
                        "abbreviation": "R",
                        "color": 0xFF0000,  # Red
                        "created_at": datetime.utcnow(),
                        "is_default": True
                    },
                    {
                        "name": "Independent",
                        "abbreviation": "I",
                        "color": 0x800080,  # Purple
                        "created_at": datetime.utcnow(),
                        "is_default": True
                    }
                ]
            }
            col.insert_one(config)
        return col, config

    @party_manage_group.command(
        name="create",
        description="Create a new political party (Admin only)"
    )
    @app_commands.describe(
        name="Full name of the party",
        abbreviation="Party abbreviation (1-3 characters)",
        color="Hex color code (e.g., #FF0000 for red)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_party(
        self,
        interaction: discord.Interaction,
        name: str,
        abbreviation: str,
        color: str = None
    ):
        col, config = self._get_parties_config(interaction.guild.id)

        # Validate inputs
        if len(name) < 2 or len(name) > 50:
            await interaction.response.send_message(
                "❌ Party name must be between 2 and 50 characters.",
                ephemeral=True
            )
            return

        abbreviation = abbreviation.upper()
        if len(abbreviation) < 1 or len(abbreviation) > 3:
            await interaction.response.send_message(
                "❌ Party abbreviation must be between 1 and 3 characters.",
                ephemeral=True
            )
            return

        # Check if party name or abbreviation already exists
        for party in config["parties"]:
            if party["name"].lower() == name.lower():
                await interaction.response.send_message(
                    f"❌ A party named '{name}' already exists.",
                    ephemeral=True
                )
                return
            if party["abbreviation"].upper() == abbreviation.upper():
                await interaction.response.send_message(
                    f"❌ A party with abbreviation '{abbreviation}' already exists.",
                    ephemeral=True
                )
                return

        # Parse color
        party_color = 0x808080  # Default gray
        if color:
            try:
                if color.startswith("#"):
                    color = color[1:]
                party_color = int(color, 16)
                if party_color > 0xFFFFFF:
                    raise ValueError("Color too large")
            except (ValueError, TypeError):
                await interaction.response.send_message(
                    "❌ Invalid color format. Use hex format like #FF0000 or FF0000.",
                    ephemeral=True
                )
                return

        # Create new party
        new_party = {
            "name": name,
            "abbreviation": abbreviation,
            "color": party_color,
            "created_at": datetime.utcnow(),
            "is_default": False
        }

        config["parties"].append(new_party)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": config["parties"]}}
        )

        # Create embed to show the new party
        embed = discord.Embed(
            title="✅ Party Created Successfully",
            color=discord.Color(party_color),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Party Name", value=name, inline=True)
        embed.add_field(name="Abbreviation", value=abbreviation, inline=True)
        embed.add_field(name="Color", value=f"#{party_color:06X}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @party_info_group.command(
        name="list",
        description="List all available political parties"
    )
    async def list_parties(self, interaction: discord.Interaction):
        col, config = self._get_parties_config(interaction.guild.id)

        embed = discord.Embed(
            title="🏛️ Political Parties",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        for party in config["parties"]:
            party_type = "Default" if party.get("is_default", False) else "Custom"
            embed.add_field(
                name=f"{party['name']} ({party['abbreviation']})",
                value=f"Color: #{party['color']:06X}\nType: {party_type}",
                inline=True
            )

        if not config["parties"]:
            embed.description = "No parties configured yet."

        await interaction.response.send_message(embed=embed)

    @party_manage_group.command(
        name="remove",
        description="Remove a political party (Admin only)"
    )
    @app_commands.describe(
        party_name="Name of the party to remove"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_party(
        self,
        interaction: discord.Interaction,
        party_name: str
    ):
        col, config = self._get_parties_config(interaction.guild.id)

        # Find the party
        party_found = None
        for i, party in enumerate(config["parties"]):
            if party["name"].lower() == party_name.lower():
                party_found = i
                break

        if party_found is None:
            await interaction.response.send_message(
                f"❌ Party '{party_name}' not found.",
                ephemeral=True
            )
            return

        party = config["parties"][party_found]

        # Prevent removal of default parties
        if party.get("is_default", False):
            await interaction.response.send_message(
                f"❌ Cannot remove default party '{party['name']}'.",
                ephemeral=True
            )
            return

        # Remove the party
        removed_party = config["parties"].pop(party_found)

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": config["parties"]}}
        )

        await interaction.response.send_message(
            f"✅ Removed party **{removed_party['name']}** ({removed_party['abbreviation']})",
            ephemeral=True
        )

    @party_manage_group.command(
        name="edit",
        description="Edit an existing political party (Admin only)"
    )
    @app_commands.describe(
        current_name="Current name of the party to edit",
        new_name="New name for the party (optional)",
        new_abbreviation="New abbreviation for the party (optional)",
        new_color="New hex color code (optional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_party(
        self,
        interaction: discord.Interaction,
        current_name: str,
        new_name: str = None,
        new_abbreviation: str = None,
        new_color: str = None
    ):
        col, config = self._get_parties_config(interaction.guild.id)

        # Find the party
        party_found = None
        for i, party in enumerate(config["parties"]):
            if party["name"].lower() == current_name.lower():
                party_found = i
                break

        if party_found is None:
            await interaction.response.send_message(
                f"❌ Party '{current_name}' not found.",
                ephemeral=True
            )
            return

        party = config["parties"][party_found]
        changes = []

        # Update name if provided
        if new_name:
            if len(new_name) < 2 or len(new_name) > 50:
                await interaction.response.send_message(
                    "❌ Party name must be between 2 and 50 characters.",
                    ephemeral=True
                )
                return

            # Check if new name conflicts
            for other_party in config["parties"]:
                if other_party["name"].lower() == new_name.lower() and other_party != party:
                    await interaction.response.send_message(
                        f"❌ A party named '{new_name}' already exists.",
                        ephemeral=True
                    )
                    return

            config["parties"][party_found]["name"] = new_name
            changes.append(f"Name: {party['name']} → {new_name}")

        # Update abbreviation if provided
        if new_abbreviation:
            new_abbreviation = new_abbreviation.upper()
            if len(new_abbreviation) < 1 or len(new_abbreviation) > 3:
                await interaction.response.send_message(
                    "❌ Party abbreviation must be between 1 and 3 characters.",
                    ephemeral=True
                )
                return

            # Check if new abbreviation conflicts
            for other_party in config["parties"]:
                if other_party["abbreviation"].upper() == new_abbreviation.upper() and other_party != party:
                    await interaction.response.send_message(
                        f"❌ A party with abbreviation '{new_abbreviation}' already exists.",
                        ephemeral=True
                    )
                    return

            config["parties"][party_found]["abbreviation"] = new_abbreviation
            changes.append(f"Abbreviation: {party['abbreviation']} → {new_abbreviation}")

        # Update color if provided
        if new_color:
            try:
                if new_color.startswith("#"):
                    new_color = new_color[1:]
                party_color = int(new_color, 16)
                if party_color > 0xFFFFFF:
                    raise ValueError("Color too large")

                config["parties"][party_found]["color"] = party_color
                changes.append(f"Color: #{party['color']:06X} → #{party_color:06X}")
            except (ValueError, TypeError):
                await interaction.response.send_message(
                    "❌ Invalid color format. Use hex format like #FF0000 or FF0000.",
                    ephemeral=True
                )
                return

        if not changes:
            await interaction.response.send_message(
                "❌ No changes provided. Specify at least one field to update.",
                ephemeral=True
            )
            return

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": config["parties"]}}
        )

        embed = discord.Embed(
            title="✅ Party Updated Successfully",
            color=discord.Color(config["parties"][party_found]["color"]),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Changes Made",
            value="\n".join([f"• {change}" for change in changes]),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def get_party_choices(self, guild_id: int) -> list:
        """Get list of party choices for autocomplete"""
        col, config = self._get_parties_config(guild_id)
        return [
            app_commands.Choice(name=party["name"], value=party["name"])
            for party in config["parties"]
        ]

    @party_manage_group.command(
        name="reset",
        description="Reset all parties to default (Admin only - DESTRUCTIVE)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reset_parties(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """Reset all parties to default configuration"""
        if not confirm:
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will remove ALL custom parties and reset to defaults:\n"
                f"• Democratic Party (D)\n"
                f"• Republican Party (R)\n"
                f"• Independent (I)\n\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        col = self.bot.db["parties_config"]
        
        # Reset to default configuration
        default_config = {
            "guild_id": interaction.guild.id,
            "parties": [
                {
                    "name": "Democratic Party",
                    "abbreviation": "D",
                    "color": 0x0099FF,  # Blue
                    "created_at": datetime.utcnow(),
                    "is_default": True
                },
                {
                    "name": "Republican Party",
                    "abbreviation": "R",
                    "color": 0xFF0000,  # Red
                    "created_at": datetime.utcnow(),
                    "is_default": True
                },
                {
                    "name": "Independent",
                    "abbreviation": "I",
                    "color": 0x800080,  # Purple
                    "created_at": datetime.utcnow(),
                    "is_default": True
                }
            ]
        }

        col.replace_one(
            {"guild_id": interaction.guild.id},
            default_config,
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ All parties have been reset to defaults:\n"
            f"• Democratic Party (D) - Blue\n"
            f"• Republican Party (R) - Red\n"
            f"• Independent (I) - Purple",
            ephemeral=True
        )

    @party_manage_group.command(
        name="bulk_create",
        description="Create multiple parties at once (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_bulk_create_parties(
        self,
        interaction: discord.Interaction,
        party_data: str
    ):
        """Create multiple parties from formatted text: Name:Abbr:Color,Name:Abbr:Color"""
        col, config = self._get_parties_config(interaction.guild.id)

        # Parse format: "Green Party:G:00FF00,Libertarian Party:L:FFFF00"
        party_entries = party_data.split(",")
        created_parties = []
        errors = []

        for entry in party_entries:
            try:
                parts = entry.strip().split(":")
                if len(parts) != 3:
                    errors.append(f"Invalid format: {entry}")
                    continue

                name, abbreviation, color = parts
                abbreviation = abbreviation.upper()

                # Validate name length
                if len(name) < 2 or len(name) > 50:
                    errors.append(f"Name too long/short: {name}")
                    continue

                # Validate abbreviation length
                if len(abbreviation) < 1 or len(abbreviation) > 3:
                    errors.append(f"Invalid abbreviation: {abbreviation}")
                    continue

                # Check for duplicates
                duplicate = False
                for party in config["parties"]:
                    if party["name"].lower() == name.lower():
                        errors.append(f"Name already exists: {name}")
                        duplicate = True
                        break
                    if party["abbreviation"].upper() == abbreviation.upper():
                        errors.append(f"Abbreviation already exists: {abbreviation}")
                        duplicate = True
                        break

                if duplicate:
                    continue

                # Parse color
                try:
                    if color.startswith("#"):
                        color = color[1:]
                    party_color = int(color, 16)
                    if party_color > 0xFFFFFF:
                        raise ValueError("Color too large")
                except (ValueError, TypeError):
                    errors.append(f"Invalid color: {color}")
                    continue

                # Create party
                new_party = {
                    "name": name,
                    "abbreviation": abbreviation,
                    "color": party_color,
                    "created_at": datetime.utcnow(),
                    "is_default": False
                }

                config["parties"].append(new_party)
                created_parties.append(f"{name} ({abbreviation})")

            except Exception as e:
                errors.append(f"Error with {entry}: {str(e)}")

        if created_parties:
            col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"parties": config["parties"]}}
            )

        response = f"✅ Created {len(created_parties)} parties"
        if created_parties:
            response += f":\n• {chr(10).join(created_parties)}"

        if errors:
            response += f"\n\n❌ Errors:\n• {chr(10).join(errors[:5])}"
            if len(errors) > 5:
                response += f"\n• ... and {len(errors) - 5} more errors"

        await interaction.response.send_message(response, ephemeral=True)

    @party_manage_group.command(
        name="remove_all_custom",
        description="Remove all custom parties (keep defaults) (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_all_custom_parties(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        """Remove all non-default parties"""
        col, config = self._get_parties_config(interaction.guild.id)

        custom_parties = [p for p in config["parties"] if not p.get("is_default", False)]

        if not custom_parties:
            await interaction.response.send_message(
                "ℹ️ No custom parties found to remove.",
                ephemeral=True
            )
            return

        if not confirm:
            party_names = [p["name"] for p in custom_parties]
            await interaction.response.send_message(
                f"⚠️ **Warning:** This will remove {len(custom_parties)} custom parties:\n"
                f"• {chr(10).join(party_names[:10])}"
                f"{chr(10) + '• ... and more' if len(party_names) > 10 else ''}\n\n"
                f"To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return

        # Keep only default parties
        config["parties"] = [p for p in config["parties"] if p.get("is_default", False)]

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": config["parties"]}}
        )

        await interaction.response.send_message(
            f"✅ Removed {len(custom_parties)} custom parties. Only default parties remain.",
            ephemeral=True
        )

    @party_manage_group.command(
        name="export",
        description="Export party configuration as text (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_export_parties(
        self,
        interaction: discord.Interaction,
        format_type: str = "csv"
    ):
        """Export party data"""
        col, config = self._get_parties_config(interaction.guild.id)

        if not config["parties"]:
            await interaction.response.send_message(
                "❌ No parties configured.",
                ephemeral=True
            )
            return

        if format_type.lower() == "csv":
            lines = ["name,abbreviation,color,is_default,created_at"]
            for party in config["parties"]:
                created_date = party["created_at"].strftime("%Y-%m-%d") if party.get("created_at") else ""
                lines.append(
                    f"{party['name']},{party['abbreviation']},{party['color']:06X},"
                    f"{party.get('is_default', False)},{created_date}"
                )
            export_text = "\n".join(lines)
        elif format_type.lower() == "bulk":
            # Format for bulk_create_parties command
            lines = []
            for party in config["parties"]:
                lines.append(f"{party['name']}:{party['abbreviation']}:{party['color']:06X}")
            export_text = ",".join(lines)
        else:
            # Text format
            lines = []
            for party in config["parties"]:
                party_type = "Default" if party.get("is_default", False) else "Custom"
                lines.append(
                    f"{party['name']} ({party['abbreviation']}) - "
                    f"#{party['color']:06X} - {party_type}"
                )
            export_text = "\n".join(lines)

        await interaction.response.send_message(
            f"📊 Party Export ({format_type.upper()}):\n```\n{export_text}\n```",
            ephemeral=True
        )

    @party_manage_group.command(
        name="modify_color",
        description="Change the color of multiple parties at once (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_modify_party_color(
        self,
        interaction: discord.Interaction,
        party_name: str,
        new_color: str
    ):
        """Change a party's color"""
        col, config = self._get_parties_config(interaction.guild.id)

        # Find the party
        party_found = None
        for i, party in enumerate(config["parties"]):
            if party["name"].lower() == party_name.lower():
                party_found = i
                break

        if party_found is None:
            await interaction.response.send_message(
                f"❌ Party '{party_name}' not found.",
                ephemeral=True
            )
            return

        # Parse color
        try:
            if new_color.startswith("#"):
                new_color = new_color[1:]
            party_color = int(new_color, 16)
            if party_color > 0xFFFFFF:
                raise ValueError("Color too large")
        except (ValueError, TypeError):
            await interaction.response.send_message(
                "❌ Invalid color format. Use hex format like #FF0000 or FF0000.",
                ephemeral=True
            )
            return

        old_color = config["parties"][party_found]["color"]
        config["parties"][party_found]["color"] = party_color

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"parties": config["parties"]}}
        )

        await interaction.response.send_message(
            f"✅ Updated color for **{party_name}**: #{old_color:06X} → #{party_color:06X}",
            ephemeral=True
        )

    @party_manage_group.command(
        name="set_role_ids",
        description="Set Discord role IDs for party validation (Admin only)"
    )
    @app_commands.describe(
        republican_role="Discord role for Republican Party members",
        democrat_role="Discord role for Democratic Party members",
        independent_role="Discord role for Independent members (optional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_party_role_ids(
        self,
        interaction: discord.Interaction,
        republican_role: discord.Role,
        democrat_role: discord.Role,
        independent_role: discord.Role = None
    ):
        """Set Discord role IDs for party validation"""
        col, config = self._get_parties_config(interaction.guild.id)

        # Set role IDs in configuration
        if "role_validation" not in config:
            config["role_validation"] = {}

        config["role_validation"]["Republican Party"] = republican_role.id
        config["role_validation"]["Democratic Party"] = democrat_role.id
        
        if independent_role:
            config["role_validation"]["Independent"] = independent_role.id

        col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"role_validation": config["role_validation"]}}
        )

        embed = discord.Embed(
            title="✅ Party Role IDs Configured",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🔴 Republican Party",
            value=f"{republican_role.mention} (ID: {republican_role.id})",
            inline=False
        )

        embed.add_field(
            name="🔵 Democratic Party", 
            value=f"{democrat_role.mention} (ID: {democrat_role.id})",
            inline=False
        )

        if independent_role:
            embed.add_field(
                name="🟣 Independent",
                value=f"{independent_role.mention} (ID: {independent_role.id})",
                inline=False
            )

        embed.add_field(
            name="ℹ️ Note",
            value="Users will now be validated against these roles when signing up for positions with the corresponding parties.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @party_manage_group.command(
        name="view_role_config",
        description="View current party role ID configuration (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view_party_role_config(self, interaction: discord.Interaction):
        """View current party role ID configuration"""
        col, config = self._get_parties_config(interaction.guild.id)

        role_validation = config.get("role_validation", {})

        if not role_validation:
            await interaction.response.send_message(
                "❌ No party role IDs configured yet. Use `/party manage set_role_ids` to set them up.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎭 Party Role ID Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        for party_name, role_id in role_validation.items():
            role = interaction.guild.get_role(role_id)
            if role:
                embed.add_field(
                    name=party_name,
                    value=f"{role.mention} (ID: {role_id})",
                    inline=False
                )
            else:
                embed.add_field(
                    name=party_name,
                    value=f"❌ Role not found (ID: {role_id})",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def validate_user_party_role(self, user: discord.Member, party_name: str, guild_id: int) -> tuple[bool, str]:
        """Validate if user has the correct role for the specified party"""
        col, config = self._get_parties_config(guild_id)
        role_validation = config.get("role_validation", {})

        # If no role validation configured, allow all
        if not role_validation:
            return True, ""

        # Check if party requires role validation
        if party_name not in role_validation:
            return True, ""

        required_role_id = role_validation[party_name]
        required_role = user.guild.get_role(required_role_id)

        if not required_role:
            return False, f"Party role configuration error: Role ID {required_role_id} not found"

        # Check if user has the required role
        if required_role not in user.roles:
            return False, f"You must have the {required_role.name} role to run as {party_name}"

        return True, ""

async def setup(bot):
    await bot.add_cog(PartyManagement(bot))