import asyncio
import json
import os
import random
import traceback

import discord
from discord.ext import commands

from bot.utils.servers import Server

initial_extensions = [
                    "bot.cogs.others.general",
                    "bot.cogs.others.help",
                    "bot.cogs.others.error",

                    "bot.cogs.moderation.moderation",

                    "bot.cogs.music.music_moderation",
                    "bot.cogs.music.music"
                    ]


class LegacyMusic(commands.AutoShardedBot):
    """
    This is our bot, we need to create an instance of the bot and run it for it to be online
    """
    def __init__(self):
        """
        The __init__ method is called whenever an instance of the class is made, it initializes the class
        """
        self.config = json.load(open(os.getcwd() + '/bot/config/config.json'))

        super().__init__(command_prefix=commands.when_mentioned_or(self.get_prefix), case_insensitive=True)  # We are inheriting from the class commands.AutoShardedBot so we also inherit from its __init__ using super()

        self.remove_command('help')  # Remove the help command so we can add our own
        self.home_dir = os.getcwd()
        self.prefix = None

        self.load_commands()

    def load_commands(self):
        for extension in initial_extensions:
            try:
                self.load_extension(extension)  # Loads in the extension
            except Exception:
                print(f"Failed to load extension {extension}.")  # If it fails, we print the traceback error
                traceback.print_exc()
        self.load_extension("jishaku")

    async def get_prefix(self, message):
        self.prefix = Server(self, message.guild).prefix
        return commands.when_mentioned_or(self.prefix)(self, message)

    # noinspection PyTypeChecker
    async def status_changer(self):
        """
            Setting `Playing ` status
            await bot.change_presence(activity=discord.Game(name="a game"))

            Setting `Streaming ` status
            await bot.change_presence(activity=discord.Streaming(name="My Stream", url=my_twitch_url))

            Setting `Listening ` status
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="a song"))

            Setting `Watching ` status
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="a movie"))
        """
        playing = []
        streaming = []
        listening = [discord.Activity(type=discord.ActivityType.listening, name=f"music in {len(self.guilds):,} servers | BIG UPDATE SOON")]
        watching = []
        statuses = playing + streaming + listening + watching
        while True:
            if not self.is_ready():
                continue
            if self.is_closed():
                return
            await self.change_presence(activity=random.choice(statuses))
            await asyncio.sleep(self.config['Bot']['StatusTimer'])

    async def on_ready(self):
        """
        Triggered whenever the bot becomes ready for use
        """
        print("------------------------------------")
        print("Bot Name: " + self.user.name)
        print("Bot ID: " + str(self.user.id))
        print("Discord Version: " + discord.__version__)
        print("------------------------------------")
        await self.loop.run_until_complete(await self.status_changer())

    def run(self):
        """
        This is how we run the bot
        """
        super().run(self.config['Bot']['Token'], reconnect=True)


if __name__ == "__main__":
    Legacy = LegacyMusic()
    Legacy.run()
