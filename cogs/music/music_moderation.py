import json
import os

import discord
from discord.ext import commands

from utils.servers import Server
from utils.user import User

config = json.load(open(os.getcwd()+'/config/config.json'))


class MusicModeration(commands.Cog):
    def __init__(self, bot):
        self.user = None
        self.server = None

        self.bot = bot
        self.config = json.load(open(os.getcwd() + '/config/config.json'))

        self.FailEmbed = int(config["Embeds Colors"]["Fail Embed"], 16)
        self.SuccessEmbed = int(config["Embeds Colors"]["Success Embed"], 16)
        self.VoteEmbed = int(config["Embeds Colors"]["Vote Embed"], 16)

    def cog_check(self, ctx):
        self.config = json.load(open(self.bot.home_dir + '/config/config.json'))  # Updates the config file to make sure we have the most relevant information
        self.user = User(bot=self.bot, ctx=ctx)
        self.server = Server(bot=self.bot, guild=ctx.guild)
        if 'blacklist' in self.user.perms:
            return False
        if self.server.locked:
            if ctx.channel.id in self.server.locked:
                return True
            else:
                return False
        return True

    @commands.command(name='Override', help="Adds permission overrides to a specific user",
                      usage="Override <permission> [user]", aliases=['AddPerm'])
    @commands.has_permissions(manage_guild=True)
    async def override(self, ctx, perm, member: discord.Member = None):
        """
        Test command to add permission overrides suck as skip, queue clear, ect
        :param ctx: Information on the context of where the command was called
        :param member: The user to add the over-ride permission to
        :param perm: The over-ride permission to add to the user; corresponding to permissions.json
        """
        if member is None:
            member = ctx.author

        user = User(bot=self.bot, ctx=ctx, user=member)
        added = user.add_permission(perm)
        if added:
            await ctx.send(f"Ok! {member.name} has the '{perm.lower().capitalize()}' override permission!")
        else:
            await ctx.send(
                f'Sorry, cant do that...Use `{self.bot.prefix}ValidPermissions` to view all valid permission names')

    @commands.command(name="ValidPermissions", aliases=["VP"], help="Shows all valid permissions you can give a user",
                      usage="ValidPermissions")
    async def validpermissions(self, ctx):
        """
        Lists all of the permissions that you can add to a user
        :param ctx: Information on the context of where the command was called
        """
        perms = json.load(open(os.getcwd()+'/utils/permissions.json'))
        embed = discord.Embed(title="Valid Permissions", color=self.SuccessEmbed)
        for name, perm in perms["Permissions"]["CommandBypasses"].items():
            embed.add_field(name=name, value=perm, inline=False)
        embed.set_footer(text=f"{self.bot.prefix}override <permission> [user]")
        await ctx.send(embed=embed)

    @commands.command(name="Permissions", aliases=['Perms'], help="Checks permissions on the giver user, if any",
                      usage="Permissions [user]")
    async def permissions(self, ctx, user: discord.Member = None):
        """
        Checks the permissions on the given user
        :param ctx: Information on the context of where the command was called
        :param user: The user whose permissions will be checked if specified, otherwise the message author
        """
        if not user:
            user = ctx.author
        self.user = User(bot=self.bot, ctx=ctx, user=user)
        embed = discord.Embed(title=f"{user.name}'s Permissions", color=self.SuccessEmbed)
        embed.add_field(name="Permissions", value=(
            ', '.join([perm.lower().capitalize() for perm in self.user.perms])) if self.user.perms else "None")
        embed.set_footer(text=f"{self.bot.prefix}ValidPermissions will show you what each permission does")
        await ctx.send(embed=embed)

    @commands.command(name="Settings", aliases=['S'], help="Toggle a setting to be on or off!",
                      usage="Settings <setting>")
    @commands.has_permissions(manage_guild=True)
    async def settings(self, ctx, setting):
        """
        Toggle a setting in the config
        :param ctx: Information on the context of where the command was called
        :param setting: The setting to be toggled
        """
        setting = setting.lower()
        if setting in ['autoplaylist', 'auto', 'playlist', 'ap']:
            value = not bool(self.server.ap)
            self.server.update_value("AutoPlaylist", int(value))
            embed = discord.Embed(title="Setting Changed!", color=self.SuccessEmbed)
            embed.add_field(name="You have changed a setting!", value=f"The auto-playlist system is now {'on!' if value else 'off!'}")
            embed.set_footer(text=f"{self.bot.prefix}Settings <setting>")
            return await ctx.send(embed=embed)
        elif setting in ['permissions', 'perms', 'votes', 'vote', 'p', 'v']:
            value = not bool(self.server.ps)
            self.server.update_value("PermissionSystem", int(value))
            embed = discord.Embed(title="Setting Changed!", color=self.SuccessEmbed)
            embed.add_field(name="You have changed a setting!", value=f"The permission system is now {'on!' if value else 'off!'}")
            embed.set_footer(text=f"{self.bot.prefix}Settings <setting>")
            return await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="That is not a setting!", color=self.FailEmbed)
            embed.add_field(name="Valid settings are", value="Permissions\nAutoPlaylist")
            embed.set_footer(text=f"{self.bot.prefix}Settings <setting>")
            return await ctx.send(embed=embed)

    @commands.command(name="AutoJoin", aliases=['AJ'], help="Set a specific voice channel for me to auto-join!",
                      usage="AutoJoin <channel>")
    @commands.has_permissions(manage_guild=True)
    async def auto_join(self, ctx, channel: discord.VoiceChannel):
        """
        Sets the bot to join a given channel when it restarts or when the !play command is used and the bot is not yet in a channel
        :param ctx: Information on the context of where the command was called
        :param channel: A discord.VoiceChannel for the bot to auto-join
        """
        self.server.update_value("auto_connect", channel.id)
        await ctx.send(f"Ok! I will join {channel.mention} from now on!")

    @commands.command(name="Whitelist", aliases=['WL'], usage="Whitelist <channel>",
                      help="Whitelist a channel for the bot to be used in!")
    @commands.has_permissions(manage_guild=True)
    async def whitelist(self, ctx, channel: discord.TextChannel):
        """
        Sets the servers whitelist channels. If any channels are in the whitelist, the bot can be used in those specific channels. Otherwise, the bot can be used anywhere
        :param ctx: Information on the context of where the command was called
        :param channel: The channel to add to the whitelist
        """
        self.server.add_whitelist(channel)
        return await ctx.send(f"Ok! I have added {channel.mention} to the whitelist!")

    @commands.command(name="UnWhitelist", aliases=['RW', 'UW'], help="Remove a channel from the whitelist",
                      usage="UnWhitelist <channel>")
    @commands.has_permissions(manage_guild=True)
    async def unwhitelist(self, ctx, channel: discord.TextChannel):
        """
        Sets the servers whitelist channels. If any channels are in the whitelist, the bot can be used in those specific channels. Otherwise, the bot can be used anywhere
        :param ctx: Information on the context of where the command was called
        :param channel: The channel to remove from the whitelist
        """
        self.server.remove_whitelist(channel)
        return await ctx.send(f"Ok! I have removed {channel.mention} from the whitelist!")

    @commands.command(name="ViewWhitelisted", aliases=['Channels', 'Channel', 'VW'],
                      help="View the servers whitelisted channels", usage="ViewWhitelisted")
    async def viewwhitelisted(self, ctx):
        """
        Displays the servers whitelisted channels
        :param ctx: Information on the context of where the command was called
        """
        embed = discord.Embed(title="Whitelisted Channels", color=self.SuccessEmbed)
        embed.add_field(name="Channels I can be used in",
                        value='\n'.join([self.bot.get_channel(channel).mention for channel in
                                         self.server.locked]) if self.server.locked
                        else f"There are no whitelisted channels so I can be used anywhere!\n"
                             f"Add one with `{self.bot.prefix}whitelist <channel>`")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(MusicModeration(bot))
