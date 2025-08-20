
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
    """Calculate median percentages for each region"""
    region_medians = {}

    # Use custom regions if provided, otherwise use default REGIONS
    regions_to_use = custom_regions if custom_regions else REGIONS

    for region, states in regions_to_use.items():
        republican_values = []
        democrat_values = []
        other_values = []

        for state in states:
            # Convert to uppercase to match STATE_DATA keys
            state_key = state.upper()
            if state_key in STATE_DATA:
                republican_values.append(STATE_DATA[state_key]["republican"])
                democrat_values.append(STATE_DATA[state_key]["democrat"])
                other_values.append(STATE_DATA[state_key]["other"])

        if republican_values:  # Only calculate if we have data
            region_medians[region] = {
                "republican": statistics.median(republican_values),
                "democrat": statistics.median(democrat_values),
                "other": statistics.median(other_values)
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

    # Calculate median for each seat based on its region
    for region, seats in region_seats.items():
        if seats:
            republican_values = [seat["republican"] for seat in seats]
            democrat_values = [seat["democrat"] for seat in seats]
            other_values = [seat["other"] for seat in seats]

            region_median = {
                "republican": statistics.median(republican_values),
                "democrat": statistics.median(democrat_values),
                "other": statistics.median(other_values)
            }

            # Assign the region median to each seat
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
    """Print formatted region medians"""
    medians = calculate_region_medians()
    print("\n=== REGION MEDIANS ===")
    for region, values in medians.items():
        print(f"\n{region}:")
        print(f"  Republican: {values['republican']:.1f}%")
        print(f"  Democrat: {values['democrat']:.1f}%")
        print(f"  Other: {values['other']:.1f}%")

def print_seat_medians():
    """Print formatted seat medians"""
    medians = calculate_seat_medians()
    print("\n=== SEAT MEDIANS (By Region) ===")

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
    """Print all medians in a formatted way"""
    print_region_medians()
    print_seat_medians()

# Main execution for testing
if __name__ == "__main__":
    print_all_medians()
