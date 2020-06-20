import asyncio
import json
import os
import random
import traceback

import discord
from discord.ext import commands

from bot.utils.servers import Server
from bot.utils.webhooks import Donation
import bot.utils.create_captcha as captcha

initial_extensions = [
                    "bot.cogs.others.general",
                    "bot.cogs.others.help",
                    "bot.cogs.others.error",

                    "bot.cogs.moderation.moderation",

                    "bot.cogs.music.music_moderation",
                    "bot.cogs.music.music"  # This needs to be loaded as the last cog, we change the working environment here
                    ]


def generate_captcha():
    """
    Generates a captcha image for the user to solve
    :return: Dict
    """
    captcha_text = captcha.create_random_captcha_text()
    captcha.create_image_captcha(captcha_text)
    file = discord.File("captcha.png", filename="captcha.png")

    return_dict = {
        "verif_code": captcha_text.lower(),
        "file": file
    }

    return return_dict


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
        """
        Loads all of the command files (stored in the cogs folder) into the bot to be used
        """
        for extension in initial_extensions:
            try:
                self.load_extension(extension)  # Loads in the extension
            except Exception:
                print(f"Failed to load extension {extension}.")  # If it fails, we print the traceback error
                traceback.print_exc()
        self.load_extension("jishaku")

    async def get_prefix(self, message):
        """
        Returns the server prefix stored in a database; this lets us have per-server prefixes
        :param message: The message object that was sent
        """
        if not message.guild:
            self.prefix = "!"
        else:
            self.prefix = Server(self, message.guild).prefix
        return commands.when_mentioned_or(self.prefix)(self, message)

    async def on_message(self, message):
        await self.process_commands(message)
    """async def on_member_join(self, member):
        server = Server(self, member.guild)
        if not server.vs:
            return

        generated_captcha = generate_captcha()
        file = generated_captcha['file']
        verif_code = generated_captcha['verif_code']

        embed = discord.Embed(title="Verify you are human", color=discord.Color.orange())
        embed.set_image(url="attachment://captcha.png")
        await member.send(file=file, embed=embed)

        while True:
            try:
                provided_code = await self.wait_for('message', check=lambda message: message.author.id == member.id, timeout=30.0)
                if provided_code.content == verif_code:
                    role = discord.utils.get(member.guild.roles, id=720177199365357659)
                    if role:
                        await member.add_roles(role, reason="Verification Passed")
                        return await member.send(f"Okay! You now have the role {role.name}!")
                    else:
                        return await member.send("Sorry, I could not find the provided role to apply to you. Please contact a server administrator")
                else:
                    generated_captcha = generate_captcha()
                    file = generated_captcha['file']
                    verif_code = generated_captcha['verif_code']

                    embed = discord.Embed(title="Invalid Verification Code! Try Again!", color=discord.Color.red())
                    embed.set_image(url="attachment://captcha.png")
                    await member.send(file=file, embed=embed)

                    continue
            except asyncio.TimeoutError:
                continue"""

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
        await self.wait_until_ready()
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
        # await self.loop.run_until_complete(await self.waitForWebhookEvents())
        # await self.loop.run_until_complete(await self.status_changer())

    def run(self):
        """
        This is how we run the bot
        """
        super().run(self.config['Bot']['Token'], reconnect=True)

    async def waitForWebhookEvents(self):
        """
        This will be waiting for any data to be sent to our database, when something is sent to the database it is
            picked up here and lets us do other things with it like sending a thank-you message or giving
            in-game rewards for supporting the bot
        """
        await self.wait_until_ready()
        while True:
            await asyncio.sleep(1)
            dono_channel = self.get_channel(id=713564746284138526)
            donation = Donation()
            listener = donation.listen()
            for dono in listener:
                donation.get_info(txn_id=dono[0])
                embed = discord.Embed(name="Donation Received!", color=discord.Color.blurple())
                embed.add_field(name=f"{self.get_user(int(donation.buyer_id))} has donated {donation.price}!", value=f"Thank you for supporting Legacy!")
                embed.set_footer(text="Thank you <3")
                await dono_channel.send(embed=embed)
                donation.remove_item(donation.txn_id)


if __name__ == "__main__":
    Legacy = LegacyMusic()
    Legacy.run()
