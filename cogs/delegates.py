
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional

class Delegates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.delegate_check_loop.start()
        print("Delegates cog loaded successfully")
        
        # Primary schedule data from your file
        self.dnc_schedule = [
            {"order": 1, "month": 8, "day": 3, "state": "New Hampshire", "party": "Democrats", "delegates": 33},
            {"order": 2, "month": 8, "day": 3, "state": "South Carolina", "party": "Democrats", "delegates": 55},
            {"order": 3, "month": 8, "day": 4, "state": "Nevada", "party": "Democrats", "delegates": 36},
            {"order": 4, "month": 8, "day": 12, "state": "Michigan", "party": "Democrats", "delegates": 117},
            {"order": 5, "month": 9, "day": 5, "state": "Alabama", "party": "Democrats", "delegates": 52},
            {"order": 6, "month": 9, "day": 5, "state": "Samoa", "party": "Democrats", "delegates": 6},
            {"order": 7, "month": 9, "day": 5, "state": "Arkansas", "party": "Democrats", "delegates": 31},
            {"order": 8, "month": 9, "day": 5, "state": "California", "party": "Democrats", "delegates": 424},
            {"order": 9, "month": 9, "day": 5, "state": "Colorado", "party": "Democrats", "delegates": 72},
            {"order": 10, "month": 9, "day": 5, "state": "Iowa", "party": "Democrats", "delegates": 40},
            {"order": 11, "month": 9, "day": 5, "state": "Maine", "party": "Democrats", "delegates": 24},
            {"order": 12, "month": 9, "day": 5, "state": "Massachusetts", "party": "Democrats", "delegates": 92},
            {"order": 13, "month": 9, "day": 5, "state": "Minnesota", "party": "Democrats", "delegates": 75},
            {"order": 14, "month": 9, "day": 5, "state": "North Carolina", "party": "Democrats", "delegates": 116},
            {"order": 15, "month": 9, "day": 5, "state": "Oklahoma", "party": "Democrats", "delegates": 36},
            {"order": 16, "month": 9, "day": 5, "state": "Tennessee", "party": "Democrats", "delegates": 63},
            {"order": 17, "month": 9, "day": 5, "state": "Texas", "party": "Democrats", "delegates": 244},
            {"order": 18, "month": 9, "day": 5, "state": "Utah", "party": "Democrats", "delegates": 30},
            {"order": 19, "month": 9, "day": 5, "state": "Vermont", "party": "Democrats", "delegates": 16},
            {"order": 20, "month": 9, "day": 5, "state": "Virginia", "party": "Democrats", "delegates": 99},
            {"order": 21, "month": 9, "day": 6, "state": "Hawaii", "party": "Democrats", "delegates": 22},
            {"order": 22, "month": 9, "day": 12, "state": "Georgia", "party": "Democrats", "delegates": 108},
            {"order": 23, "month": 9, "day": 13, "state": "Mississippi", "party": "Democrats", "delegates": 35},
            {"order": 24, "month": 9, "day": 14, "state": "Marianas", "party": "Democrats", "delegates": 6},
            {"order": 25, "month": 9, "day": 15, "state": "Washington", "party": "Democrats", "delegates": 92},
            {"order": 26, "month": 9, "day": 16, "state": "Delaware", "party": "Democrats", "delegates": 19},
            {"order": 27, "month": 9, "day": 17, "state": "Florida", "party": "Democrats", "delegates": 224},
            {"order": 28, "month": 9, "day": 18, "state": "Arizona", "party": "Democrats", "delegates": 72},
            {"order": 29, "month": 9, "day": 19, "state": "Illinois", "party": "Democrats", "delegates": 147},
            {"order": 30, "month": 9, "day": 20, "state": "Kansas", "party": "Democrats", "delegates": 33},
            {"order": 31, "month": 9, "day": 21, "state": "Ohio", "party": "Democrats", "delegates": 127},
            {"order": 32, "month": 9, "day": 22, "state": "Louisiana", "party": "Democrats", "delegates": 48},
            {"order": 33, "month": 9, "day": 23, "state": "Missouri", "party": "Democrats", "delegates": 64},
            {"order": 34, "month": 9, "day": 24, "state": "North Dakota", "party": "Democrats", "delegates": 13},
            {"order": 35, "month": 9, "day": 25, "state": "Connecticut", "party": "Democrats", "delegates": 60},
            {"order": 36, "month": 9, "day": 26, "state": "New York", "party": "Democrats", "delegates": 268},
            {"order": 37, "month": 9, "day": 27, "state": "Rhode Island", "party": "Democrats", "delegates": 26},
            {"order": 38, "month": 9, "day": 28, "state": "Wisconsin", "party": "Democrats", "delegates": 82},
            {"order": 39, "month": 9, "day": 29, "state": "Alaska", "party": "Democrats", "delegates": 15},
            {"order": 40, "month": 9, "day": 30, "state": "Wyoming", "party": "Democrats", "delegates": 13},
            {"order": 41, "month": 10, "day": 3, "state": "Pennsylvania", "party": "Democrats", "delegates": 159},
            {"order": 42, "month": 10, "day": 5, "state": "Puerto Rico", "party": "Democrats", "delegates": 55},
            {"order": 43, "month": 10, "day": 7, "state": "Indiana", "party": "Democrats", "delegates": 79},
            {"order": 44, "month": 10, "day": 14, "state": "Maryland", "party": "Democrats", "delegates": 95},
            {"order": 45, "month": 10, "day": 15, "state": "Nebraska", "party": "Democrats", "delegates": 29},
            {"order": 46, "month": 10, "day": 16, "state": "West Virginia", "party": "Democrats", "delegates": 20},
            {"order": 47, "month": 10, "day": 21, "state": "Kentucky", "party": "Democrats", "delegates": 53},
            {"order": 48, "month": 10, "day": 22, "state": "Oregon", "party": "Democrats", "delegates": 66},
            {"order": 49, "month": 10, "day": 23, "state": "Idaho", "party": "Democrats", "delegates": 23},
            {"order": 50, "month": 11, "day": 4, "state": "District of Columbia", "party": "Democrats", "delegates": 20},
            {"order": 51, "month": 11, "day": 5, "state": "Montana", "party": "Democrats", "delegates": 20},
            {"order": 52, "month": 11, "day": 6, "state": "New Jersey", "party": "Democrats", "delegates": 126},
            {"order": 53, "month": 11, "day": 7, "state": "New Mexico", "party": "Democrats", "delegates": 34},
            {"order": 54, "month": 11, "day": 8, "state": "South Dakota", "party": "Democrats", "delegates": 16},
            {"order": 55, "month": 11, "day": 9, "state": "Guam", "party": "Democrats", "delegates": 7},
            {"order": 56, "month": 11, "day": 10, "state": "Virgin Islands", "party": "Democrats", "delegates": 7}
        ]
        
        self.gop_schedule = [
            {"order": 1, "month": 8, "day": 3, "state": "Iowa", "party": "Republican", "delegates": 40},
            {"order": 2, "month": 8, "day": 3, "state": "New Hampshire", "party": "Republican", "delegates": 22},
            {"order": 3, "month": 8, "day": 4, "state": "Nevada", "party": "Republican", "delegates": 26},
            {"order": 4, "month": 8, "day": 6, "state": "Virgin Islands", "party": "Republican", "delegates": 9},
            {"order": 5, "month": 8, "day": 13, "state": "South Carolina", "party": "Republican", "delegates": 50},
            {"order": 6, "month": 8, "day": 23, "state": "Michigan", "party": "Republican", "delegates": 55},
            {"order": 7, "month": 9, "day": 2, "state": "Idaho", "party": "Republican", "delegates": 32},
            {"order": 8, "month": 9, "day": 2, "state": "Missouri", "party": "Republican", "delegates": 54},
            {"order": 9, "month": 9, "day": 3, "state": "District of Columbia", "party": "Republican", "delegates": 19},
            {"order": 10, "month": 9, "day": 4, "state": "North Dakota", "party": "Republican", "delegates": 29},
            {"order": 11, "month": 9, "day": 5, "state": "Alabama", "party": "Republican", "delegates": 49},
            {"order": 12, "month": 9, "day": 5, "state": "Alaska", "party": "Republican", "delegates": 28},
            {"order": 13, "month": 9, "day": 5, "state": "Arkansas", "party": "Republican", "delegates": 40},
            {"order": 14, "month": 9, "day": 5, "state": "California", "party": "Republican", "delegates": 169},
            {"order": 15, "month": 9, "day": 5, "state": "Colorado", "party": "Republican", "delegates": 37},
            {"order": 16, "month": 9, "day": 5, "state": "Maine", "party": "Republican", "delegates": 20},
            {"order": 17, "month": 9, "day": 5, "state": "Massachusetts", "party": "Republican", "delegates": 40},
            {"order": 18, "month": 9, "day": 5, "state": "Minnesota", "party": "Republican", "delegates": 39},
            {"order": 19, "month": 9, "day": 5, "state": "North Carolina", "party": "Republican", "delegates": 74},
            {"order": 20, "month": 9, "day": 5, "state": "Oklahoma", "party": "Republican", "delegates": 43},
            {"order": 21, "month": 9, "day": 5, "state": "Tennessee", "party": "Republican", "delegates": 58},
            {"order": 22, "month": 9, "day": 5, "state": "Texas", "party": "Republican", "delegates": 161},
            {"order": 23, "month": 9, "day": 5, "state": "Utah", "party": "Republican", "delegates": 40},
            {"order": 24, "month": 9, "day": 5, "state": "Vermont", "party": "Republican", "delegates": 17},
            {"order": 25, "month": 9, "day": 5, "state": "Virginia", "party": "Republican", "delegates": 49},
            {"order": 26, "month": 9, "day": 8, "state": "Samoa", "party": "Republican", "delegates": 9},
            {"order": 27, "month": 9, "day": 12, "state": "Georgia", "party": "Republican", "delegates": 59},
            {"order": 28, "month": 9, "day": 13, "state": "Hawaii", "party": "Republican", "delegates": 19},
            {"order": 29, "month": 9, "day": 14, "state": "Mississippi", "party": "Republican", "delegates": 40},
            {"order": 30, "month": 9, "day": 15, "state": "Washington", "party": "Republican", "delegates": 43},
            {"order": 31, "month": 9, "day": 16, "state": "Marianas", "party": "Republican", "delegates": 9},
            {"order": 32, "month": 9, "day": 17, "state": "Guam", "party": "Republican", "delegates": 9},
            {"order": 33, "month": 9, "day": 18, "state": "Arizona", "party": "Republican", "delegates": 43},
            {"order": 34, "month": 9, "day": 19, "state": "Florida", "party": "Republican", "delegates": 125},
            {"order": 35, "month": 9, "day": 20, "state": "Illinois", "party": "Republican", "delegates": 64},
            {"order": 36, "month": 9, "day": 21, "state": "Kansas", "party": "Republican", "delegates": 39},
            {"order": 37, "month": 9, "day": 22, "state": "Ohio", "party": "Republican", "delegates": 79},
            {"order": 38, "month": 9, "day": 23, "state": "Louisiana", "party": "Republican", "delegates": 47},
            {"order": 39, "month": 9, "day": 24, "state": "Connecticut", "party": "Republican", "delegates": 28},
            {"order": 40, "month": 9, "day": 25, "state": "New York", "party": "Republican", "delegates": 91},
            {"order": 41, "month": 9, "day": 26, "state": "Rhode Island", "party": "Republican", "delegates": 19},
            {"order": 42, "month": 9, "day": 27, "state": "Wisconsin", "party": "Republican", "delegates": 41},
            {"order": 43, "month": 9, "day": 28, "state": "Wyoming", "party": "Republican", "delegates": 29},
            {"order": 44, "month": 9, "day": 29, "state": "Puerto Rico", "party": "Republican", "delegates": 23},
            {"order": 45, "month": 9, "day": 30, "state": "Pennsylvania", "party": "Republican", "delegates": 67},
            {"order": 46, "month": 10, "day": 7, "state": "Indiana", "party": "Republican", "delegates": 58},
            {"order": 47, "month": 10, "day": 14, "state": "Maryland", "party": "Republican", "delegates": 37},
            {"order": 48, "month": 10, "day": 15, "state": "Nebraska", "party": "Republican", "delegates": 36},
            {"order": 49, "month": 10, "day": 16, "state": "West Virginia", "party": "Republican", "delegates": 32},
            {"order": 50, "month": 10, "day": 10, "state": "Kentucky", "party": "Republican", "delegates": 46},
            {"order": 51, "month": 10, "day": 21, "state": "Oregon", "party": "Republican", "delegates": 31},
            {"order": 52, "month": 11, "day": 4, "state": "Montana", "party": "Republican", "delegates": 31},
            {"order": 53, "month": 11, "day": 5, "state": "New Jersey", "party": "Republican", "delegates": 12},
            {"order": 54, "month": 11, "day": 6, "state": "New Mexico", "party": "Republican", "delegates": 22},
            {"order": 55, "month": 11, "day": 7, "state": "Delaware", "party": "Republican", "delegates": 16},
            {"order": 56, "month": 11, "day": 8, "state": "South Dakota", "party": "Republican", "delegates": 29}
        ]

    def cog_unload(self):
        self.delegate_check_loop.cancel()

    def _get_delegates_config(self, guild_id: int):
        """Get or create delegates configuration for a guild"""
        col = self.bot.db["delegates_config"]
        config = col.find_one({"guild_id": guild_id})
        if not config:
            config = {
                "guild_id": guild_id,
                "called_states": [],  # List of states that have been called
                "delegate_totals": {},  # Candidate delegate totals
                "enabled": True,
                "last_check": datetime.utcnow()
            }
            col.insert_one(config)
        return col, config

    def _get_time_config(self, guild_id: int):
        """Get time configuration"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_presidential_candidates(self, guild_id: int, party: str, year: int):
        """Get presidential candidates for a specific party and year"""
        col = self.bot.db["presidential_signups"]
        config = col.find_one({"guild_id": guild_id})
        
        if not config:
            return []
            
        candidates = []
        for candidate in config.get("candidates", []):
            if (candidate.get("party", "").lower() == party.lower() and 
                candidate.get("year", 0) == year):
                candidates.append(candidate)
                
        return candidates

    def _allocate_delegates(self, candidates: List[dict], total_delegates: int):
        """Allocate delegates proportionally based on candidate points"""
        if not candidates:
            return {}
            
        # Calculate total points
        total_points = sum(candidate.get("points", 0) for candidate in candidates)
        
        if total_points == 0:
            # If no points, allocate equally
            delegates_per_candidate = total_delegates // len(candidates)
            remaining = total_delegates % len(candidates)
            
            allocation = {}
            for i, candidate in enumerate(candidates):
                allocation[candidate["name"]] = delegates_per_candidate
                if i < remaining:
                    allocation[candidate["name"]] += 1
        else:
            # Proportional allocation based on points
            allocation = {}
            allocated_delegates = 0
            
            for candidate in candidates[:-1]:  # All but last candidate
                delegates = round((candidate.get("points", 0) / total_points) * total_delegates)
                allocation[candidate["name"]] = delegates
                allocated_delegates += delegates
            
            # Give remaining delegates to last candidate
            if candidates:
                last_candidate = candidates[-1]
                allocation[last_candidate["name"]] = total_delegates - allocated_delegates
        
        return allocation

    @tasks.loop(minutes=5)
    async def delegate_check_loop(self):
        """Check for states to call every 5 minutes"""
        try:
            # Get all guild configurations
            time_col = self.bot.db["time_configs"]
            time_configs = time_col.find({})
            
            for time_config in time_configs:
                guild_id = time_config["guild_id"]
                guild = self.bot.get_guild(guild_id)
                
                if not guild:
                    continue
                    
                # Calculate current RP time
                current_rp_date = self._calculate_current_rp_time(time_config)
                current_phase = time_config.get("current_phase", "")
                current_year = current_rp_date.year
                
                # Auto-enable delegate system during presidential election years (odd years) and Primary Campaign phase
                delegates_col, delegates_config = self._get_delegates_config(guild_id)
                
                # Check if this is a presidential primary year (odd years) and Primary Campaign phase
                if current_year % 2 == 1 and current_phase == "Primary Campaign":
                    # Auto-enable delegate system if not already enabled
                    if not delegates_config.get("enabled", True):
                        delegates_col.update_one(
                            {"guild_id": guild_id},
                            {"$set": {"enabled": True}}
                        )
                        delegates_config["enabled"] = True
                        print(f"Auto-enabled delegate system for guild {guild_id} (Presidential primary year {current_year})")
                
                # Only check during Primary Campaign phase and if enabled
                if current_phase != "Primary Campaign" or not delegates_config.get("enabled", True):
                    continue
                
                # Only process delegates during presidential election years (odd years)
                if current_year % 2 != 1:
                    continue
                
                # Check both Democratic and Republican schedules
                await self._check_and_call_states(
                    guild, guild_id, current_rp_date, current_year, 
                    self.dnc_schedule, "Democrats", delegates_config, delegates_col
                )
                await self._check_and_call_states(
                    guild, guild_id, current_rp_date, current_year, 
                    self.gop_schedule, "Republican", delegates_config, delegates_col
                )
                
        except Exception as e:
            print(f"Error in delegate check loop: {e}")

    def _calculate_current_rp_time(self, time_config):
        """Calculate current RP time based on time manager configuration"""
        last_update = time_config["last_real_update"]
        current_real_time = datetime.utcnow()
        real_minutes_elapsed = (current_real_time - last_update).total_seconds() / 60

        minutes_per_rp_day = time_config["minutes_per_rp_day"]
        rp_days_elapsed = real_minutes_elapsed / minutes_per_rp_day

        current_rp_date = time_config["current_rp_date"] + timedelta(days=rp_days_elapsed)
        return current_rp_date

    async def _check_and_call_states(self, guild, guild_id: int, current_rp_date, current_year: int, 
                                   schedule: List[dict], party: str, delegates_config: dict, delegates_col):
        """Check if any states should be called and call them"""
        for state_data in schedule:
            state_key = f"{state_data['state']}_{party}_{current_year}"
            
            # Skip if already called
            if state_key in delegates_config.get("called_states", []):
                continue
                
            # Check if date matches
            if (current_rp_date.month == state_data["month"] and 
                current_rp_date.day >= state_data["day"]):
                
                await self._call_state(
                    guild, guild_id, state_data, party, current_year, 
                    delegates_config, delegates_col
                )

    async def _call_state(self, guild, guild_id: int, state_data: dict, party: str, 
                         year: int, delegates_config: dict, delegates_col):
        """Call a state and allocate delegates"""
        state_name = state_data["state"]
        total_delegates = state_data["delegates"]
        state_key = f"{state_name}_{party}_{year}"
        
        # Get presidential candidates for this party
        candidates = self._get_presidential_candidates(guild_id, party, year)
        
        if not candidates:
            # No candidates, skip this state
            delegates_config["called_states"].append(state_key)
            delegates_col.update_one(
                {"guild_id": guild_id},
                {"$set": {"called_states": delegates_config["called_states"]}}
            )
            return
            
        # Allocate delegates
        allocation = self._allocate_delegates(candidates, total_delegates)
        
        # Update delegate totals
        if "delegate_totals" not in delegates_config:
            delegates_config["delegate_totals"] = {}
            
        for candidate_name, delegates in allocation.items():
            if candidate_name not in delegates_config["delegate_totals"]:
                delegates_config["delegate_totals"][candidate_name] = 0
            delegates_config["delegate_totals"][candidate_name] += delegates
        
        # Mark state as called
        delegates_config["called_states"].append(state_key)
        
        # Update database
        delegates_col.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "called_states": delegates_config["called_states"],
                    "delegate_totals": delegates_config["delegate_totals"]
                }
            }
        )
        
        # Send announcement
        await self._send_state_announcement(guild, state_name, party, total_delegates, allocation)

    async def _send_state_announcement(self, guild, state_name: str, party: str, 
                                     total_delegates: int, allocation: dict):
        """Send announcement when a state is called"""
        # Find announcement channel or general channel
        setup_col = self.bot.db["guild_configs"]
        setup_config = setup_col.find_one({"guild_id": guild.id})
        announcement_channel_id = setup_config.get("announcement_channel") if setup_config else None
        
        channel = None
        if announcement_channel_id:
            channel = guild.get_channel(announcement_channel_id)
        if not channel:
            channel = discord.utils.get(guild.channels, name="general") or guild.system_channel
            
        if not channel:
            return
            
        # Create announcement embed
        party_color = discord.Color.blue() if party == "Democrats" else discord.Color.red()
        
        embed = discord.Embed(
            title=f"📢 {state_name} ({party}) Primary Called!",
            description=f"**{total_delegates} delegates** have been allocated!",
            color=party_color,
            timestamp=datetime.utcnow()
        )
        
        # Add allocation results
        results_text = ""
        for candidate_name, delegates in sorted(allocation.items(), key=lambda x: x[1], reverse=True):
            percentage = (delegates / total_delegates) * 100
            results_text += f"**{candidate_name}**: {delegates} delegates ({percentage:.1f}%)\n"
            
        embed.add_field(
            name="🗳️ Delegate Allocation",
            value=results_text,
            inline=False
        )
        
        try:
            await channel.send(embed=embed)
        except:
            pass  # Ignore if can't send message

    @delegate_check_loop.before_loop
    async def before_delegate_check_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="delegate_totals",
        description="Show current delegate totals for presidential candidates"
    )
    async def delegate_totals(
        self, 
        interaction: discord.Interaction,
        party: str = None,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return
            
        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year
        
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        
        delegate_totals = delegates_config.get("delegate_totals", {})
        
        if not delegate_totals:
            await interaction.response.send_message("📊 No delegates have been allocated yet.", ephemeral=True)
            return
            
        # Get all presidential candidates to match with delegate totals
        all_candidates = {}
        for party_name in ["Democrats", "Republican"]:
            if party and party.lower() != party_name.lower():
                continue
                
            candidates = self._get_presidential_candidates(interaction.guild.id, party_name, target_year)
            for candidate in candidates:
                all_candidates[candidate["name"]] = {
                    "party": candidate["party"],
                    "points": candidate.get("points", 0),
                    "delegates": delegate_totals.get(candidate["name"], 0)
                }
        
        if not all_candidates:
            await interaction.response.send_message("📊 No presidential candidates found.", ephemeral=True)
            return
            
        # Group by party
        party_groups = {}
        for candidate_name, data in all_candidates.items():
            candidate_party = data["party"]
            if candidate_party not in party_groups:
                party_groups[candidate_party] = []
            party_groups[candidate_party].append((candidate_name, data))
            
        embed = discord.Embed(
            title=f"🏛️ {target_year} Presidential Delegate Count",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        for party_name, candidates in party_groups.items():
            # Sort by delegate count
            candidates.sort(key=lambda x: x[1]["delegates"], reverse=True)
            
            party_text = ""
            total_party_delegates = sum(data["delegates"] for _, data in candidates)
            
            for candidate_name, data in candidates:
                party_text += f"**{candidate_name}**: {data['delegates']} delegates\n"
                party_text += f"└ Campaign Points: {data['points']:.2f}\n\n"
                
            party_color = "🔵" if party_name == "Democrats" else "🔴"
            embed.add_field(
                name=f"{party_color} {party_name} (Total: {total_party_delegates})",
                value=party_text or "No candidates",
                inline=True
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="upcoming_primaries",
        description="Show upcoming primary elections"
    )
    async def upcoming_primaries(
        self, 
        interaction: discord.Interaction,
        days_ahead: int = 7
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return
            
        current_rp_date = self._calculate_current_rp_time(time_config)
        current_year = current_rp_date.year
        
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        called_states = delegates_config.get("called_states", [])
        
        # Find upcoming primaries
        upcoming = []
        
        for schedule, party in [(self.dnc_schedule, "Democrats"), (self.gop_schedule, "Republican")]:
            for state_data in schedule:
                state_key = f"{state_data['state']}_{party}_{current_year}"
                
                # Skip if already called
                if state_key in called_states:
                    continue
                    
                # Check if within the next X days
                primary_date = datetime(current_year, state_data["month"], state_data["day"])
                days_until = (primary_date - current_rp_date).days
                
                if 0 <= days_until <= days_ahead:
                    upcoming.append({
                        "state": state_data["state"],
                        "party": party,
                        "delegates": state_data["delegates"],
                        "date": primary_date,
                        "days_until": days_until
                    })
        
        if not upcoming:
            await interaction.response.send_message(
                f"📅 No primaries scheduled in the next {days_ahead} days.",
                ephemeral=True
            )
            return
            
        # Sort by date
        upcoming.sort(key=lambda x: x["date"])
        
        embed = discord.Embed(
            title=f"📅 Upcoming Primaries ({days_ahead} days)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📍 Current Date",
            value=current_rp_date.strftime("%B %d, %Y"),
            inline=False
        )
        
        for primary in upcoming:
            party_emoji = "🔵" if primary["party"] == "Democrats" else "🔴"
            date_str = primary["date"].strftime("%B %d")
            days_text = "Today" if primary["days_until"] == 0 else f"in {primary['days_until']} days"
            
            embed.add_field(
                name=f"{party_emoji} {primary['state']} ({primary['party']})",
                value=f"**{date_str}** ({days_text})\n{primary['delegates']} delegates",
                inline=True
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="primary_schedule",
        description="Show the full primary election schedule"
    )
    async def primary_schedule(
        self, 
        interaction: discord.Interaction,
        party: str = None
    ):
        embed = discord.Embed(
            title="🗓️ Primary Election Schedule",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        
        schedules_to_show = []
        if not party or party.lower() in ["democrat", "democrats", "dem", "d"]:
            schedules_to_show.append((self.dnc_schedule, "Democrats", "🔵"))
        if not party or party.lower() in ["republican", "republicans", "gop", "r"]:
            schedules_to_show.append((self.gop_schedule, "Republican", "🔴"))
            
        for schedule, party_name, emoji in schedules_to_show:
            schedule_text = ""
            total_delegates = 0
            
            # Group by month for better organization
            months = {}
            for state_data in schedule[:20]:  # Show first 20 states
                month = state_data["month"]
                if month not in months:
                    months[month] = []
                months[month].append(state_data)
                total_delegates += state_data["delegates"]
                
            for month, states in sorted(months.items()):
                month_name = datetime(2000, month, 1).strftime("%B")
                schedule_text += f"**{month_name}:**\n"
                
                for state_data in sorted(states, key=lambda x: x["day"]):
                    schedule_text += f"  {state_data['day']}: {state_data['state']} ({state_data['delegates']})\n"
                schedule_text += "\n"
                
            embed.add_field(
                name=f"{emoji} {party_name} (Total: {total_delegates}+ delegates)",
                value=schedule_text[:1024],  # Discord field limit
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="force_call_state",
        description="Manually call a state primary (Admin only)"
    )
    async def force_call_state(
        self,
        interaction: discord.Interaction,
        state_name: str,
        party: str,
        year: int = None
    ):
        time_col, time_config = self._get_time_config(interaction.guild.id)
        
        if not time_config:
            await interaction.response.send_message("❌ Time system not configured.", ephemeral=True)
            return
            
        current_year = time_config["current_rp_date"].year
        target_year = year if year else current_year
        
        # Find the state in the schedule
        schedule = self.dnc_schedule if party.lower() in ["democrat", "democrats", "dem"] else self.gop_schedule
        party_name = "Democrats" if party.lower() in ["democrat", "democrats", "dem"] else "Republican"
        
        state_data = None
        for data in schedule:
            if data["state"].lower() == state_name.lower():
                state_data = data
                break
                
        if not state_data:
            await interaction.response.send_message(f"❌ State '{state_name}' not found in {party_name} schedule.", ephemeral=True)
            return
            
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        
        # Call the state
        await self._call_state(
            interaction.guild, interaction.guild.id, state_data, party_name, 
            target_year, delegates_config, delegates_col
        )
        
        await interaction.response.send_message(
            f"✅ Manually called {state_name} ({party_name}) primary!\nCheck announcements for results.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="reset_delegates",
        description="Reset all delegate allocations (Admin only)"
    )
    async def reset_delegates(
        self,
        interaction: discord.Interaction,
        confirm: bool = False
    ):
        if not confirm:
            await interaction.response.send_message(
                "⚠️ **Warning:** This will reset all delegate totals and called states.\n"
                "To confirm, run with `confirm:True`",
                ephemeral=True
            )
            return
            
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "called_states": [],
                    "delegate_totals": {}
                }
            }
        )
        
        await interaction.response.send_message(
            "✅ All delegate data has been reset.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="toggle_delegate_system",
        description="Enable or disable the automatic delegate system (Admin only)"
    )
    async def toggle_delegate_system(self, interaction: discord.Interaction):
        delegates_col, delegates_config = self._get_delegates_config(interaction.guild.id)
        
        current_status = delegates_config.get("enabled", True)
        new_status = not current_status
        
        delegates_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": new_status}}
        )
        
        status_text = "enabled" if new_status else "disabled"
        await interaction.response.send_message(
            f"✅ Delegate system has been **{status_text}**.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Delegates(bot))
