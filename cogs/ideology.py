import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import statistics
from typing import Dict, List, Tuple

# State ideological data
STATE_DATA = {
    "ALABAMA": {"republican": 57, "democrat": 32, "other": 11, "ideology": "Conservative", "economic": "Nationalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "ALASKA": {"republican": 52, "democrat": 34, "other": 14, "ideology": "Libertarian", "economic": "Capitalist", "social": "Moderate", "government": "Small", "axis": "Right"},
    "ARIZONA": {"republican": 44, "democrat": 42, "other": 14, "ideology": "Libertarian", "economic": "Populist", "social": "Moderate", "government": "Moderate", "axis": "Right"},
    "ARKANSAS": {"republican": 52, "democrat": 39, "other": 9, "ideology": "Right Populist", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "CALIFORNIA": {"republican": 36, "democrat": 56, "other": 8, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "COLORADO": {"republican": 45, "democrat": 47, "other": 8, "ideology": "Liberal", "economic": "Capitalist", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "CONNECTICUT": {"republican": 40, "democrat": 50, "other": 10, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Big", "axis": "Left"},
    "DELAWARE": {"republican": 37, "democrat": 55, "other": 8, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Big", "axis": "Left"},
    "FLORIDA": {"republican": 48, "democrat": 43, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Moderate", "government": "Small", "axis": "Right"},
    "GEORGIA": {"republican": 47, "democrat": 44, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "HAWAII": {"republican": 33, "democrat": 58, "other": 9, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "IDAHO": {"republican": 60, "democrat": 29, "other": 11, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "ILLINOIS": {"republican": 39, "democrat": 52, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Big", "axis": "Left"},
    "INDIANA": {"republican": 53, "democrat": 38, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "IOWA": {"republican": 47, "democrat": 44, "other": 9, "ideology": "Moderate", "economic": "Capitalist", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "KANSAS": {"republican": 54, "democrat": 37, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "KENTUCKY": {"republican": 56, "democrat": 35, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "LOUISIANA": {"republican": 52, "democrat": 39, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "MAINE": {"republican": 42, "democrat": 49, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "MARYLAND": {"republican": 34, "democrat": 57, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Big", "axis": "Left"},
    "MASSACHUSETTS": {"republican": 32, "democrat": 59, "other": 9, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "MICHIGAN": {"republican": 44, "democrat": 47, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "MINNESOTA": {"republican": 42, "democrat": 49, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Moderate", "axis": "Centre"},
    "MISSISSIPPI": {"republican": 55, "democrat": 36, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "MISSOURI": {"republican": 51, "democrat": 40, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "MONTANA": {"republican": 54, "democrat": 37, "other": 9, "ideology": "Libertarian", "economic": "Capitalist", "social": "Moderate", "government": "Small", "axis": "Right"},
    "NEBRASKA": {"republican": 56, "democrat": 35, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "NEVADA": {"republican": 43, "democrat": 46, "other": 11, "ideology": "Liberal", "economic": "Capitalist", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "NEW HAMPSHIRE": {"republican": 46, "democrat": 45, "other": 9, "ideology": "Libertarian", "economic": "Capitalist", "social": "Moderate", "government": "Small", "axis": "Centre"},
    "NEW JERSEY": {"republican": 38, "democrat": 53, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Big", "axis": "Left"},
    "NEW MEXICO": {"republican": 40, "democrat": 48, "other": 12, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Moderate", "axis": "Centre"},
    "NEW YORK": {"republican": 35, "democrat": 56, "other": 9, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "NORTH CAROLINA": {"republican": 47, "democrat": 44, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Moderate", "government": "Small", "axis": "Right"},
    "NORTH DAKOTA": {"republican": 62, "democrat": 29, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "OHIO": {"republican": 46, "democrat": 45, "other": 9, "ideology": "Moderate", "economic": "Populist", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "OKLAHOMA": {"republican": 59, "democrat": 32, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "OREGON": {"republican": 38, "democrat": 51, "other": 11, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Moderate", "axis": "Centre"},
    "PENNSYLVANIA": {"republican": 44, "democrat": 47, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "RHODE ISLAND": {"republican": 33, "democrat": 58, "other": 9, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "SOUTH CAROLINA": {"republican": 51, "democrat": 40, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "SOUTH DAKOTA": {"republican": 58, "democrat": 33, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "TENNESSEE": {"republican": 55, "democrat": 36, "other": 9, "ideology": "Conservative", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "TEXAS": {"republican": 48, "democrat": 43, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "UTAH": {"republican": 58, "democrat": 33, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "VERMONT": {"republican": 35, "democrat": 56, "other": 9, "ideology": "Progressive", "economic": "Socialist", "social": "Progressive", "government": "Big", "axis": "Left"},
    "VIRGINIA": {"republican": 44, "democrat": 47, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "WASHINGTON": {"republican": 37, "democrat": 53, "other": 10, "ideology": "Liberal", "economic": "Moderate", "social": "Progressive", "government": "Moderate", "axis": "Centre"},
    "WEST VIRGINIA": {"republican": 64, "democrat": 27, "other": 9, "ideology": "Right Populist", "economic": "Populist", "social": "Traditionalist", "government": "Small", "axis": "Right"},
    "WISCONSIN": {"republican": 45, "democrat": 46, "other": 9, "ideology": "Liberal", "economic": "Moderate", "social": "Moderate", "government": "Moderate", "axis": "Centre"},
    "WYOMING": {"republican": 66, "democrat": 25, "other": 9, "ideology": "Conservative", "economic": "Capitalist", "social": "Traditionalist", "government": "Small", "axis": "Right"}
}

# Representative seat mappings (State -> Seat ID)
STATE_TO_SEAT = {
    "ALABAMA": "REP-CO-4",
    "ALASKA": "REP-PH-3",
    "ARIZONA": "REP-YS-2",
    "ARKANSAS": "REP-AU-2",
    "CALIFORNIA": "REP-PH-1",
    "COLORADO": "REP-YS-3",
    "CONNECTICUT": "REP-CA-3",
    "DELAWARE": "REP-CA-6",
    "FLORIDA": "REP-CO-6",
    "GEORGIA": "REP-CO-5",
    "HAWAII": "REP-PH-3",
    "IDAHO": "REP-YS-1",
    "ILLINOIS": "REP-SU-4",
    "INDIANA": "REP-SU-1",
    "IOWA": "REP-HL-2",
    "KANSAS": "REP-HL-3",
    "KENTUCKY": "REP-CO-7",
    "LOUISIANA": "REP-AU-2",
    "MAINE": "REP-CA-4",
    "MARYLAND": "REP-CA-6",
    "MASSACHUSETTS": "REP-CA-3",
    "MICHIGAN": "REP-SU-2",
    "MINNESOTA": "REP-HL-1",
    "MISSISSIPPI": "REP-CO-4",
    "MISSOURI": "REP-HL-2",
    "MONTANA": "REP-YS-1",
    "NEBRASKA": "REP-HL-3",
    "NEVADA": "REP-PH-4",
    "NEW HAMPSHIRE": "REP-CA-4",
    "NEW JERSEY": "REP-CA-5",
    "NEW MEXICO": "REP-YS-3",
    "NEW YORK": "REP-CA-2",
    "NORTH CAROLINA": "REP-CO-2",
    "NORTH DAKOTA": "REP-HL-4",
    "OHIO": "REP-SU-1",
    "OKLAHOMA": "REP-AU-1",
    "OREGON": "REP-PH-2",
    "PENNSYLVANIA": "REP-CA-1",
    "RHODE ISLAND": "REP-CA-3",
    "SOUTH CAROLINA": "REP-CO-2",
    "SOUTH DAKOTA": "REP-HL-4",
    "TENNESSEE": "REP-CO-3",
    "TEXAS": "REP-AU-1",
    "UTAH": "REP-YS-2",
    "VERMONT": "REP-CA-4",
    "VIRGINIA": "REP-CO-1",
    "WASHINGTON": "REP-PH-2",
    "WEST VIRGINIA": "REP-CO-1",
    "WISCONSIN": "REP-SU-3",
    "WYOMING": "REP-YS-1"
}

# Regional mappings
REGIONS = {
    "Cambridge": [
        "NEW YORK", "MASSACHUSETTS", "NEW HAMPSHIRE", "CONNECTICUT",
        "RHODE ISLAND", "VERMONT", "MAINE", "PENNSYLVANIA",
        "DELAWARE", "NEW JERSEY", "MARYLAND"
    ],
    "Superior": [
        "OHIO", "ILLINOIS", "MICHIGAN", "WISCONSIN", "INDIANA"
    ],
    "Heartland": [
        "MINNESOTA", "IOWA", "MISSOURI", "NORTH DAKOTA",
        "SOUTH DAKOTA", "NEBRASKA", "KANSAS"
    ],
    "Columbia": [
        "VIRGINIA", "WEST VIRGINIA", "NORTH CAROLINA", "SOUTH CAROLINA",
        "KENTUCKY", "TENNESSEE", "GEORGIA", "FLORIDA",
        "ALABAMA", "MISSISSIPPI"
    ],
    "Austin": [
        "TEXAS", "LOUISIANA", "ARKANSAS", "OKLAHOMA"
    ],
    "Yellowstone": [
        "WYOMING", "MONTANA", "IDAHO", "COLORADO",
        "NEW MEXICO", "UTAH", "ARIZONA"
    ],
    "Phoenix": [
        "CALIFORNIA", "WASHINGTON", "OREGON", "NEVADA",
        "HAWAII", "ALASKA"
    ]
}

def calculate_region_medians(custom_regions=None) -> Dict[str, Dict[str, float]]:
    """Calculate summed percentages for each region, normalized to 100%"""
    region_medians = {}

    # Use custom regions if provided, otherwise use default REGIONS
    regions_to_use = custom_regions if custom_regions else REGIONS

    for region, states in regions_to_use.items():
        total_republican = 0
        total_democrat = 0
        total_other = 0
        valid_states = 0

        for state in states:
            # Convert to uppercase to match STATE_DATA keys
            state_key = state.upper()
            if state_key in STATE_DATA:
                total_republican += STATE_DATA[state_key]["republican"]
                total_democrat += STATE_DATA[state_key]["democrat"]
                total_other += STATE_DATA[state_key]["other"]
                valid_states += 1

        if valid_states > 0:  # Only calculate if we have data
            # Calculate the total sum
            regional_total = total_republican + total_democrat + total_other

            # Normalize to percentages that add up to exactly 100%
            region_medians[region] = {
                "republican": (total_republican / regional_total) * 100,
                "democrat": (total_democrat / regional_total) * 100,
                "other": (total_other / regional_total) * 100
            }

    return region_medians

def calculate_seat_medians() -> Dict[str, Dict[str, float]]:
    """Calculate median percentages for each representative seat by region"""
    seat_medians = {}

    # Group seats by region prefix
    seat_regions = {
        "CA": "Cambridge",
        "SU": "Superior",
        "HL": "Heartland",
        "CO": "Columbia",
        "AU": "Austin",
        "YS": "Yellowstone",
        "PH": "Phoenix"
    }

    # Group seats by their region
    region_seats = {}
    for state, seat_id in STATE_TO_SEAT.items():
        seat_prefix = seat_id.split("-")[1]
        region = seat_regions.get(seat_prefix, "Unknown")

        if region not in region_seats:
            region_seats[region] = []

        if state in STATE_DATA:
            region_seats[region].append({
                "seat_id": seat_id,
                "state": state,
                "republican": STATE_DATA[state]["republican"],
                "democrat": STATE_DATA[state]["democrat"],
                "other": STATE_DATA[state]["other"]
            })

    # Calculate summed percentages for each seat based on its region, normalized to 100%
    for region, seats in region_seats.items():
        if seats:
            total_republican = sum(seat["republican"] for seat in seats)
            total_democrat = sum(seat["democrat"] for seat in seats)
            total_other = sum(seat["other"] for seat in seats)

            # Calculate the total sum
            regional_total = total_republican + total_democrat + total_other

            # Normalize to percentages that add up to exactly 100%
            region_median = {
                "republican": (total_republican / regional_total) * 100,
                "democrat": (total_democrat / regional_total) * 100,
                "other": (total_other / regional_total) * 100
            }

            # Assign the region percentage to each seat
            for seat in seats:
                seat_medians[seat["seat_id"]] = {
                    "state": seat["state"],
                    "region": region,
                    "republican": region_median["republican"],
                    "democrat": region_median["democrat"],
                    "other": region_median["other"]
                }

    return seat_medians

def get_dynamic_regions_from_db(client, guild_id: int) -> Dict[str, list]:
    """Get dynamic region mappings from database if available"""
    try:
        ideology_col = client["election_bot"]["ideology_config"]
        config = ideology_col.find_one({"guild_id": guild_id})
        if config and "dynamic_regions" in config:
            return config["dynamic_regions"]
    except:
        pass
    return None

def get_all_medians(client=None, guild_id=None) -> Dict[str, Dict]:
    """Get all calculated medians in one convenient function"""
    # Try to get dynamic regions from database first
    custom_regions = None
    if client and guild_id:
        custom_regions = get_dynamic_regions_from_db(client, guild_id)

    return {
        "regions": calculate_region_medians(custom_regions),
        "seats": calculate_seat_medians()
    }

def print_region_medians():
    """Print formatted region percentages"""
    medians = calculate_region_medians()
    print("\n=== REGION PERCENTAGES (Summed & Normalized) ===")
    for region, values in medians.items():
        print(f"\n{region}:")
        print(f"  Republican: {values['republican']:.1f}%")
        print(f"  Democrat: {values['democrat']:.1f}%")
        print(f"  Other: {values['other']:.1f}%")

def print_seat_medians():
    """Print formatted seat percentages"""
    medians = calculate_seat_medians()
    print("\n=== SEAT PERCENTAGES (By Region, Summed & Normalized) ===")

    # Group by region for better display
    by_region = {}
    for seat_id, data in medians.items():
        region = data["region"]
        if region not in by_region:
            by_region[region] = []
        by_region[region].append((seat_id, data))

    for region, seats in by_region.items():
        print(f"\n{region} Region:")
        for seat_id, data in seats:
            print(f"  {seat_id} ({data['state']}):")
            print(f"    Republican: {data['republican']:.1f}%")
            print(f"    Democrat: {data['democrat']:.1f}%")
            print(f"    Other: {data['other']:.1f}%")

def print_all_medians():
    """Print all percentages in a formatted way"""
    print_region_medians()
    print_seat_medians()

class IdeologyManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Ideology Management cog loaded successfully")

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
        name="admin_add_ideology_option",
        description="Add a new ideology option by updating a state in STATE_DATA (Admin only)"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    @app_commands.describe(
        state_name="The state to update with the new ideology option",
        category="The ideology category to update",
        new_value="The new ideology value to set"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_add_ideology_option(
        self,
        interaction: discord.Interaction,
        state_name: str,
        category: str,
        new_value: str
    ):
        """Add new ideology options by updating a state"""
        state_name = state_name.upper()
        category = category.lower()
        valid_categories = ["ideology", "economic", "social", "government", "axis"]

        if category not in valid_categories:
            await interaction.response.send_message(
                f"❌ Invalid category '{category}'. \n\n**Valid options:** {', '.join(valid_categories)}\n\n"
                f"Please type one of the categories exactly as shown.",
                ephemeral=True
            )
            return

        if state_name not in STATE_DATA:
            await interaction.response.send_message(
                f"❌ State '{state_name}' not found in STATE_DATA.\nAvailable states: {', '.join(list(STATE_DATA.keys())[:10])}...",
                ephemeral=True
            )
            return

        # Check if new value already exists
        available_choices = self._get_available_choices()
        current_options = available_choices.get(category, [])

        if new_value in current_options:
            await interaction.response.send_message(
                f"❌ '{new_value}' already exists in {category}.\n"
                f"Current options: {', '.join(current_options)}",
                ephemeral=True
            )
            return

        # Store the modification in database for tracking
        # Assuming self.bot.db provides access to your database (e.g., motor or pymongo)
        # Replace 'ideology_modifications' with your actual collection name
        ideology_col = self.bot.db["ideology_modifications"]

        old_value = STATE_DATA[state_name][category]

        modification = {
            "guild_id": interaction.guild.id,
            "action": "add_ideology_option",
            "state_name": state_name,
            "category": category,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.utcnow(),
            "user_id": interaction.user.id
        }

        ideology_col.insert_one(modification)

        await interaction.response.send_message(
            f"✅ **Note:** This would add '{new_value}' to the {category} category by updating {state_name}.\n\n"
            f"**Current {state_name} {category}:** {old_value}\n"
            f"**Would change to:** {new_value}\n\n"
            f"**To implement this change:**\n"
            f"1. Edit `cogs/ideology.py`\n"
            f"2. Find the '{state_name}' entry in STATE_DATA\n"
            f"3. Change `\"{category}\": \"{old_value}\"` to `\"{category}\": \"{new_value}\"`\n\n"
            f"This will make '{new_value}' available as a {category} option for all signups.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_change_ideology_option",
        description="Change an existing ideology option across all states (Admin only)"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    @app_commands.describe(
        category="The ideology category to update",
        old_value="The current ideology value to replace",
        new_value="The new ideology value"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_change_ideology_option(
        self,
        interaction: discord.Interaction,
        category: str,
        old_value: str,
        new_value: str
    ):
        """Change an ideology option across all states that use it"""
        category = category.lower()
        valid_categories = ["ideology", "economic", "social", "government", "axis"]

        if category not in valid_categories:
            await interaction.response.send_message(
                f"❌ Invalid category '{category}'. \n\n**Valid options:** {', '.join(valid_categories)}\n\n"
                f"Please type one of the categories exactly as shown.",
                ephemeral=True
            )
            return

        # Check if old value exists
        available_choices = self._get_available_choices()
        current_options = available_choices.get(category, [])

        if old_value not in current_options:
            await interaction.response.send_message(
                f"❌ '{old_value}' not found in {category}.\n"
                f"Available options: {', '.join(current_options)}",
                ephemeral=True
            )
            return

        if new_value in current_options:
            await interaction.response.send_message(
                f"❌ '{new_value}' already exists in {category}.",
                ephemeral=True
            )
            return

        # Find all states using this value
        affected_states = []
        for state_name, state_data in STATE_DATA.items():
            if state_data.get(category) == old_value:
                affected_states.append(state_name)

        if not affected_states:
            await interaction.response.send_message(
                f"❌ No states found using '{old_value}' in {category}.",
                ephemeral=True
            )
            return

        # Store the modification in database for tracking
        ideology_col = self.bot.db["ideology_modifications"]

        modification = {
            "guild_id": interaction.guild.id,
            "action": "change_ideology_option",
            "category": category,
            "old_value": old_value,
            "new_value": new_value,
            "affected_states": affected_states,
            "timestamp": datetime.utcnow(),
            "user_id": interaction.user.id
        }

        ideology_col.insert_one(modification)

        await interaction.response.send_message(
            f"✅ **Note:** This would change '{old_value}' to '{new_value}' in the {category} category.\n\n"
            f"**Affected states ({len(affected_states)}):** {', '.join(affected_states[:10])}"
            f"{'...' if len(affected_states) > 10 else ''}\n\n"
            f"**To implement this change:**\n"
            f"1. Edit `cogs/ideology.py`\n"
            f"2. Find all instances of `\"{category}\": \"{old_value}\"` in STATE_DATA\n"
            f"3. Replace them with `\"{category}\": \"{new_value}\"`\n\n"
            f"This will update the {category} option globally across all affected states.",
            ephemeral=True
        )

    @app_commands.command(
        name="admin_remove_ideology_option",
        description="Remove an ideology option by reassigning all states using it (Admin only)"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    @app_commands.describe(
        category="The ideology category to update",
        value_to_remove="The ideology value to remove",
        replacement_value="The ideology value to replace it with"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_remove_ideology_option(
        self,
        interaction: discord.Interaction,
        category: str,
        value_to_remove: str,
        replacement_value: str
    ):
        """Remove an ideology option by replacing it with another"""
        category = category.lower()
        valid_categories = ["ideology", "economic", "social", "government", "axis"]

        if category not in valid_categories:
            await interaction.response.send_message(
                f"❌ Invalid category '{category}'. \n\n**Valid options:** {', '.join(valid_categories)}\n\n"
                f"Please type one of the categories exactly as shown.",
                ephemeral=True
            )
            return

        # Check if values exist
        available_choices = self._get_available_choices()
        current_options = available_choices.get(category, [])

        if value_to_remove not in current_options:
            await interaction.response.send_message(
                f"❌ '{value_to_remove}' not found in {category}.\n"
                f"Available options: {', '.join(current_options)}",
                ephemeral=True
            )
            return

        if replacement_value not in current_options:
            await interaction.response.send_message(
                f"❌ Replacement value '{replacement_value}' not found in {category}.\n"
                f"Available options: {', '.join(current_options)}",
                ephemeral=True
            )
            return

        # Find all states using this value
        affected_states = []
        for state_name, state_data in STATE_DATA.items():
            if state_data.get(category) == value_to_remove:
                affected_states.append(state_name)

        if not affected_states:
            await interaction.response.send_message(
                f"❌ No states found using '{value_to_remove}' in {category}. Option may already be unused.",
                ephemeral=True
            )
            return

        # Store the modification in database for tracking
        ideology_col = self.bot.db["ideology_modifications"]

        modification = {
            "guild_id": interaction.guild.id,
            "action": "remove_ideology_option",
            "category": category,
            "removed_value": value_to_remove,
            "replacement_value": replacement_value,
            "affected_states": affected_states,
            "timestamp": datetime.utcnow(),
            "user_id": interaction.user.id
        }

        ideology_col.insert_one(modification)

        await interaction.response.send_message(
            f"✅ **Note:** This would remove '{value_to_remove}' from the {category} category.\n\n"
            f"**Affected states ({len(affected_states)}):** {', '.join(affected_states[:10])}"
            f"{'...' if len(affected_states) > 10 else ''}\n"
            f"**Replacement value:** {replacement_value}\n\n"
            f"**To implement this change:**\n"
            f"1. Edit `cogs/ideology.py`\n"
            f"2. Find all instances of `\"{category}\": \"{value_to_remove}\"` in STATE_DATA\n"
            f"3. Replace them with `\"{category}\": \"{replacement_value}\"`\n\n"
            f"After this change, '{value_to_remove}' will no longer be available as a {category} option.",
            ephemeral=True
        )

    @app_commands.command(
        name="show_ideology_options",
        description="Show all available ideology options"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    async def show_ideology_options(self, interaction: discord.Interaction):
        """Show all available ideology choices"""
        choices = self._get_available_choices()

        embed = discord.Embed(
            title="🎯 Available Ideology Options",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        for category, options in choices.items():
            embed.add_field(
                name=f"📋 {category.title()}",
                value=", ".join(options),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="admin_view_state_ideology",
        description="View ideology data for a specific state (Admin only)"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    @app_commands.describe(
        state_name="The state name to view (optional - shows all if not specified)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_state_ideology(
        self,
        interaction: discord.Interaction,
        state_name: str = None
    ):
        """View ideology data for a specific state or all states"""
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
                title=f"📊 Ideology Data: {state_name}",
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
        name="admin_view_ideology_mod_log",
        description="View log of ideology modifications made (Admin only)"
    )
    @app_commands.guilds(discord.Object(id=1407527193470439565))
    @app_commands.describe(
        limit="Number of recent modifications to show (max 25)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_view_ideology_mod_log(
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

            if mod["action"] == "add_ideology_option":
                value = f"**Added option:** {mod['new_value']}\n"
                value += f"**Category:** {mod['category']}\n"
                value += f"**Via state:** {mod['state_name']}\n"
                value += f"**By:** {user_name} on {timestamp}"
            elif mod["action"] == "change_ideology_option":
                value = f"**Changed:** {mod['old_value']} → {mod['new_value']}\n"
                value += f"**Category:** {mod['category']}\n"
                value += f"**States affected:** {len(mod['affected_states'])}\n"
                value += f"**By:** {user_name} on {timestamp}"
            elif mod["action"] == "remove_ideology_option":
                value = f"**Removed:** {mod['removed_value']}\n"
                value += f"**Category:** {mod['category']}\n"
                value += f"**Replaced with:** {mod['replacement_value']}\n"
                value += f"**States affected:** {len(mod['affected_states'])}\n"
                value += f"**By:** {user_name} on {timestamp}"
            else:
                value = f"**Action:** {mod['action']}\n**By:** {user_name} on {timestamp}"

            embed.add_field(
                name=f"🔄 {mod['action'].replace('_', ' ').title()}",
                value=value,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Autocomplete functions for admin commands
    @admin_add_ideology_option.autocomplete("state_name")
    async def state_name_autocomplete(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @admin_add_ideology_option.autocomplete("category")
    async def category_autocomplete(self, interaction: discord.Interaction, current: str):
        categories = ["ideology", "economic", "social", "government", "axis"]
        return [app_commands.Choice(name=cat, value=cat)
                for cat in categories if current.lower() in cat][:25]

    @admin_change_ideology_option.autocomplete("category")
    async def change_category_autocomplete(self, interaction: discord.Interaction, current: str):
        categories = ["ideology", "economic", "social", "government", "axis"]
        return [app_commands.Choice(name=cat, value=cat)
                for cat in categories if current.lower() in cat][:25]

    @admin_change_ideology_option.autocomplete("old_value")
    async def old_value_autocomplete(self, interaction: discord.Interaction, current: str):
        # Get category from current input to show relevant options
        # Note: This requires fetching the category from the interaction or assuming a default
        # For simplicity, we'll get all possible values. A more robust solution would
        # involve parsing the interaction data to get the selected category.
        choices = self._get_available_choices()
        all_values = []
        for category_values in choices.values():
            all_values.extend(category_values)

        return [app_commands.Choice(name=value, value=value)
                for value in set(all_values) if current.lower() in value.lower()][:25]

    @admin_remove_ideology_option.autocomplete("category")
    async def remove_category_autocomplete(self, interaction: discord.Interaction, current: str):
        categories = ["ideology", "economic", "social", "government", "axis"]
        return [app_commands.Choice(name=cat, value=cat)
                for cat in categories if current.lower() in cat][:25]

    @admin_remove_ideology_option.autocomplete("value_to_remove")
    async def value_to_remove_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()
        all_values = []
        for category_values in choices.values():
            all_values.extend(category_values)

        return [app_commands.Choice(name=value, value=value)
                for value in set(all_values) if current.lower() in value.lower()][:25]

    @admin_remove_ideology_option.autocomplete("replacement_value")
    async def replacement_value_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = self._get_available_choices()
        all_values = []
        for category_values in choices.values():
            all_values.extend(category_values)

        return [app_commands.Choice(name=value, value=value)
                for value in set(all_values) if current.lower() in value.lower()][:25]

    @admin_view_state_ideology.autocomplete("state_name")
    async def view_state_name_autocomplete(self, interaction: discord.Interaction, current: str):
        states = list(STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

async def setup(bot):
    await bot.add_cog(IdeologyManagement(bot))