import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import random
import math
from typing import Optional, Dict, List
from .presidential_winners import PRESIDENTIAL_STATE_DATA

class Momentum(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.momentum_decay_loop.start()  # Start the decay loop
        print("Momentum cog loaded successfully")

    # Create command groups
    momentum_group = app_commands.Group(name="momentum", description="State momentum commands")
    momentum_admin_group = app_commands.Group(name="admin", description="Momentum admin commands", parent=momentum_group)

    def cog_unload(self):
        self.momentum_decay_loop.cancel()

    def _get_time_config(self, guild_id: int):
        """Get time configuration to check current phase"""
        col = self.bot.db["time_configs"]
        config = col.find_one({"guild_id": guild_id})
        return col, config

    def _get_momentum_config(self, guild_id: int):
        """Get or create momentum configuration"""
        col = self.bot.db["momentum_config"]
        config = col.find_one({"guild_id": guild_id})

        if not config:
            # Initialize momentum system with default settings
            config = {
                "guild_id": guild_id,
                "settings": {
                    "vulnerability_threshold": 3,  # How many people needed to trigger collapse
                    "admin_can_change_lean": True,
                    "momentum_decay_rate": 0.95,  # Daily decay rate
                    "exponential_growth_rate": 1.05,  # Growth multiplier
                    "volatility_threshold": 50.0,  # Momentum level that triggers volatility
                    "auto_collapse_threshold": 100.0,  # Automatic collapse threshold (anti-spam)
                },
                "state_leans": {},  # State political leans (hardcoded values)
                "state_momentum": {},  # Current momentum by state and party
                "regional_momentum": {},  # Regional momentum for senate/governor races
                "momentum_events": []  # Log of momentum changes
            }

            # Initialize state leans based on PRESIDENTIAL_STATE_DATA
            for state_name, state_data in PRESIDENTIAL_STATE_DATA.items():
                republican_pct = state_data.get("republican", 33.3)
                democrat_pct = state_data.get("democrat", 33.3)
                other_pct = state_data.get("other", 33.3)

                # Determine lean based on highest percentage
                if republican_pct > democrat_pct and republican_pct > other_pct:
                    if republican_pct >= 55:
                        lean = {"party": "Republican", "intensity": "Strong"}
                    elif republican_pct >= 45:
                        lean = {"party": "Republican", "intensity": "Moderate"}
                    else:
                        lean = {"party": "Republican", "intensity": "Weak"}
                elif democrat_pct > republican_pct and democrat_pct > other_pct:
                    if democrat_pct >= 55:
                        lean = {"party": "Democrat", "intensity": "Strong"}
                    elif democrat_pct >= 45:
                        lean = {"party": "Democrat", "intensity": "Moderate"}
                    else:
                        lean = {"party": "Democrat", "intensity": "Weak"}
                else:
                    lean = {"party": "Swing", "intensity": "None"}  # Swing state

                config["state_leans"][state_name] = lean

                # Initialize momentum at 0 for all parties (only if not already exists)
                if state_name not in config.get("state_momentum", {}):
                    if "state_momentum" not in config:
                        config["state_momentum"] = {}
                    config["state_momentum"][state_name] = {
                        "Republican": 0.0,
                        "Democrat": 0.0,
                        "Independent": 0.0,
                        "last_updated": datetime.utcnow()
                    }

            # Initialize regional momentum for senate/governor races (only if not already exists)
            from .ideology import REGIONS
            if "regional_momentum" not in config:
                config["regional_momentum"] = {}
            for region_name in REGIONS.keys():
                if region_name not in config["regional_momentum"]:
                    config["regional_momentum"][region_name] = {
                        "Republican": 0.0,
                        "Democrat": 0.0,
                        "Independent": 0.0,
                        "last_updated": datetime.utcnow()
                    }

            col.insert_one(config)

        return col, config

    def _get_intensity_multiplier(self, intensity: str) -> float:
        """Get momentum gain multiplier based on lean intensity"""
        multipliers = {
            "Strong": 1.5,   # California, Texas level
            "Moderate": 1.2, # Most partisan states
            "Weak": 1.0,     # Slight lean states
            "None": 0.8      # True swing states
        }
        return multipliers.get(intensity, 1.0)

    def _apply_exponential_growth(self, current_momentum: float, growth_rate: float = 1.05) -> float:
        """Apply exponential growth to momentum"""
        if current_momentum <= 0:
            return current_momentum

        # Exponential growth: the more momentum you have, the more you gain
        new_momentum = current_momentum * growth_rate

        # Auto-collapse if momentum gets too high (prevents spam abuse)
        auto_collapse_threshold = 100.0  # Automatic collapse at 100 momentum
        if new_momentum >= auto_collapse_threshold:
            # Trigger automatic collapse - reduce by 60-80%
            collapse_percentage = random.uniform(0.6, 0.8)
            new_momentum = new_momentum * (1 - collapse_percentage)

        return new_momentum

    def _check_vulnerability_threshold(self, guild_id: int, state: str, party: str, momentum_config: dict) -> bool:
        """Check if party has high momentum making them vulnerable"""
        settings = momentum_config["settings"]
        volatility_threshold = settings.get("volatility_threshold", 50.0)

        current_momentum = momentum_config["state_momentum"][state][party]
        return current_momentum >= volatility_threshold

    def _add_momentum_event(self, momentum_col, guild_id: int, state: str, party: str, 
                           change: float, reason: str, user_id: int = None):
        """Log a momentum change event"""
        try:
            result = momentum_col.update_one(
                {"guild_id": guild_id},
                {
                    "$push": {
                        "momentum_events": {
                            "timestamp": datetime.utcnow(),
                            "state": state,
                            "party": party,
                            "change": change,
                            "reason": reason,
                            "user_id": user_id
                        }
                    }
                }
            )
            print(f"DEBUG: Momentum event logged - matched: {result.matched_count}, modified: {result.modified_count}")
        except Exception as e:
            print(f"ERROR: Failed to log momentum event: {e}")
            import traceback
            traceback.print_exc()

    def _check_and_apply_auto_collapse(self, momentum_col, guild_id: int, state: str, party: str, current_momentum: float):
        """Check if momentum should auto-collapse and apply it"""
        # Get the auto-collapse threshold from settings
        momentum_col_config, momentum_config = self._get_momentum_config(guild_id)
        auto_collapse_threshold = momentum_config["settings"].get("auto_collapse_threshold", 100.0)

        if current_momentum >= auto_collapse_threshold:
            # Calculate collapse amount (60-80% reduction)
            collapse_percentage = random.uniform(0.6, 0.8)
            momentum_loss = current_momentum * collapse_percentage
            new_momentum = current_momentum - momentum_loss

            # Update momentum
            momentum_col.update_one(
                {"guild_id": guild_id},
                {
                    "$set": {
                        f"state_momentum.{state}.{party}": new_momentum,
                        f"state_momentum.{state}.last_updated": datetime.utcnow()
                    }
                }
            )

            # Log the auto-collapse event
            self._add_momentum_event(
                momentum_col, guild_id, state, party, 
                -momentum_loss, "Automatic collapse (anti-spam)", None
            )

            return new_momentum, True

        return current_momentum, False

    def _calculate_momentum_effect_on_polling(self, state: str, party: str, momentum_config: dict) -> float:
        """Calculate how momentum affects polling percentages"""
        state_momentum = momentum_config["state_momentum"].get(state, {})
        party_momentum = state_momentum.get(party, 0.0)

        # Convert momentum to polling percentage change
        # Each 10 points of momentum = ~1% polling change
        polling_effect = party_momentum / 10.0

        # Cap the effect to prevent extreme swings
        return max(-15.0, min(15.0, polling_effect))

    def _calculate_momentum_campaign_multiplier(self, state: str, party: str, momentum_config: dict) -> float:
        """Calculate campaign effectiveness multiplier based on momentum"""
        state_momentum = momentum_config["state_momentum"].get(state, {})
        party_momentum = state_momentum.get(party, 0.0)

        # Base multiplier of 1.0 (no change)
        base_multiplier = 1.0

        if party_momentum > 0:
            # Positive momentum increases campaign effectiveness
            # Every 25 points of momentum = +50% effectiveness (max +200% at 100 momentum)
            momentum_bonus = min(party_momentum / 25.0 * 0.5, 2.0)
            return base_multiplier + momentum_bonus
        elif party_momentum < 0:
            # Negative momentum decreases campaign effectiveness
            # Every -25 points of momentum = -25% effectiveness (min -75% at -75 momentum)
            momentum_penalty = max(party_momentum / 25.0 * 0.25, -0.75)
            return base_multiplier + momentum_penalty
        else:
            return base_multiplier

    def _calculate_regional_momentum_effect(self, region: str, party: str, momentum_config: dict) -> float:
        """Calculate regional momentum effect for senate/governor races"""
        regional_momentum = momentum_config.get("regional_momentum", {}).get(region, {})
        party_momentum = regional_momentum.get(party, 0.0)

        # Convert momentum to polling percentage change
        # Each 15 points of momentum = ~1% polling change (weaker than state-level)
        polling_effect = party_momentum / 15.0

        # Cap the effect to prevent extreme swings
        return max(-10.0, min(10.0, polling_effect))

    def _get_region_from_seat_id(self, seat_id: str) -> str:
        """Extract region from seat ID"""
        if not seat_id or "-" not in seat_id:
            return None

        parts = seat_id.split("-")
        if len(parts) >= 2:
            region_code = parts[0] if seat_id.endswith("-GOV") else parts[1]
            region_mapping = {
                "CO": "Columbia", "CA": "Cambridge", "AU": "Austin",
                "SU": "Superior", "HL": "Heartland", "YS": "Yellowstone", "PH": "Phoenix"
            }
            return region_mapping.get(region_code)
        return None

    @tasks.loop(hours=12)  # Run decay every 12 hours
    async def momentum_decay_loop(self):
        """Apply momentum decay across all guilds"""
        try:
            col = self.bot.db["momentum_config"]
            configs = col.find({})

            for config in configs:
                guild_id = config["guild_id"]

                # Check if we're in General Campaign phase
                time_col, time_config = self._get_time_config(guild_id)
                if not time_config or time_config.get("current_phase", "") != "General Campaign":
                    continue  # Skip decay if not in General Campaign

                settings = config["settings"]
                decay_rate = settings.get("momentum_decay_rate", 0.95)

                # Apply decay to all state momentum
                updates = {}
                momentum_changed = False

                for state_name, momentum_data in config["state_momentum"].items():
                    # Skip non-dictionary entries (like 'last_decay' timestamp)
                    if not isinstance(momentum_data, dict):
                        continue
                        
                    for party in ["Republican", "Democrat", "Independent"]:
                        current_momentum = momentum_data.get(party, 0.0)

                        if abs(current_momentum) > 0.1:  # Only decay if momentum is significant
                            # Apply decay - reduce momentum toward zero
                            if current_momentum > 0:
                                new_momentum = current_momentum * decay_rate
                            else:
                                new_momentum = current_momentum * decay_rate

                            # If momentum gets very small, set it to 0
                            if abs(new_momentum) < 0.1:
                                new_momentum = 0.0

                            updates[f"state_momentum.{state_name}.{party}"] = new_momentum
                            momentum_changed = True

                            # Log decay event if significant change
                            if abs(current_momentum - new_momentum) > 0.5:
                                self._add_momentum_event(
                                    col, guild_id, state_name, party,
                                    new_momentum - current_momentum, "Daily decay"
                                )

                # Apply all updates at once
                if updates:
                    updates[f"state_momentum.last_decay"] = datetime.utcnow()
                    col.update_one(
                        {"guild_id": guild_id},
                        {"$set": updates}
                    )

                    print(f"Applied momentum decay for guild {guild_id}")

        except Exception as e:
            print(f"Error in momentum decay loop: {e}")

    @momentum_decay_loop.before_loop
    async def before_momentum_decay_loop(self):
        await self.bot.wait_until_ready()

    @momentum_group.command(
        name="status",
        description="View momentum status for a specific state"
    )
    @app_commands.describe(
        state="U.S. state to check momentum (for presidential races)"
    )
    async def momentum_status(self, interaction: discord.Interaction, state: str):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Momentum tracking is only active during the General Campaign phase.",
                ephemeral=True
            )
            return

        # Validate state
        if not state:
            await interaction.response.send_message(
                "❌ Please provide a state name.",
                ephemeral=True
            )
            return

        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        state_lean = momentum_config["state_leans"].get(state_upper, {"party": "Unknown", "intensity": "None"})
        state_momentum = momentum_config["state_momentum"].get(state_upper, {})

        embed = discord.Embed(
            title=f"🌊 Momentum Status: {state_upper}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Show state lean
        lean_party = state_lean["party"]
        lean_intensity = state_lean["intensity"]

        if lean_party == "Swing":
            lean_color = "🟡"
            lean_text = f"{lean_color} **Swing State** (No inherent lean)"
        else:
            lean_color = "🔴" if lean_party == "Republican" else ("🔵" if lean_party == "Democrat" else "🟢")
            lean_text = f"{lean_color} **{lean_intensity} {lean_party} Lean**"

        embed.add_field(
            name="📊 State Lean",
            value=lean_text,
            inline=True
        )

        # Show current momentum for each party
        momentum_text = ""
        parties = ["Republican", "Democrat", "Independent"]

        print(f"DEBUG: Checking momentum for state {state_upper}")
        print(f"DEBUG: State momentum data: {state_momentum}")

        for party in parties:
            current_momentum = state_momentum.get(party, 0.0)

            # Create momentum bar
            momentum_bar = ""
            if current_momentum > 0:
                bar_length = min(int(current_momentum / 5), 20)  # Max 20 chars
                momentum_bar = "█" * bar_length
            elif current_momentum < 0:
                bar_length = min(int(abs(current_momentum) / 5), 20)
                momentum_bar = "▓" * bar_length
            else:
                momentum_bar = "─"

            # Color coding
            if party == "Republican":
                party_emoji = "🔴"
            elif party == "Democrat":
                party_emoji = "🔵"
            else:
                party_emoji = "🟢"

            # Check vulnerability
            vulnerable = self._check_vulnerability_threshold(interaction.guild.id, state_upper, party, momentum_config)
            vulnerability_indicator = " ⚠️" if vulnerable else ""

            momentum_text += f"{party_emoji} **{party}**{vulnerability_indicator}\n"
            momentum_text += f"{momentum_bar} {current_momentum:+.1f}\n\n"

        embed.add_field(
            name="🌊 Current Momentum",
            value=momentum_text,
            inline=False
        )

        # Show campaign effectiveness multipliers
        campaign_multipliers = ""
        for party in parties:
            multiplier = self._calculate_momentum_campaign_multiplier(state_upper, party, momentum_config)
            if abs(multiplier - 1.0) > 0.05:  # Only show if significantly different from 1.0
                campaign_multipliers += f"**{party}:** {multiplier:.2f}x effectiveness\n"

        if campaign_multipliers:
            embed.add_field(
                name="⚡ Campaign Multipliers",
                value=campaign_multipliers,
                inline=True
            )

        # Show recent momentum events for this state
        recent_events = [
            event for event in momentum_config.get("momentum_events", [])
            if event["state"] == state_upper
        ][-3:]  # Last 3 events

        if recent_events:
            events_text = ""
            for event in recent_events:
                timestamp = event["timestamp"]
                party = event["party"]
                change = event["change"]
                reason = event["reason"]

                sign = "+" if change > 0 else ""
                events_text += f"**{party}:** {sign}{change:.1f} ({reason})\n"

            embed.add_field(
                name="📝 Recent Events",
                value=events_text,
                inline=True
            )

        embed.add_field(
            name="ℹ️ Legend",
            value="⚠️ = Vulnerable to collapse\n█ = Positive momentum\n▓ = Negative momentum",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @momentum_group.command(
        name="trigger_collapse",
        description="Attempt to trigger momentum collapse for a vulnerable party in a state"
    )
    @app_commands.describe(
        state="U.S. state where collapse should occur",
        target_party="Party to target for momentum collapse"
    )
    async def trigger_collapse(self, interaction: discord.Interaction, state: str, target_party: str):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Momentum collapse can only be triggered during the General Campaign phase.",
                ephemeral=True
            )
            return

        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate party
        valid_parties = ["Republican", "Democrat", "Independent"]
        if target_party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Choose from: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        # Check if target party is vulnerable
        if not self._check_vulnerability_threshold(interaction.guild.id, state_upper, target_party, momentum_config):
            current_momentum = momentum_config["state_momentum"][state_upper][target_party]
            threshold = momentum_config["settings"]["volatility_threshold"]
            await interaction.response.send_message(
                f"❌ {target_party} is not vulnerable to collapse in {state_upper}. "
                f"They need {threshold:.1f}+ momentum (current: {current_momentum:.1f}).",
                ephemeral=True
            )
            return

        # Check if user has recently triggered a collapse (prevent spam)
        cooldown_col = self.bot.db["momentum_cooldowns"]
        cooldown_record = cooldown_col.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "action": "trigger_collapse"
        })

        if cooldown_record:
            last_action = cooldown_record["last_action"]
            cooldown_end = last_action + timedelta(hours=6)  # 6 hour cooldown

            if datetime.utcnow() < cooldown_end:
                remaining = cooldown_end - datetime.utcnow()
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before triggering another collapse.",
                    ephemeral=True
                )
                return

        # Calculate collapse magnitude (30-70% of current momentum)
        current_momentum = momentum_config["state_momentum"][state_upper][target_party]
        collapse_percentage = random.uniform(0.3, 0.7)
        momentum_loss = current_momentum * collapse_percentage

        # Apply momentum loss
        new_momentum = current_momentum - momentum_loss

        # Update momentum
        momentum_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    f"state_momentum.{state_upper}.{target_party}": new_momentum,
                    f"state_momentum.{state_upper}.last_updated": datetime.utcnow()
                }
            }
        )

        # Log the event
        self._add_momentum_event(
            momentum_col, interaction.guild.id, state_upper, target_party, 
            -momentum_loss, "Opposition-triggered collapse", interaction.user.id
        )

        # Set cooldown
        cooldown_col.update_one(
            {"guild_id": interaction.guild.id, "user_id": interaction.user.id, "action": "trigger_collapse"},
            {
                "$set": {
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id,
                    "action": "trigger_collapse",
                    "last_action": datetime.utcnow()
                }
            },
            upsert=True
        )

        # Optionally shift state lean slightly toward opposition
        settings = momentum_config["settings"]
        if settings.get("lean_shift_on_collapse", True):
            # Small chance to slightly shift state lean
            if random.random() < 0.3:  # 30% chance
                current_lean = momentum_config["state_leans"][state_upper]
                if current_lean["party"] == target_party and current_lean["intensity"] != "Weak":
                    # Weaken the lean
                    if current_lean["intensity"] == "Strong":
                        new_intensity = "Moderate"
                    elif current_lean["intensity"] == "Moderate":
                        new_intensity = "Weak"
                    else:
                        new_intensity = "None"
                        current_lean["party"] = "Swing"

                    momentum_col.update_one(
                        {"guild_id": interaction.guild.id},
                        {
                            "$set": {
                                f"state_leans.{state_upper}.intensity": new_intensity,
                                f"state_leans.{state_upper}.party": current_lean["party"]
                            }
                        }
                    )

                    lean_shift_text = f"\n🔄 **State lean weakened from {current_lean['intensity']} to {new_intensity}!**"
                else:
                    lean_shift_text = ""
            else:
                lean_shift_text = ""
        else:
            lean_shift_text = ""

        embed = discord.Embed(
            title="💥 Momentum Collapse Triggered!",
            description=f"Opposition campaigning has caused {target_party} momentum to collapse in {state_upper}!",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📉 Collapse Details",
            value=f"**State:** {state_upper}\n"
                  f"**Target Party:** {target_party}\n"
                  f"**Momentum Lost:** -{momentum_loss:.1f}\n"
                  f"**Previous Momentum:** {current_momentum:.1f}\n"
                  f"**New Momentum:** {new_momentum:.1f}",
            inline=True
        )

        embed.add_field(
            name="👤 Triggered By",
            value=interaction.user.mention,
            inline=True
        )

        if lean_shift_text:
            embed.add_field(
                name="🔄 Additional Effects",
                value=lean_shift_text.strip(),
                inline=False
            )

        embed.add_field(
            name="⏰ Cooldown",
            value="You cannot trigger another collapse for 6 hours.",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @momentum_admin_group.command(
        name="add_momentum",
        description="Add momentum to a party in a specific state (Admin only)"
    )
    @app_commands.describe(
        state="U.S. state",
        party="Party to give momentum",
        amount="Amount of momentum to add",
        reason="Reason for momentum change"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_momentum(self, interaction: discord.Interaction, state: str, party: str, amount: float, reason: str = "Admin adjustment"):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate party
        valid_parties = ["Republican", "Democrat", "Independent"]
        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party. Choose from: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        # Update momentum
        current_momentum = momentum_config["state_momentum"][state_upper][party]
        new_momentum = current_momentum + amount

        momentum_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    f"state_momentum.{state_upper}.{party}": new_momentum,
                    f"state_momentum.{state_upper}.last_updated": datetime.utcnow()
                }
            }
        )

        # Log the event
        self._add_momentum_event(
            momentum_col, interaction.guild.id, state_upper, party, 
            amount, reason, interaction.user.id
        )

        embed = discord.Embed(
            title="⚙️ Admin Momentum Adjustment",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Changes",
            value=f"**State:** {state_upper}\n"
                  f"**Party:** {party}\n"
                  f"**Previous:** {current_momentum:.1f}\n"
                  f"**Change:** {amount:+.1f}\n"
                  f"**New Total:** {new_momentum:.1f}",
            inline=True
        )

        embed.add_field(
            name="📝 Details",
            value=f"**Reason:** {reason}\n"
                  f"**Admin:** {interaction.user.mention}",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @momentum_admin_group.command(
        name="set_lean",
        description="Set or change a state's political lean (Admin only)"
    )
    @app_commands.describe(
        state="U.S. state",
        party="Party lean (Republican, Democrat, or Swing)",
        intensity="Intensity of lean (Strong, Moderate, Weak, or None)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_lean(self, interaction: discord.Interaction, state: str, party: str, intensity: str):
        # Validate state
        state_upper = state.upper()
        if state_upper not in PRESIDENTIAL_STATE_DATA:
            await interaction.response.send_message(
                f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                ephemeral=True
            )
            return

        # Validate party
        valid_parties = ["Republican", "Democrat", "Swing"]
        if party not in valid_parties:
            await interaction.response.send_message(
                f"❌ Invalid party lean. Choose from: {', '.join(valid_parties)}",
                ephemeral=True
            )
            return

        # Validate intensity
        valid_intensities = ["Strong", "Moderate", "Weak", "None"]
        if intensity not in valid_intensities:
            await interaction.response.send_message(
                f"❌ Invalid intensity. Choose from: {', '.join(valid_intensities)}",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        # Check if admin can change leans
        settings = momentum_config["settings"]
        if not settings.get("admin_can_change_lean", True):
            await interaction.response.send_message(
                "❌ Lean changes are disabled in this server.",
                ephemeral=True
            )
            return

        # Get current lean
        current_lean = momentum_config["state_leans"].get(state_upper, {"party": "Unknown", "intensity": "None"})

        # Update lean
        new_lean = {"party": party, "intensity": intensity}
        momentum_col.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    f"state_leans.{state_upper}": new_lean
                }
            }
        )

        embed = discord.Embed(
            title="⚙️ State Lean Updated",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Lean Change",
            value=f"**State:** {state_upper}\n"
                  f"**Previous:** {current_lean['intensity']} {current_lean['party']}\n"
                  f"**New:** {intensity} {party}",
            inline=True
        )

        embed.add_field(
            name="👤 Changed By",
            value=interaction.user.mention,
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @momentum_admin_group.command(
        name="settings",
        description="View or modify momentum system settings (Admin only)"
    )
    @app_commands.describe(
        vulnerability_threshold="Number of people needed to trigger collapse",
        momentum_decay_rate="Daily decay rate (0.0-1.0)",
        volatility_threshold="Momentum level that triggers volatility",
        auto_collapse_threshold="Automatic collapse threshold (anti-spam)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def momentum_settings(
        self, 
        interaction: discord.Interaction, 
        vulnerability_threshold: Optional[int] = None,
        momentum_decay_rate: Optional[float] = None,
        volatility_threshold: Optional[float] = None,
        auto_collapse_threshold: Optional[float] = None
    ):
        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)
        settings = momentum_config["settings"]

        # Update settings if provided
        updates = {}
        if vulnerability_threshold is not None:
            if vulnerability_threshold < 1 or vulnerability_threshold > 10:
                await interaction.response.send_message(
                    "❌ Vulnerability threshold must be between 1 and 10.",
                    ephemeral=True
                )
                return
            updates["settings.vulnerability_threshold"] = vulnerability_threshold

        if momentum_decay_rate is not None:
            if momentum_decay_rate < 0.0 or momentum_decay_rate > 1.0:
                await interaction.response.send_message(
                    "❌ Decay rate must be between 0.0 and 1.0.",
                    ephemeral=True
                )
                return
            updates["settings.momentum_decay_rate"] = momentum_decay_rate

        if volatility_threshold is not None:
            if volatility_threshold < 10.0 or volatility_threshold > 200.0:
                await interaction.response.send_message(
                    "❌ Volatility threshold must be between 10.0 and 200.0.",
                    ephemeral=True
                )
                return
            updates["settings.volatility_threshold"] = volatility_threshold

        if auto_collapse_threshold is not None:
            if auto_collapse_threshold < 50.0 or auto_collapse_threshold > 500.0:
                await interaction.response.send_message(
                    "❌ Auto-collapse threshold must be between 50.0 and 500.0.",
                    ephemeral=True
                )
                return
            updates["settings.auto_collapse_threshold"] = auto_collapse_threshold

        if updates:
            momentum_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": updates}
            )

        # Refresh config after updates
        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)
        settings = momentum_config["settings"]

        embed = discord.Embed(
            title="⚙️ Momentum System Settings",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎯 Collapse Settings",
            value=f"**Vulnerability Threshold:** {settings['vulnerability_threshold']} people\n"
                  f"**Volatility Threshold:** {settings['volatility_threshold']:.1f} momentum\n"
                  f"**Auto-Collapse Threshold:** {settings.get('auto_collapse_threshold', 100.0):.1f} momentum",
            inline=True
        )

        embed.add_field(
            name="📈 Growth Settings",
            value=f"**Decay Rate:** {settings['momentum_decay_rate']:.2f}\n"
                  f"**Growth Rate:** {settings['exponential_growth_rate']:.2f}",
            inline=True
        )

        embed.add_field(
            name="🔧 System Settings",
            value=f"**Admin Can Change Lean:** {settings['admin_can_change_lean']}\n"
                  f"**Lean Shift on Collapse:** {settings.get('lean_shift_on_collapse', True)}",
            inline=True
        )

        if updates:
            embed.add_field(
                name="✅ Updated Settings",
                value="\n".join([f"**{key.split('.')[-1]}:** {value}" for key, value in updates.items()]),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @momentum_admin_group.command(
        name="reset",
        description="Reset momentum for all states or a specific state (Admin only)"
    )
    @app_commands.describe(
        state="U.S. state to reset (leave blank to reset all states)",
        party="Specific party to reset (leave blank to reset all parties)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_momentum(self, interaction: discord.Interaction, state: Optional[str] = None, party: Optional[str] = None):
        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        # Validate state if provided
        if state:
            state_upper = state.upper()
            if state_upper not in PRESIDENTIAL_STATE_DATA:
                await interaction.response.send_message(
                    f"❌ Invalid state. Please choose from: {', '.join(sorted(PRESIDENTIAL_STATE_DATA.keys()))}",
                    ephemeral=True
                )
                return
        
        # Validate party if provided
        if party:
            valid_parties = ["Republican", "Democrat", "Independent"]
            if party not in valid_parties:
                await interaction.response.send_message(
                    f"❌ Invalid party. Choose from: {', '.join(valid_parties)}",
                    ephemeral=True
                )
                return

        updates = {}
        reset_summary = []

        if state:
            # Reset specific state
            state_upper = state.upper()
            if party:
                # Reset specific party in specific state
                old_momentum = momentum_config["state_momentum"][state_upper][party]
                updates[f"state_momentum.{state_upper}.{party}"] = 0.0
                reset_summary.append(f"**{state_upper} {party}:** {old_momentum:.1f} → 0.0")
                
                # Log reset event
                self._add_momentum_event(
                    momentum_col, interaction.guild.id, state_upper, party,
                    -old_momentum, "Admin momentum reset", interaction.user.id
                )
            else:
                # Reset all parties in specific state
                for party_name in ["Republican", "Democrat", "Independent"]:
                    old_momentum = momentum_config["state_momentum"][state_upper][party_name]
                    if old_momentum != 0.0:
                        updates[f"state_momentum.{state_upper}.{party_name}"] = 0.0
                        reset_summary.append(f"**{state_upper} {party_name}:** {old_momentum:.1f} → 0.0")
                        
                        # Log reset event
                        self._add_momentum_event(
                            momentum_col, interaction.guild.id, state_upper, party_name,
                            -old_momentum, "Admin momentum reset", interaction.user.id
                        )
        else:
            # Reset all states
            for state_name, momentum_data in momentum_config["state_momentum"].items():
                # Skip non-dictionary entries (like 'last_decay' timestamp)
                if not isinstance(momentum_data, dict):
                    continue
                
                parties_to_reset = [party] if party else ["Republican", "Democrat", "Independent"]
                
                for party_name in parties_to_reset:
                    old_momentum = momentum_data.get(party_name, 0.0)
                    if old_momentum != 0.0:
                        updates[f"state_momentum.{state_name}.{party_name}"] = 0.0
                        if len(reset_summary) < 15:  # Only show first 15 for readability
                            reset_summary.append(f"**{state_name} {party_name}:** {old_momentum:.1f} → 0.0")
                        
                        # Log reset event
                        self._add_momentum_event(
                            momentum_col, interaction.guild.id, state_name, party_name,
                            -old_momentum, "Admin momentum reset", interaction.user.id
                        )

        # Apply all updates
        if updates:
            updates["state_momentum.last_reset"] = datetime.utcnow()
            momentum_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": updates}
            )

        # Create response embed
        embed = discord.Embed(
            title="🔄 Momentum Reset",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        # Determine scope description
        if state and party:
            scope = f"{state.upper()} {party}"
        elif state:
            scope = f"All parties in {state.upper()}"
        elif party:
            scope = f"{party} in all states"
        else:
            scope = "All momentum values"

        embed.add_field(
            name="📊 Reset Scope",
            value=f"**Target:** {scope}\n"
                  f"**Values Reset:** {len([k for k in updates.keys() if 'state_momentum' in k and 'last_reset' not in k])}",
            inline=True
        )

        embed.add_field(
            name="👤 Reset By",
            value=interaction.user.mention,
            inline=True
        )

        if reset_summary:
            summary_text = "\n".join(reset_summary)
            if len([k for k in updates.keys() if 'state_momentum' in k and 'last_reset' not in k]) > 15:
                total_resets = len([k for k in updates.keys() if 'state_momentum' in k and 'last_reset' not in k])
                summary_text += f"\n... and {total_resets - 15} more resets"

            embed.add_field(
                name="📉 Changes Made",
                value=summary_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📉 Changes Made",
                value="No momentum values to reset (all were already at 0.0)",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @momentum_admin_group.command(
        name="trigger_decay",
        description="Manually trigger momentum decay for all states (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def trigger_decay(self, interaction: discord.Interaction):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Momentum decay can only be triggered during the General Campaign phase.",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)
        settings = momentum_config["settings"]
        decay_rate = settings.get("momentum_decay_rate", 0.95)

        # Apply decay to all states
        updates = {}
        decay_summary = []

        for state_name, momentum_data in momentum_config["state_momentum"].items():
            # Skip non-dictionary entries (like 'last_decay' timestamp)
            if not isinstance(momentum_data, dict):
                continue
                
            for party in ["Republican", "Democrat", "Independent"]:
                current_momentum = momentum_data.get(party, 0.0)

                if abs(current_momentum) > 0.1:  # Only decay if momentum is significant
                    # Apply decay
                    if current_momentum > 0:
                        new_momentum = current_momentum * decay_rate
                    else:
                        new_momentum = current_momentum * decay_rate

                    # If momentum gets very small, set it to 0
                    if abs(new_momentum) < 0.1:
                        new_momentum = 0.0

                    change = new_momentum - current_momentum
                    updates[f"state_momentum.{state_name}.{party}"] = new_momentum

                    # Track significant changes for summary
                    if abs(change) > 0.5:
                        decay_summary.append(f"**{state_name} {party}:** {current_momentum:.1f} → {new_momentum:.1f}")

                        # Log decay event
                        self._add_momentum_event(
                            momentum_col, interaction.guild.id, state_name, party,
                            change, "Manual decay trigger", interaction.user.id
                        )

        # Apply all updates
        if updates:
            updates["state_momentum.last_decay"] = datetime.utcnow()
            momentum_col.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": updates}
            )

        embed = discord.Embed(
            title="⚙️ Momentum Decay Applied",
            description=f"Applied {((1-decay_rate)*100):.1f}% decay to all momentum values",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        if decay_summary:
            # Show first 10 significant changes
            summary_text = "\n".join(decay_summary[:10])
            if len(decay_summary) > 10:
                summary_text += f"\n... and {len(decay_summary) - 10} more changes"

            embed.add_field(
                name="📉 Significant Changes",
                value=summary_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📉 Changes",
                value="No significant momentum changes (all values below 0.1)",
                inline=False
            )

        embed.add_field(
            name="⚙️ Settings",
            value=f"**Decay Rate:** {decay_rate:.2f} ({((1-decay_rate)*100):.1f}% reduction)\n"
                  f"**Triggered By:** {interaction.user.mention}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @momentum_group.command(
        name="overview",
        description="View momentum overview for all states"
    )
    async def momentum_overview(self, interaction: discord.Interaction):
        # Check if in General Campaign phase
        time_col, time_config = self._get_time_config(interaction.guild.id)
        if not time_config or time_config.get("current_phase", "") != "General Campaign":
            await interaction.response.send_message(
                "❌ Momentum tracking is only active during the General Campaign phase.",
                ephemeral=True
            )
            return

        momentum_col, momentum_config = self._get_momentum_config(interaction.guild.id)

        embed = discord.Embed(
            title="🌊 National Momentum Overview",
            description="State-by-state momentum summary",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Group states by their strongest momentum
        republican_states = []
        democrat_states = []
        competitive_states = []

        for state_name, momentum_data in momentum_config["state_momentum"].items():
            # Skip non-dictionary entries (like 'last_decay' timestamp)
            if not isinstance(momentum_data, dict):
                continue
                
            rep_momentum = momentum_data.get("Republican", 0.0)
            dem_momentum = momentum_data.get("Democrat", 0.0)
            ind_momentum = momentum_data.get("Independent", 0.0)

            max_momentum = max(rep_momentum, dem_momentum, ind_momentum)

            # Check vulnerability
            vulnerable_parties = []
            for party in ["Republican", "Democrat", "Independent"]:
                if self._check_vulnerability_threshold(interaction.guild.id, state_name, party, momentum_config):
                    vulnerable_parties.append(party[0])  # Just first letter

            vulnerability_indicator = f" ({''.join(vulnerable_parties)}⚠️)" if vulnerable_parties else ""

            if max_momentum < 5.0:
                competitive_states.append(f"{state_name}{vulnerability_indicator}")
            elif rep_momentum == max_momentum:
                republican_states.append(f"{state_name} (+{rep_momentum:.1f}){vulnerability_indicator}")
            elif dem_momentum == max_momentum:
                democrat_states.append(f"{state_name} (+{dem_momentum:.1f}){vulnerability_indicator}")

        if republican_states:
            embed.add_field(
                name="🔴 Republican Momentum",
                value="\n".join(republican_states[:10]) + ("..." if len(republican_states) > 10 else ""),
                inline=True
            )

        if democrat_states:
            embed.add_field(
                name="🔵 Democrat Momentum",
                value="\n".join(democrat_states[:10]) + ("..." if len(democrat_states) > 10 else ""),
                inline=True
            )

        if competitive_states:
            embed.add_field(
                name="⚡ Competitive States",
                value="\n".join(competitive_states[:10]) + ("..." if len(competitive_states) > 10 else ""),
                inline=True
            )

        # Show last decay time
        last_decay = momentum_config["state_momentum"].get("last_decay")
        if last_decay:
            time_since_decay = datetime.utcnow() - last_decay
            hours_since = int(time_since_decay.total_seconds() // 3600)
            decay_text = f"Last decay: {hours_since}h ago"
        else:
            decay_text = "No decay applied yet"

        embed.add_field(
            name="ℹ️ Legend",
            value="Numbers show momentum level\n⚠️ = Party vulnerable to collapse\nR/D/I = Republican/Democrat/Independent vulnerable\n" + decay_text,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # Autocomplete functions
    @momentum_status.autocomplete("state")
    async def state_autocomplete_status(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @trigger_collapse.autocomplete("state")
    async def state_autocomplete_collapse(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @trigger_collapse.autocomplete("target_party")
    async def party_autocomplete_collapse(self, interaction: discord.Interaction, current: str):
        parties = ["Republican", "Democrat", "Independent"]
        return [app_commands.Choice(name=party, value=party)
                for party in parties if current.lower() in party.lower()][:25]

    @add_momentum.autocomplete("state")
    async def state_autocomplete_add(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @add_momentum.autocomplete("party")
    async def party_autocomplete_add(self, interaction: discord.Interaction, current: str):
        parties = ["Republican", "Democrat", "Independent"]
        return [app_commands.Choice(name=party, value=party)
                for party in parties if current.lower() in party.lower()][:25]

    @set_lean.autocomplete("state")
    async def state_autocomplete_lean(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @set_lean.autocomplete("party")
    async def party_autocomplete_lean(self, interaction: discord.Interaction, current: str):
        parties = ["Republican", "Democrat", "Swing"]
        return [app_commands.Choice(name=party, value=party)
                for party in parties if current.lower() in party.lower()][:25]

    @set_lean.autocomplete("intensity")
    async def intensity_autocomplete(self, interaction: discord.Interaction, current: str):
        intensities = ["Strong", "Moderate", "Weak", "None"]
        return [app_commands.Choice(name=intensity, value=intensity)
                for intensity in intensities if current.lower() in intensity.lower()][:25]

    @reset_momentum.autocomplete("state")
    async def state_autocomplete_reset(self, interaction: discord.Interaction, current: str):
        states = list(PRESIDENTIAL_STATE_DATA.keys())
        return [app_commands.Choice(name=state, value=state)
                for state in states if current.upper() in state][:25]

    @reset_momentum.autocomplete("party")
    async def party_autocomplete_reset(self, interaction: discord.Interaction, current: str):
        parties = ["Republican", "Democrat", "Independent"]
        return [app_commands.Choice(name=party, value=party)
                for party in parties if current.lower() in party.lower()][:25]

async def setup(bot):
    await bot.add_cog(Momentum(bot))