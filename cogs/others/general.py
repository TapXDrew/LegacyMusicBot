import json
import os

import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):

        self.bot = bot

        self.config = json.load(open(os.getcwd() + '/config/config.json'))  # Updates the config file to make sure we have the most relevant information

        self.FailEmbed = int(self.config["Embeds Colors"]["Fail Embed"], 16)
        self.SuccessEmbed = int(self.config["Embeds Colors"]["Success Embed"], 16)
        self.VoteEmbed = int(self.config["Embeds Colors"]["Vote Embed"], 16)

    def cog_check(self, ctx):
        self.config = json.load(open(self.bot.home_dir + '/config/config.json'))  # Updates the config file to make sure we have the most relevant information
        return True

    @commands.command(name="Server", aliases=['Support', 'Invite', 'Bot'], help="Get an invite to the support server and a bot invite link", usage="Server")
    async def server_CMD(self, ctx):
        embed = discord.Embed(name="Invite Links", color=discord.Color.green())
        embed.add_field(name="Server", value=f"Click [here]({self.config['Bot']['ServerLink']}) to join the official Legacy Bot Support Server")
        embed.add_field(name="Bot", value=f"Click [here]({self.config['Bot']['BotLink']}) to invite me to your own server")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))
