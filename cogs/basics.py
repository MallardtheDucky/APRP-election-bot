from discord.ext import commands
import discord
from discord import app_commands
from discord.ext.commands import BucketType
from discord.ext.commands import Context

# Define the context for type hinting
class CustomContext(Context):
    pass

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
                label="🚨 Special Elections",
                description="Special election commands",
                value="special"
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
        try:
            embed = self.view.get_embed(self.values[0])
            await interaction.response.edit_message(embed=embed, view=self.view)
        except discord.NotFound:
            # If interaction expired, try to send a new message
            await interaction.followup.send("The interaction has expired. Please run the command again.", ephemeral=True)

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
            discord.SelectOption(label="🚨 Special Elections", description="Special election system guide", value="special_elections"),
            discord.SelectOption(label="🎓 Advanced Strategies", description="Complex campaign techniques", value="advanced"),
            discord.SelectOption(label="🔧 Admin Tools", description="Administrative commands guide", value="admin_tools"),
            discord.SelectOption(label="🛠️ Troubleshooting", description="Common issues and solutions", value="troubleshooting")
        ]
        super().__init__(placeholder="Select a handbook section...", options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            embed = self.view.get_handbook_embed(self.values[0])
            await interaction.response.edit_message(embed=embed, view=self.view)
        except discord.NotFound:
            # If interaction expired, try to send a new message
            await interaction.followup.send("The interaction has expired. Please run the command again.", ephemeral=True)

class HandbookView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HandbookDropdown())

    def get_handbook_embed(self, section: str) -> discord.Embed:
        handbook_sections = {
            "getting_started": {
                "title": "📖 Getting Started",
                "content": """**Step 1: Basic Configuration**
1. Use `/setup add_region` to add US states to your server
   - Add key battleground states first: Pennsylvania, Florida, Michigan, Wisconsin
   - Include safe red states: Texas, Alabama, Wyoming  
   - Include safe blue states: California, New York, Massachusetts
   - Add swing states: Arizona, Georgia, North Carolina

2. Use `/setup set_start` to set your election start date
   - Format: YYYY-MM-DD
   - Example: `/setup set_start 2024-01-01`
   - This determines when your election cycle begins

3. Use `/setup set_announcement_channel` for election updates
   - Choose a channel where all major election events will be announced

4. Use `/party admin create` to create custom parties if needed
   - Default parties: Democratic Party (Blue), Republican Party (Red), Independent (Purple)
   - Example: `/party admin create name:"Green Party" abbreviation:"G" color:"00FF00"`

5. Use `/election admin set_seats` to configure election seats
   - Sets up all available offices: Senate, House, Governor, President, VP

**Step 2: Understanding Election Phases**
• **Signup Phase** - Candidates register using `/signup`, `/pres_signup`, `/vp_signup`
• **Primary Campaign** (2-4 weeks RP time) - Campaign within parties, build momentum
• **Primary Voting** (1-3 days RP time) - Automated/admin-controlled voting
• **General Campaign** (4-8 weeks RP time) - Party nominees face off, momentum crucial
• **General Voting** (1-3 days RP time) - Final election, winners determined
• **Governance** - Winners serve terms, setup for next cycle

**Step 3: Time Management**
- Use `/time current_time` to check current election phase
- Real time vs RP time: Admins can set how fast time moves
- Example: `/time set_time_scale 60` means 1 real hour = 1 RP day
- Elections automatically progress through phases

**Essential Commands:**
• `/help commands` - View all available commands
• `/time current_time` - Check current phase and date
• `/signup` - Register as a candidate (during signup phase)
• `/speech` - Give a basic campaign speech (1 hour cooldown)
• `/momentum status` - Check state momentum
• `/demographic_status` - Check demographic progress (presidential candidates)"""
            },
            "election_management": {
                "title": "🗳️ Election Management",
                "content": """**Comprehensive Seat Configuration**

**Senate Seats** (6-year terms)
- 3 senators per state in default configuration
- Staggered elections (different classes expire different years)
- High-profile races that affect national politics

**House Seats** (2-year terms)  
- Multiple districts per state based on population
- All seats up for election every cycle
- More local, district-focused campaigns

**Governor Seats** (4-year terms)
- One per state, significant state-level executive power
- Important for party momentum

**National Offices** (4-year terms)
- President and Vice President
- Highest-profile races, Electoral College simulation

**Election Timing Configuration**
Example Timeline:
- January-March: Signup Phase
- April-June: Primary Campaign
- July: Primary Elections  
- August-October: General Campaign
- November: General Election
- December-January: Transition/Governance

**Use `/time admin set_time_scale` to control pacing:**
- Fast pace: 30 (30 real minutes = 1 RP day)
- Medium pace: 60 (1 real hour = 1 RP day)
- Slow pace: 120 (2 real hours = 1 RP day)

**Candidate Registration Process**

**General Election Signup**
- `/signup` for general elections (Senate, House, Governor)
- Must specify: name, party, seat, region/state
- Each user can run for multiple offices if allowed
- Withdrawals possible with `/withdraw_signup`

**Presidential Campaign Registration**
1. Presidential: `/pres_signup name:"John Smith" party:"Democratic Party" ideology:"Liberal"`
2. Vice Presidential: `/vp_signup presidential_candidate:"John Smith"`
3. Ticket Formation: Presidential candidate must accept VP with `/accept_vp`

**Vote Management**
1. **Automated Voting** (Recommended) - System calculates based on campaign activity
2. **Manual Vote Setting** - `/poll admin bulk_set_votes` for specific outcomes
3. **Hybrid Approach** - Automated with manual adjustments for close races"""
            },
            "campaign_strategies": {
                "title": "🎯 Campaign Strategies (Updated 1-Hour Cooldowns)",
                "content": """**MAJOR UPDATE: Universal 1-Hour Cooldowns**

All campaign actions now have unified 1-hour cooldowns, creating more strategic timing decisions.

**Core Campaign Actions:**

**1. Speeches** (`/speech`)
- Purpose: Build support with ideology alignment bonuses
- Requirements: 700-3000 characters, reply within 5 minutes
- Effect: 1.5-3.0 points + ideology bonuses
- Stamina Cost: 1.5, Cooldown: 1 hour
- Best Used: Swing states, base building

**2. Canvassing** (`/canvassing`)
- Purpose: High-impact regional targeting
- Requirements: 100-300 character message
- Effect: High in targeted regions, momentum multipliers apply
- Stamina Cost: 1, Cooldown: 1 hour
- Best Used: Competitive districts, ground game

**3. Advertisements** (`/ad`)
- Purpose: Wide reach, premium effectiveness
- Requirements: Video upload (25MB), reply within 5 minutes
- Effect: 0.5-1% polling boost
- Stamina Cost: 1.5, Cooldown: 1 hour
- Best Used: Major media markets, final push

**4. Posters** (`/poster`)
- Purpose: Cost-efficient presence building
- Requirements: Image upload (10MB)
- Effect: 0.25-0.5% polling boost
- Stamina Cost: 1, Cooldown: 1 hour
- Best Used: Consistent presence, name recognition

**5. Donor Appeals** (`/donor`)
- Purpose: High-risk, high-reward fundraising
- Requirements: 400-3000 characters, reply within 5 minutes
- Effect: Up to 3% boost, +5 corruption (scandal risk)
- Stamina Cost: 1.5, Cooldown: 1 hour
- Warning: High corruption leads to scandals

**Critical Timing Strategies:**
- **Peak Activity Scheduling**: Use actions during server peak hours
- **Action Cycling**: Rotate between different action types
- **Crisis Response**: Always keep one action available for emergencies
- **Coordination**: Stagger actions with allies to maintain party presence

**Resource Management:**
- General: 100 stamina total, 50/day regeneration
- Presidential: 200 stamina total, 100/day regeneration
- Emergency Reserve: Keep 10-15 stamina for crisis response"""
            },
            "demographics": {
                "title": "👥 Demographics & Targeting (Updated No-Threshold System)",
                "content": """**MAJOR UPDATE: No More Thresholds!**

**Complete Demographic List (20+ Groups)**
• Geographic: Urban Voters, Suburban Voters, Rural Voters
• Religious: Evangelical Christians
• Racial/Ethnic: African American, Latino/Hispanic, Asian American, Native American Voters
• Economic: Blue-Collar Workers, College-Educated Professionals, Wealthy Voters, Low-Income Voters, Tech Workers
• Age: Young Voters (18–29), Senior Citizens (65+)
• Special Interest: Military/Veterans, LGBTQ+ Voters, Immigrants, Environmental Voters, Gun Rights Advocates

**New Multiplier System (No Thresholds)**
- **Strong (0.25x)**: Demographics very influential in that state
- **Moderate (0.10x)**: Average influence  
- **Small (0.05x)**: Limited influence

**Strategic Example:**
100 points for Rural Voters:
• Alabama (Strong): 25 effective points
• Pennsylvania (Moderate): 10 effective points  
• California (Small): 5 effective points

**Major Conflict Pairs:**
- Urban ↔ Rural Voters
- Young ↔ Senior Citizens
- Environmental ↔ Gun Rights Advocates  
- Evangelical Christians ↔ LGBTQ+ Voters
- Blue-Collar ↔ College-Educated Professionals

**New Strategy Focus:**
1. **Efficiency Over Volume**: Target demographics in strong-multiplier states only
2. **Geographic Specialization**: Build overwhelming strength in favorable areas
3. **Conflict Avoidance**: Use different states for conflicting demographics
4. **Continuous Investment**: Every point matters, no stopping points

**Key Commands:**
• `/demographics view_state_demographics` - Research state multipliers
• `/demographic_appeal` - Target specific groups (presidential)
• `/demographic_status` - Track your progress"""
            },
            "momentum": {
                "title": "🌊 Momentum System",
                "content": """**Understanding Political Momentum**
The momentum system simulates how parties gain and lose influence in states based on campaign activity, scandals, and voter sentiment.

**Core Momentum Mechanics**
- Successful campaign actions build momentum
- Momentum multiplies effectiveness of future actions
- High momentum makes everything easier
- Momentum decays over time without activity

**Momentum Vulnerability**
- Parties with high momentum (50+ points) become vulnerable
- Opponents can trigger "momentum collapse" 
- Collapses cause massive momentum loss (30-70%)
- Vulnerable parties have warning indicators (⚠️)

**State Political Leans**
Every state has a baseline political lean that affects momentum:
- **Strong Lean** (1.5x momentum gain): Deep red/blue states
- **Moderate Lean** (1.2x momentum gain): Typical partisan states
- **Weak Lean** (1.0x momentum gain): Light red/blue states  
- **Swing State** (0.8x momentum gain): True purple states

**Examples by Category:**
- **Strong Republican**: Alabama, Wyoming, Idaho
- **Swing States**: Pennsylvania, Michigan, Wisconsin
- **Strong Democratic**: California, Massachusetts, Hawaii

**Building Momentum Strategies**

**1. Fortress Strategy**
- Pick 2-3 states to completely dominate
- Campaign relentlessly in these states
- Build massive momentum reserves

**2. Expansion Strategy**  
- Start with natural strongholds
- Gradually expand to competitive states
- More risky but higher potential reward

**3. Surgical Strategy**
- Focus on specific types of states
- Deep expertise in chosen battlegrounds

**Momentum Collapse System**
- Momentum above 50.0 points creates vulnerability
- Multiple party members can trigger collapses
- 6-hour cooldown between collapse attempts
- Reduces momentum by 30-70% of current total

**Defensive Strategies:**
- Monitor momentum levels carefully
- Build momentum in multiple states to spread risk
- Keep party members ready to trigger collapses on opponents
- Have backup campaign plans ready

**Campaign Effectiveness Multipliers:**
- **Positive Momentum**: Every 25 points = +50% campaign effectiveness (max +200% at 100 momentum)
- **Negative Momentum**: Every -25 points = -25% campaign effectiveness (min -75% at -75 momentum)
- **Base Multiplier**: 1.0x with no momentum

**Strategic Implications:**
- Every 10 points of momentum = ~1% polling shift
- **Momentum multiplies all campaign action effectiveness**
- High momentum makes every action significantly more powerful
- Negative momentum severely handicaps campaign efforts
- Late momentum swings can overcome early deficits
- Timing of momentum building is crucial
- Success breeds more success through multiplier effects"""
            },
            "presidential": {
                "title": "🏛️ Presidential Campaigns",
                "content": """**Presidential Primary System**
Presidential campaigns are the most complex and prestigious elections, featuring unique mechanics and strategic considerations.

**Primary Calendar and Delegate System**
**Early Primary States** (High Influence)
- Iowa, New Hampshire, South Carolina, Nevada traditionally go first
- Early victories create momentum and media attention
- Strong performance here can make or break campaigns

**Super Tuesday** (Mass Delegate Day)
- Multiple large states vote simultaneously  
- California, Texas, New York often included
- Requires significant resource allocation

**Primary Campaign Strategy**
1. **Early State Strategy** - Focus heavily on Iowa and New Hampshire
2. **National Strategy** - Campaign everywhere from the start
3. **Regional Strategy** - Focus on specific geographic regions

**Presidential Action System**
Presidential candidates have enhanced campaign actions:

**1. Presidential Speeches** (`/pres_speech`)
- Effect: Enhanced reach and impact
- Stamina Cost: Variable, Cooldown: 1 hour
- Special Features: Multi-state reach, national media coverage

**2. Presidential Canvassing** (`/pres_canvassing`)
- Effect: State-targeted with momentum bonus
- Stamina Cost: Variable, Cooldown: 1 hour
- Special Features: Builds momentum and demographic points

**3. Presidential Ads** (`/pres_ad`)
- Effect: Very high impact
- Stamina Cost: Variable, Cooldown: 1 hour
- Special Features: Multi-state reach, premium effectiveness

**4. Presidential Posters** (`/pres_poster`)
- Effect: Enhanced distribution
- Stamina Cost: Variable, Cooldown: 1 hour
- Special Features: National distribution, brand building

**5. Presidential Donor Appeals** (`/pres_donor`)
- Effect: Major fundraising, future campaign benefits
- Stamina Cost: Variable, Cooldown: 1 hour

**Vice Presidential Selection Strategy**
**Geographic Balance** - Choose VP from different region
**Demographic Balance** - Balance age, gender, race, religion, background
**Ideological Balance** - Moderate candidate + progressive VP or vice versa
**Electoral Strategy Balance** - Swing state VPs help with crucial battlegrounds

**General Election Strategy**
**Electoral College Simulation:**
- **Safe States Strategy** - Minimal presence to prevent upsets
- **Swing State Focus** - Allocate majority of campaign resources
- **Expansion Strategy** - Target opponent safe states after securing swing states
- **Defensive Strategy** - When behind, focus on preventing opponent momentum

**Presidential Campaign Timeline**
1. **Early Primary Phase** (Months 1-3) - Build name recognition
2. **Primary Campaign Phase** (Months 4-8) - Intensive primary campaigning  
3. **VP Selection Phase** (Month 9) - Vet potential running mates
4. **General Election Phase** (Months 10-12) - Focus on swing states"""
            },
            "party_management": {
                "title": "🎉 Party Management",
                "content": """**Default Party Configuration**

**Democratic Party (Blue)**
- Color: #0099FF (Blue), Abbreviation: D
- Traditional Strongholds: Urban areas, coasts, educated suburbs
- Typical Demographics: Urban voters, college-educated, young voters, minorities
- Advantages: Strong in high-population states

**Republican Party (Red)**
- Color: #FF0000 (Red), Abbreviation: R
- Traditional Strongholds: Rural areas, suburbs, Southern states
- Typical Demographics: Rural voters, gun rights advocates, evangelicals
- Advantages: Geographic distribution, consistent base turnout

**Independent (Purple)**
- Color: #800080 (Purple), Abbreviation: I
- Traditional Strongholds: Varies widely
- Typical Demographics: Suburban voters, moderate professionals
- Advantages: Flexibility, can build unique coalitions

**Additional Default Parties** (Server-dependent)
- Green Party (Green) - Environmental voters, young progressives
- Libertarian Party (Yellow) - Limited government, social liberals

**Custom Party Creation**
Administrators can create custom parties for unique roleplay scenarios:
```
/party admin create name:"Progressive Party" abbreviation:"P" color:"00FF80"
```

**Party Design Considerations**
**Naming Strategy:** Choose names that reflect ideology or region
**Visual Identity:** Choose distinguishable colors, consider color psychology
**Abbreviation System:** Keep short and memorable (1-3 characters)

**Party Strategy and Coalition Building**

**Intra-Party Dynamics**
- **Primary Elections:** Multiple candidates from same party compete
- **Party Unity:** Coordinate campaigns to avoid conflicting messages
- **Faction Management:** Balance moderate and extreme positions

**Inter-Party Strategy**  
- **Opposition Research:** Track opponent party activities
- **Coalition Disruption:** Target opponent's demographic coalitions
- **Alliance Building:** Temporary alliances with minor parties

**Party Management Commands**
- `/party info list` - Shows all available parties
- `/party admin create` - Creates new political parties (Admin only)
- `/party admin edit` - Modifies existing party attributes (Admin only)
- `/party admin remove` - Removes custom parties (Admin only)
- `/party admin bulk_create` - Create multiple parties at once (Admin only)
- `/party admin reset` - Removes all custom parties (Admin only)
- `/party admin export` - Export party configuration for backup (Admin only)
- `/party admin modify_color` - Change the color of multiple parties at once (Admin only)

**Advanced Party Strategies**
**Multi-Party Scenarios:** Coalition government simulation
**Regional Party Systems:** Parties representing specific regions
**Issue-Based Parties:** Single-issue parties for specific causes
**Historical Simulation:** Parties based on historical periods

**Party Brand Management**
- Ensure all party candidates use similar messaging
- Coordinate policy positions and priorities
- Build party infrastructure across multiple election cycles
- Adapt to changing demographics and new issues"""
            },
            "special_elections": {
                "title": "🚨 Special Elections",
                "content": """**Special Election System Overview**
Special elections are called when House seats become vacant outside of regular election cycles. They follow a fast-paced 4-day timeline with unique mechanics.

**Special Election Timeline**
- **Day 1**: Signup Phase (24 hours)
- **Days 2-4**: Campaign Phase (72 hours)
- **End of Day 4**: Results declared

**Special Election Commands**

**User Commands:**
- `/special signup` - Register for an active special election
- `/special speech` - Give campaign speech (1 hour cooldown, 2-4 points)
- `/special poster` - Create campaign posters (1 hour cooldown, 1-3 points)
- `/special ad` - Run video advertisements (1 hour cooldown, 3-6 points)
- `/special calendar` - View election timeline and status
- `/special poll` - Conduct NPC polling with 7% margin of error

**Admin Commands:**
- `/special admin call_election` - Call special election for vacant House seat
- `/special admin end_election` - End active special election
- `/special admin set_winner` - Manually set election winner

**Eligibility and Requirements**
- **Seats Eligible**: Only House seats (REP- or District seats)
- **User Participation**: Anyone can participate, not just registered candidates
- **Target System**: Must specify target candidate for campaign actions

**Special Election Mechanics**

**Signup Phase (24 hours)**
- Use `/special signup candidate_name:"Your Name" party:"Your Party"`
- Multiple users can participate regardless of regular election status
- Get seat information and timeline details

**Campaign Phase (72 hours)**
- All campaign actions have 1-hour cooldowns
- Actions require target candidate specification
- Stamina system: Start with 100, actions cost 15-25 stamina

**Campaign Actions Details**

**1. Special Speech** (`/special speech`)
- Requirements: 700-3000 characters, reply within 5 minutes
- Effect: 2-4 points gained
- Stamina Cost: -20
- Cooldown: 1 hour

**2. Special Poster** (`/special poster`)
- Requirements: Image upload (max 10MB)
- Effect: 1-3 points gained
- Stamina Cost: -15
- Cooldown: 1 hour

**3. Special Ad** (`/special ad`)
- Requirements: Video upload (max 25MB), reply within 5 minutes
- Effect: 3-6 points gained
- Stamina Cost: -25
- Cooldown: 1 hour

**Strategic Considerations**

**Time Management**
- Short 4-day cycle requires aggressive campaigning
- Plan action timing around cooldowns
- Save high-impact actions for peak activity times

**Resource Allocation**
- Limited stamina requires careful planning
- High-point actions (ads) vs. cost-efficient actions (posters)
- Balance frequency vs. impact

**Competition Dynamics**
- Smaller candidate pools create more focused competition
- Every action directly impacts relative standing
- Late campaign surges can overcome early deficits

**Administrative Guidelines**
- Call special elections only for legitimate vacancies
- Monitor for fair play and rule compliance
- Use polling commands to track race dynamics

**Special Election Polling**
- 7% margin of error (higher than regular elections)
- Smaller sample sizes (300-800 voters)
- More volatile results due to shorter campaign period
- Real-time tracking of candidate momentum"""
            },
            "advanced": {
                "title": "🎓 Advanced Strategies",
                "content": """**Coalition Building Mastery**

**The 3-4-2 Rule**
- 3 Core Demographics: Your absolute base (focus heavily)
- 4 Supporting Demographics: Secondary targets (moderate focus)
- 2 Opportunity Demographics: Stretch goals if resources allow

**Example Progressive Coalition**
- Core: Urban Voters, College-Educated Professionals, Young Voters
- Supporting: Environmental Voters, Tech Workers, LGBTQ+ Voters, Immigrant Communities
- Opportunity: Asian American Voters, Low-Income Voters

**Geographic Optimization Matrix**
Create a matrix showing where your core demographics are strongest:
```
State         | Urban | College | Young | Environmental
California    | 0.25  | 0.25    | 0.25  | 0.25
New York      | 0.25  | 0.25    | 0.25  | 0.10
Colorado      | 0.25  | 0.25    | 0.25  | 0.25
```

**Strategic Targeting Priority**
1. States where all core demographics are strong (0.25 multiplier)
2. States where 2-3 core demographics are strong
3. Swing states where at least 1 core demographic is strong
4. Opponent strongholds only if you have overwhelming advantages

**Advanced Momentum Warfare**

**Momentum Cascade Strategy**
Create chain reactions that build momentum across multiple states:
- **Phase 1:** Build moderate momentum (30-40 points) in 5-6 states
- **Phase 2:** Push one strategic state to vulnerability (50+ momentum)
- **Phase 3:** Spread momentum to other states before collapse occurs

**Counter-Momentum Operations**
Track opponent momentum and plan strategic collapses:
- Week 1-2: Identify opponent momentum patterns
- Week 3-4: Position party members for collapse attempts
- Week 5-6: Execute collapses during crucial campaign moments
- Week 7-8: Follow up with own momentum building

**Resource Optimization Strategies**

**Stamina Management Across Multiple Candidates**
- **Stamina Sharing Protocols:** High-stamina candidates support allies
- **Action Specialization:** Assign specific action types to different candidates
- **Crisis Response Capabilities:** Maintain 20% stamina reserve across party

**Psychological Warfare and Narrative Control**

**Expectation Management**
- **Underdog Positioning:** Set low expectations, exceed them for momentum
- **Frontrunner Discipline:** When ahead, avoid major risks and controversies

**Advanced Geographic Strategies**

**Regional Specialization**
- **Rust Belt Strategy:** Blue-collar voters, economic messaging (MI, OH, PA, WI)
- **Sun Belt Strategy:** Suburban growth, education focus (AZ, GA, NC, TX)
- **Mountain West Strategy:** Environmental issues, individual freedom (CO, NV, UT, MT)

**Micro-Targeting Within States**
- **Urban Cores:** Demographics - Urban voters, minorities, young professionals
- **Suburban Rings:** Demographics - Suburban voters, college-educated, families
- **Rural Areas:** Demographics - Rural voters, gun rights advocates, religious voters

**Opposition Research and Counter-Intelligence**

**Information Gathering**
- Track all opponent campaign actions and effectiveness
- Monitor demographic progress and momentum building
- Analyze resource allocation and strategic priorities

**Strategic Counter-Operations**
- Time major announcements to overshadow opponents
- Use momentum collapses to disrupt opponent campaign rhythm
- Counter-program against opponent's demographic targeting

**Late-Campaign Surge Strategies**

**Resource Conservation vs. All-Out Push**
- **Conservation Strategy** (When Ahead): Maintain minimal presence, focus on preventing opponent momentum
- **Surge Strategy** (When Behind): Spend all remaining resources, take calculated risks

**Closing Argument Development**
- Synthesize campaign themes into final message
- Target undecided voters with moderate positions
- Reinforce base support to ensure turnout

**Special Election Integration**
- Use special elections as testing grounds for new strategies
- Build name recognition for future general elections
- Coordinate with general election campaigns for maximum impact"""
            },
            "admin_tools": {
                "title": "🔧 Admin Tools",
                "content": """**Essential Election Administration**

**Election System Architecture**
Before campaigns begin, configure fundamental election infrastructure:

**Seat Configuration** (`/election admin set_seats`)
Consider these factors:
- **Realistic Representation:** Base seats on actual population/server member counts
- **Election Timing Balance:** Senate (6-year), House (2-year), Governor (4-year), President/VP (4-year)

**Example Seat Configuration:**
```
Large States (CA, TX, NY): 6 Senate seats, 8-12 House districts, 1 Governor
Medium States (PA, OH, MI): 3 Senate seats, 4-6 House districts, 1 Governor  
Small States (WY, VT, DE): 3 Senate seats, 1-2 House districts, 1 Governor
```

**Time Scale Management**
**Realistic Pacing Guidelines:**
- Signup Phase: 3-7 real days
- Primary Campaign: 7-14 real days
- Primary Election: 1-3 real days
- General Campaign: 14-21 real days
- General Election: 1-3 real days

**Time Scale Formulas:**
- Active Server: 30-60 minutes per RP day
- Moderate Server: 60-120 minutes per RP day
- Casual Server: 120-240 minutes per RP day

**Advanced Election Management**

**Multi-Cycle Planning**
- **Presidential Election Years** (Every 4 years): All House, 1/3 Senate, Governors, President/VP
- **Midterm Election Years** (2 years after): All House, 1/3 Senate (different class), some Governors
- **Off-Year Elections**: Special elections only, good for party building

**Voting System Management**
**Hybrid Approach** (Recommended):
- Use automated calculations for most races
- Manual intervention for close races (within 5%)
- Administrative judgment for special circumstances

**Vote Calculation Factors:**
- Campaign points accumulated
- Momentum levels in relevant states
- Demographic coalition strength
- State political leans and multipliers
- Random variance for realism

**Monitoring and Balance**

**Campaign Activity Tracking**
- Track campaign actions per candidate
- Monitor stamina usage patterns
- Identify inactive candidates for intervention

**Fairness and Balance Maintenance**
- **Demographic System Balance:** Monitor coalition effectiveness
- **Momentum System Oversight:** Track accumulation rates and collapse frequency
- **State Balance Verification:** Ensure no states are consistently ignored

**Special Election Administration**
- **Call Special Elections:** `/special admin call_election` for vacant House seats
- **Monitor Special Campaigns:** Track 4-day election cycles
- **Manage Special Results:** Use `/special admin set_winner` if needed

**Advanced Administrative Features**

**Crisis Management Tools**
- Reset campaign cooldowns for technical issues: `/admin system reset_campaign_cooldowns`
- Manually adjust momentum for game balance: `/momentum admin add_momentum`
- Resolve disputes between candidates
- Handle rule violations and enforcement

**Data Management and Analysis**
- Export seat configurations for backup: `/election admin export`
- Analyze historical election data
- Track long-term trends and patterns
- Monitor bot performance and response times

**Common Administrative Challenges**
**Low Engagement Issues:** Reduce time scales, create more competitive races, call special elections
**Over-Engagement Issues:** Increase cooldowns, add more complex strategic elements
**System Balance Problems:** Monitor win rates by party and strategy

**Essential Admin Commands:**
- `/election admin set_seats` - Configure all election seats
- `/time admin set_current_time` - Control election timing and phases
- `/time admin set_time_scale` - Set how many real minutes equal one RP day
- `/momentum admin add_momentum` - Adjust state momentum levels
- `/party admin create` - Create custom political parties
- `/poll admin bulk_set_votes` - Set voting results manually
- `/special admin call_election` - Call special elections for vacant House seats
- `/admin system reset_campaign_cooldowns` - Reset user cooldowns"""
            },
            "troubleshooting": {
                "title": "🛠️ Troubleshooting",
                "content": """**Common User Issues and Solutions**

**Command Execution Problems**

**"Command on cooldown" Errors**
- **Cause:** User attempting action before 1-hour cooldown expires
- **Solution:** Wait for cooldown to complete or check remaining time
- **Prevention:** Track cooldowns carefully, all campaign actions now have 1-hour cooldowns
- **Admin Override:** Use `/admin system reset_campaign_cooldowns` if necessary

**Example Resolution Process:**
1. Check remaining cooldown time (usually 1 hour for all actions)
2. Plan next action timing based on cooldown info
3. Use different action types if one is on cooldown
4. Contact admin if cooldown seems incorrect

**"Not in correct phase" Errors**
- **Cause:** Attempting phase-specific actions at wrong time
- **Solution:** Check current phase with `/time current_time`
- **Understanding:** Different actions available in different phases

**Phase-Action Compatibility Guide:**
- **Signup Phase:** `/signup`, `/pres_signup`, `/vp_signup`, `/special signup`
- **Primary Campaign:** All campaign actions, demographic appeals
- **Primary Election:** Voting only, limited campaign actions
- **General Campaign:** Enhanced campaign actions, momentum system
- **General Election:** Voting only, final appeals
- **Governance:** Administrative actions, next cycle preparation
- **Special Elections:** Available anytime for House seats

**Permission and Access Issues**
**"Insufficient permissions" Errors**
- **Cause:** Non-admin attempting admin-only commands
- **Solution:** Contact server administrator for assistance
- **Alternative:** Use equivalent non-admin commands where available

**Registration and Signup Problems**
**"Already signed up" Errors**
- **Solution:** Use `/signup withdraw` first, then re-register
- **Note:** Can run for multiple different offices simultaneously
- **Special Elections:** Separate from regular signups

**"Invalid region/state" Errors**
- **Solution:** Check available regions with `/setup list_regions`
- **Format:** Use exact spelling and capitalization
- **Examples:** "PENNSYLVANIA" not "Pennsylvania"

**Campaign Strategy Troubleshooting**

**Low Campaign Effectiveness Issues**
- **Diagnosis:** Check state demographic multipliers
- **Solution:** Campaign in states where your demographics are strong
- **Tool:** Use `/demographics view_state_demographics` to research
- **Strategy:** Focus on 0.25 multiplier states, avoid 0.05 states

**Example Effectiveness Analysis:**
Target: Rural Voters
- Strong States (0.25): Alabama, Montana, Wyoming
- Moderate States (0.10): Colorado, Pennsylvania
- Weak States (0.05): California, New York
- Action Plan: Campaign for Rural Voters in Alabama/Montana/Wyoming

**Demographic Coalition Problems**
- **Cause:** Targeting conflicting demographic groups
- **Symptoms:** Losing support in demographics you've previously built
- **Prevention:** Plan coalition strategy to avoid major conflicts
- **New System:** No thresholds, focus on building strong coalitions

**Coalition Prevention Strategy:**
1. Map out your core demographic coalition
2. Identify all conflicting demographics for each core group
3. Plan geographic targeting to minimize overlap
4. Focus on states where your demographics have strong multipliers

**Momentum Building Difficulties**
- **Solution:** Increase campaign frequency in target states
- **Strategy:** Build momentum systematically in 2-3 states first
- **Tool:** Use `/momentum status` to track progress

**Momentum Building Best Practices:**
- Week 1-2: Choose 2-3 target states, begin consistent campaigning
- Week 3-4: Build to 30-40 momentum in each target state
- Week 5-6: Expand to 2-3 additional states
- Week 7-8: Maintain momentum, avoid vulnerability thresholds

**Special Election Issues**
- **Short Timeline:** 4-day cycles require aggressive campaigning
- **Stamina Management:** Start with 100, actions cost 15-25
- **Target Requirements:** Must specify target candidate for all actions
- **Solution:** Plan actions around 1-hour cooldowns

**System Performance and Technical Issues**

**Bot Response Problems**
- **Slow Command Response:** Wait for response, avoid spamming commands
- **Failed Command Execution:** Wait and retry command once, screenshot errors
- **Interaction Timeouts:** Re-run commands if interactions expire

**Best Practices for Issue Prevention**

**Strategic Planning**
- Plan campaign strategy before beginning active campaigning
- Research state demographics and momentum systems thoroughly
- Develop contingency plans for various scenarios
- Consider special election opportunities

**Resource Management**
- Track stamina usage and 1-hour cooldown timers carefully
- Maintain reserves for emergency responses
- Plan action timing around server activity patterns
- Coordinate with party members and running mates

**Communication and Coordination**
- Share research and analysis with party members
- Coordinate timing of major campaign actions
- Report issues and problems promptly to admins
- Maintain good sportsmanship and fair play standards

**Updated System Notes**
- All campaign actions now have 1-hour cooldowns
- Demographics have no thresholds - focus on state multipliers
- Special elections available for House seats anytime
- Momentum system more important than ever for effectiveness"""
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
                "content": """`/help` - Show this help menu with options for commands, handbook, or credits
`/commands` - Display all available bot commands (alias for /help commands)"""
            },
            "setup": {
                "title": "🏛️ Setup Commands", 
                "content": """**User Commands:**
`/setup show_config` - Show current election configuration
`/setup list_regions` - List all the US states you've added as regions

**Admin Commands:**
`/setup add_region` - Add a US state (by abbreviation) to this guild's election regions (Admin only)
`/setup remove_region` - Remove a US state from this guild's regions (Admin only)
`/setup set_start` - Set the start date & time for your election (format: YYYY-MM-DD HH:MM) (Admin only)
`/setup set_announcement_channel` - Set the channel for election announcements (Admin only)
`/setup remove_announcement_channel` - Remove the announcement channel setting (Admin only)
`/setup bulk_add_regions` - Add multiple regions at once from a formatted list (Admin only)"""
            },
            "party": {
                "title": "🎉 Party Management Commands",
                "content": """**User Commands:**
`/party info list` - List all available political parties

**Admin Commands:**
`/party admin create` - Create a new political party (Admin only)
`/party admin remove` - Remove a political party (Admin only)
`/party admin edit` - Edit an existing political party (Admin only)
`/party admin reset` - Reset all parties to default (Admin only - DESTRUCTIVE)
`/party admin bulk_create` - Create multiple parties at once (Admin only)
`/party admin remove_all_custom` - Remove all custom parties (keep defaults) (Admin only)
`/party admin export` - Export party configuration as text (Admin only)
`/party admin modify_color` - Change the color of multiple parties at once (Admin only)"""
            },
            "polling": {
                "title": "📊 Polling Commands",
                "content": """**User Commands:**
`/poll candidate` - Conduct an NPC poll for a specific candidate (shows polling with 7% margin of error)
`/poll info state` - Conduct an NPC poll for all parties in a specific state, showing Rep/Dem/Independent support

**Admin Commands:**
`/poll admin bulk_set_votes` - Set vote counts for multiple candidates (Admin only)
`/poll admin set_winner_votes` - Set election winner and vote counts for general elections (Admin only)"""
            },
            "election": {
                "title": "🗳️ Election Management",
                "content": """**User Commands:**
`/election seat view` - View details of a specific election seat
`/election seat list` - List all election seats
`/election seat assign` - Assign a user to an election seat
`/election info phases` - Show current election phase information
`/election info winners` - View election winners

**Admin Commands:**
`/election admin set_seats` - Set up election seats for the guild (Admin only)
`/election admin reset_seats` - Reset all election seats (Admin only)
`/election admin view_seats` - View all configured election seats (Admin only)
`/election admin bulk_add_seats` - Add multiple seats from formatted text (Admin only)
`/election admin fill_vacant_seat` - Fill a vacant seat with a user (Admin only)
`/election seat admin_update` - Update a specific election seat (Admin only)
`/election seat admin_reset_term` - Reset term for a specific seat (Admin only)"""
            },
            "time": {
                "title": "⏰ Time Management",
                "content": """**User Commands:**
`/time current_time` - Show the current RP date and election phase
`/time show_phases` - Show all election phases and their timing

**Admin Commands:**
`/time admin set_current_time` - Set the current RP date and time (Admin only)
`/time admin set_time_scale` - Set how many real minutes equal one RP day (Admin only)
`/time admin reset_cycle` - Reset the election cycle to the beginning (Admin only)
`/time admin set_voice_channel` - Set which voice channel to update with RP date (Admin only)
`/time admin toggle_voice_updates` - Toggle automatic voice channel name updates (Admin only)
`/time admin update_voice_channel` - Manually update the configured voice channel with current RP date (Admin only)
`/time admin pause_time` - Pause or unpause RP time progression (Admin only)
`/time admin regenerate_stamina` - Manually regenerate stamina for all candidates (Admin only)"""
            },
            "signups": {
                "title": "📋 Election Signups",
                "content": """`/signup` - Sign up as a candidate for election (only during signup phase)
`/view_signups` - View all current candidate signups
`/withdraw_signup` - Withdraw your candidacy from the current election
`/my_signup` - View your current signup details
`/signups_by_seat` - View signups organized by election seat
`/signups_by_party` - View signups organized by political party"""
            },
            "presidential": {
                "title": "🏛️ Presidential Elections",
                "content": """`/pres_signup` - Sign up to run for President
`/vp_signup` - Sign up to run for Vice President under a specific presidential candidate
`/accept_vp` - Accept a VP candidate for your presidential campaign
`/decline_vp` - Decline a VP candidate request
`/view_pres_signups` - View all current presidential signups
`/my_pres_signup` - View your current presidential signup details

**Presidential Campaign Actions (1 hour cooldowns):**
`/pres_speech` - Give a presidential campaign speech
`/pres_donor` - Make a presidential donor appeal
`/pres_canvassing` - Conduct presidential canvassing in a state
`/pres_ad` - Run a presidential campaign ad
`/pres_poster` - Put up presidential campaign posters"""
            },
            "endorsements": {
                "title": "🤝 Endorsements & Delegates",
                "content": """**User Commands:**
`/endorse` - Endorse a candidate (value based on your Discord role)
`/view_endorsements` - View all endorsements made in current cycle
`/my_endorsement` - View your current endorsement status
`/view_delegates` - View current delegate count for presidential candidates

**Admin Commands:**
`/endorsement_admin set_role` - Set Discord role for endorsement position (Admin only)
`/endorsement_admin remove_role` - Remove endorsement role setting (Admin only)
`/endorsement_admin clear_endorsements` - Clear all endorsements for current cycle (Admin only)
`/delegate_admin call_state` - Manually call a state for delegate allocation (Admin only)
`/delegate_admin set_delegates` - Manually set delegate counts for candidates (Admin only)"""
            },
            "voting": {
                "title": "🗳️ Voting & Results",
                "content": """**User Commands:**
`/view_primary_winners` - View all primary election winners for the current year
`/view_general_winners` - View all general election winners
`/winner_info primary` - View detailed winner information for primary elections
`/winner_info general` - View detailed winner information for general elections

**Admin Commands:**
`/poll admin bulk_set_votes` - Set vote counts for multiple candidates (Admin only)
`/poll admin set_winner_votes` - Set election winner and vote counts for general elections (Admin only)
`/winners admin set_primary_winner` - Set primary election winner with vote counts (Admin only)
`/winners admin set_general_winner` - Set general election winner with vote counts (Admin only)
`/winners admin declare_general_winners` - Declare all general election winners based on final scores (Admin only)
`/winners admin clear_winners` - Clear all winners for a specific election type (Admin only)"""
            },
            "campaign": {
                "title": "🎯 Campaign Actions",
                "content": """**General Campaign Actions (All 1 hour cooldowns):**
`/speech` - Give a campaign speech in a specific state with ideology alignment (700-3000 chars, 1.5 stamina)
`/donor` - Make a donor fundraising appeal (400-3000 chars, 1.5 stamina, +5 corruption)
`/canvassing` - Conduct door-to-door canvassing in a region (100-300 chars, 1 stamina)
`/ad` - Run a campaign video advertisement (video upload, 1.5 stamina)
`/poster` - Put up campaign posters (image upload, 1 stamina)

**Demographics & Voter Outreach:**
`/demographic_appeal` - Target specific demographic groups with campaign appeals
`/demographic_status` - View your current demographic progress (presidential only)

**All actions now have:**
- **1 hour cooldowns** (unified across all campaign actions)
- **Stamina costs** (varies by action type)
- **Target system** (specify which candidate benefits)"""
            },
            "momentum": {
                "title": "🌊 Momentum & Demographics",
                "content": """**User Commands:**
`/momentum status` - View momentum status for a specific state
`/momentum overview` - View momentum overview for all states
`/momentum trigger_collapse` - Attempt to trigger momentum collapse for a vulnerable party

**Demographics Commands:**
`/demographic_appeal` - Appeal to specific demographic groups
`/demographic_status` - View your demographic progress (presidential candidates)
`/demographics view_state_demographics` - View demographic strengths by state

**Admin Commands:**
`/momentum admin add_momentum` - Add momentum to a party in a state (Admin only)
`/momentum admin set_lean` - Set or change a state's political lean (Admin only)
`/momentum admin settings` - View or modify momentum system settings (Admin only)

**Key System Updates:**
- **No Thresholds**: Demographics no longer have point thresholds
- **Multiplier Focus**: States have Small (0.05), Moderate (0.10), Strong (0.25) multipliers
- **Conflict System**: Targeting opposing demographics creates backlash
- **Momentum Vulnerability**: 50+ momentum makes parties vulnerable to collapse"""
            },
            "special": {
                "title": "🚨 Special Elections",
                "content": """**Special Election Commands:**

**User Commands:**
`/special signup` - Sign up for an active special election (candidate name, party)
`/special speech` - Give a campaign speech (1 hour cooldown, 2-4 points, 700-3000 chars, -20 stamina)
`/special poster` - Put up campaign posters (1 hour cooldown, 1-3 points, image upload, -15 stamina)
`/special ad` - Run campaign video ads (1 hour cooldown, 3-6 points, video upload, -25 stamina)
`/special calendar` - View current special election timeline and status
`/special poll` - Conduct NPC poll with 7% margin of error (300-800 sample size)

**Admin Commands:**
`/special admin call_election` - Call a special election for a vacant House seat (Admin only)
`/special admin end_election` - End an active special election and declare winner (Admin only)
`/special admin view_points` - View real campaign points for all candidates (Admin only)
`/special admin cancel_election` - Cancel an active special election (Admin only)

**Special Election System Features:**
- **Eligibility**: Only House seats (REP- or District seats)
- **Timeline**: 4 days total (1 day signup, 3 days campaign)
- **Participation**: Anyone can participate, regardless of regular election status
- **Stamina**: Start with 100, regeneration varies, actions cost 15-25 stamina
- **Cooldowns**: All actions have unified 1-hour cooldowns
- **Target System**: Must specify target candidate for all campaign actions
- **Winner Determination**: Highest total points wins the seat
- **Automatic Progression**: Elections progress through phases automatically
- **Real-time Tracking**: Admin tools for monitoring campaign progress"""
            },
            "admin": {
                "title": "🔧 Admin Commands",
                "content": """**System Administration:**
`/admin_central reset_campaign_cooldowns` - Reset campaign action cooldowns for a user (Admin only)
`/admin_central regenerate_stamina` - Manually regenerate stamina for all candidates (Admin only)
`/admin_central system_status` - View overall system status and health (Admin only)

**Campaign Administration:**
`/admin_campaign speech` - Administrative speech action (Admin only)
`/admin_campaign donor` - Administrative donor action (Admin only)
`/admin_campaign canvassing` - Administrative canvassing action (Admin only)
`/admin_campaign ad` - Administrative advertisement action (Admin only)
`/admin_campaign poster` - Administrative poster action (Admin only)

**Party Management:**
`/party admin create` - Create a new political party (Admin only)
`/party admin remove` - Remove a political party (Admin only)
`/party admin edit` - Edit an existing political party (Admin only)
`/party admin reset` - Reset all parties to default (Admin only)
`/party admin bulk_create` - Create multiple parties at once (Admin only)
`/party admin remove_all_custom` - Remove all custom parties (Admin only)
`/party admin export` - Export party configuration as text (Admin only)
`/party admin modify_color` - Change the color of multiple parties (Admin only)

**Election Management:**
`/election admin set_seats` - Set up election seats for the guild (Admin only)
`/election admin reset_seats` - Reset all election seats (Admin only)
`/election admin view_seats` - View all configured election seats (Admin only)
`/election admin bulk_add_seats` - Add multiple seats from formatted text (Admin only)
`/election admin fill_vacant_seat` - Fill a vacant seat with a user (Admin only)
`/election seat admin_update` - Update a specific election seat (Admin only)
`/election seat admin_reset_term` - Reset term for a specific seat (Admin only)

**Time Management:**
`/time admin set_current_time` - Set the current RP date and time (Admin only)
`/time admin set_time_scale` - Set how many real minutes equal one RP day (Admin only)
`/time admin reset_cycle` - Reset the election cycle to the beginning (Admin only)
`/time admin pause_time` - Pause or unpause RP time progression (Admin only)
`/time admin set_voice_channel` - Set voice channel for RP date updates (Admin only)
`/time admin toggle_voice_updates` - Toggle automatic voice channel updates (Admin only)
`/time admin update_voice_channel` - Manually update voice channel with RP date (Admin only)

**Momentum & Demographics:**
`/momentum admin add_momentum` - Add momentum to a party in a state (Admin only)
`/momentum admin set_lean` - Set or change a state's political lean (Admin only)
`/momentum admin settings` - View or modify momentum system settings (Admin only)

**Special Elections:**
`/special admin call_election` - Call a special election for a vacant House seat (Admin only)
`/special admin end_election` - End an active special election (Admin only)
`/special admin set_winner` - Manually set special election winner (Admin only)

**Polling & Voting:**
`/poll admin bulk_set_votes` - Set vote counts for multiple candidates (Admin only)
`/poll admin set_winner_votes` - Set election winner and vote counts (Admin only)
`/winners admin set_primary_winner` - Set primary election winner with votes (Admin only)
`/winners admin set_general_winner` - Set general election winner with votes (Admin only)
`/winners admin declare_general_winners` - Declare all general winners based on scores (Admin only)
`/winners admin clear_winners` - Clear all winners for specific election type (Admin only)"""
            }
        }

        category_data = categories.get(category, categories["basic"])
        embed = discord.Embed(
            title=category_data["title"],
            description=category_data["content"],
            color=discord.Colour.blue()
        )
        embed.set_footer(text="Use the dropdown below to navigate between command categories")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class Basics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Basics cog loaded successfully")

    @app_commands.command(
        name="help",
        description="Show help information with interactive navigation"
    )
    @app_commands.describe(section="Optional: Jump directly to a specific help section")
    async def help_command(self, interaction: discord.Interaction, section: str = None):
        if section == "commands":
            view = HelpView()
            embed = view.get_embed("basic")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        elif section == "handbook":
            view = HandbookView()
            embed = view.get_handbook_embed("getting_started")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        elif section == "credits":
            embed = discord.Embed(
                title="🏆 Bot Credits",
                description="This Discord election simulation bot was created and developed by dedicated contributors.",
                color=discord.Colour.gold()
            )
            embed.add_field(
                name="Development Team",
                value="• **Lead Developer**: [Your Name]\n• **Contributors**: [Additional contributors]\n• **Special Thanks**: Discord.py community",
                inline=False
            )
            embed.add_field(
                name="Bot Features",
                value="• Full election simulation system\n• Presidential and general elections\n• Special elections for House seats\n• Momentum and demographic systems\n• Campaign actions with 1-hour cooldowns\n• Time management and progression\n• Comprehensive admin tools",
                inline=False
            )
            embed.set_footer(text="Thank you for using our election simulation bot!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Default help message with options - no view needed
            embed = discord.Embed(
                title="🤖 Election Bot Help System",
                description="Welcome to the comprehensive election simulation bot! Choose how you'd like to get help:",
                color=discord.Colour.blue()
            )

            embed.add_field(
                name="📋 Command Reference",
                value="Use `/help commands` to browse all available commands organized by category. Includes special elections, updated demographics, and 1-hour cooldown system.",
                inline=False
            )

            embed.add_field(
                name="📚 Strategy Handbook", 
                value="Use `/help handbook` for detailed guides on campaign strategies, demographics (no thresholds), momentum system, and special elections.",
                inline=False
            )

            embed.add_field(
                name="🏆 Credits",
                value="Use `/help credits` to see who made this bot possible.",
                inline=False
            )

            embed.add_field(
                name="🆕 Recent Updates",
                value="• **Special Elections**: 4-day House seat elections\n• **Demographics**: No thresholds, focus on state multipliers\n• **Campaign Actions**: All actions now have 1-hour cooldowns\n• **Unified Stamina**: General (100) and Presidential (200) candidates\n• **Enhanced Momentum**: More strategic importance",
                inline=False
            )

            embed.set_footer(text="Use the commands above to access specific help sections")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.autocomplete("section")
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            app_commands.Choice(name="Commands Reference", value="commands"),
            app_commands.Choice(name="Strategy Handbook", value="handbook"), 
            app_commands.Choice(name="Credits", value="credits")
        ]
        return [choice for choice in choices if current.lower() in choice.name.lower()]

async def setup(bot):
    await bot.add_cog(Basics(bot))