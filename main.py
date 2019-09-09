from discord.ext import commands
import os

TOKEN = os.environ.get('EBAY_BOT_TOKEN')
client = commands.Bot(command_prefix='?', case_insensitive=True)

extensions = ['ebay']


@client.event
async def on_ready():
    print("READY")

if __name__ == "__main__":
    for extension in extensions:
        try:
            client.load_extension(extension)
            print(f"Loaded extension {extension}")
        except Exception as e:
            print(f"Error loading {extension} : {e}")

    client.run(TOKEN)
