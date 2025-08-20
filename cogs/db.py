from pymongo.mongo_client import MongoClient
from discord.ext import commands
import discord
import os

class Db(commands.Cog):  # Capitalized as per style
    def __init__(self, bot):
        self.bot = bot
        print("Database cog loaded successfully.")

db_user = os.getenv("db_user") # Get the MongoDB user from environment variables
if not db_user:
    print("Please set the MongoDB user environment variable.")
   # return
db_password = os.getenv("db_password") # Get the MongoDB password from environment variables
if not db_password:
    print("Please set the MongoDB password environment variable.")
 #   return
uri = f"mongodb+srv://{db_user}:{db_password}@election-bot.sxvcepu.mongodb.net/?retryWrites=true&w=majority&appName=election-bot"

# Create a new client and connect to the server
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

async def setup(bot):
    bot.db = client ["election_bot"]
#    bot.db = client.election_bot  # Set the database to election_bot

    await bot.add_cog(Db(bot))


