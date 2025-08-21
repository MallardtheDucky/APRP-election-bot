from discord.ext import commands
import discord

class Basics(commands.Cog):  # Capitalized as per style
    def __init__(self, bot):
        self.bot = bot
        print("Basics cog loaded successfully.")

    @discord.app_commands.command(name="commands", description="Lists all the commands in the bot") #commands command
    async def help_command(self, interaction: discord.Interaction):
        with open('help.txt', 'r', encoding='utf-8') as f: # opens help.txt in read mode (unicode), assigns to help_text and 
            help_text = f.read()

        embed = discord.Embed(
            title='Election bot commands:',
            description=help_text,
            color=discord.Colour.blurple()
        )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="credits", description="Lists the people that made this bot")
    async def credits_command(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title='To the people who made me possible:',
            description="""
            Mallard - original creator
            Sixteen - 16bysixteen - maintainer
            Yuri - deftvessel2.0 - maintainer
            """,
            color=discord.Colour.blurple()
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Basics(bot))
