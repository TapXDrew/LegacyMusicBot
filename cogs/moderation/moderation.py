import asyncio
import json
import os

import discord
from discord.ext import commands

from utils.userInfo import User
from utils.servers import Server


class Moderation(commands.Cog):
    """
    This is the command class we will be loading into the bot
    """
    def __init__(self, bot):
        """
        Initializes the command class for use
        :param bot: The bot class that this is being loaded into
        """
        self.config = json.load(open(os.getcwd() + '/config/config.json'))  # loads in the config file so we can use it later
        self.bot = bot  # This is the bot instance, it lets us interact with most things

    def cog_check(self, ctx):
        """
        The cog check is ran before each command, this can let us limit what commands can be used by what users if we apply a check
        :param ctx: The context the command was called from
        """
        self.config = json.load(open(self.bot.home_dir + '/config/config.json'))  # Updates the config file to make sure we have the most relevant information
        return True  # If we return False, nobody can use commands; True lets the user run the command

    @commands.command(name="Kick", aliases=[], help="Kicks a user from the server", usage="Kick <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def kick_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason="No Reason Provided"):
        """
        The Kick command; Kicks a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to kick from the server
        :param reason: Why the users were kicked; this will show on the audit log; defaulted to 'No Reason Provided'
        """
        kicked_users = []
        failed_users = []
        for user in users:
            try:
                await ctx.guild.kick(user, reason=reason)
                kicked_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)
        embed = discord.Embed(title="Kicked Users", color=discord.Color.green())
        if kicked_users:
            embed.add_field(name="Successful Kicks", value='\n'.join(kicked_users))
        if failed_users:
            embed.add_field(name="Failed Kicks", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="Ban", aliases=[], help="Ban a user from the server", usage="Ban <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def ban_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason="No Reason Provided"):
        """
        The Ban command; Bans a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to ban from the server
        :param reason: Why the users were banned; this will show on the audit log; defaulted to 'No Reason Provided'
        """
        banned_users = []
        failed_users = []
        for user in users:
            try:
                await ctx.guild.ban(user, delete_message_days=7, reason=reason)
                banned_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)
        embed = discord.Embed(title="Banned Users", color=discord.Color.green())
        if banned_users:
            embed.add_field(name="Successful Bans", value='\n'.join(banned_users))
        if failed_users:
            embed.add_field(name="Failed Bans", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="UnBan", aliases=[], help="UnBan a user from the server", usage="UnBan <user> [reason]")
    @commands.has_permissions(manage_guild=True)
    async def unban_CMD(self, ctx, user, *, reason="No Reason Provided"):
        """
        The UnBan command; UnBan a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param user: The user to UnBan from the server
        :param reason: Why the users were unbanned; this will show on the audit log; defaulted to 'No Reason Provided'
        """
        embed = discord.Embed(title="Un-Banned Users", color=discord.Color.green())
        bans = await ctx.guild.bans()
        try:
            for user_reason in bans:
                original_reason, banned_user = user_reason
                if banned_user.id == int(user):
                    await ctx.guild.unban(banned_user, reason=reason)
                    embed.add_field(name="Successful Un-Bans", value=banned_user.name)
        except discord.errors.Forbidden:
            embed.add_field(name="Failed Un-Bans", value=user)
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="TempBan", aliases=[], help="TempBan a user from the server", usage="TempBan <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def tempban_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason="No Reason Provided"):
        """
        The TempBan command; TempBan a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to tempban from the server
        :param reason: Why the users were banned; this will show on the audit log; defaulted to 'No Reason Provided'
        """
        tempbanned_users = []
        failed_users = []
        for user in users:
            try:
                await ctx.guild.ban(user, delete_message_days=7, reason=reason)
                await ctx.guild.unban(user, reason=reason)
                tempbanned_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)
        embed = discord.Embed(title="Temp-Banned Users", color=discord.Color.green())
        if tempbanned_users:
            embed.add_field(name="Successful Temp-Bans", value='\n'.join(tempbanned_users))
        if failed_users:
            embed.add_field(name="Failed Temp-Bans", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="Mute", aliases=[], help="Mute a user from speaking in the server", usage="Mute <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def mute_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason="No Reason Provided"):
        """
        The Mute command; Mute a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to mute from the server
        :param reason: Why the users were muted; this will show on the audit log; defaulted to 'No Reason Provided'
        """
        muted_users = []
        failed_users = []
        for user in users:
            try:
                perms = {user: discord.PermissionOverwrite(send_messages=False, read_messages=True)}
                for channel in ctx.guild.channels:
                    await channel.edit(overwrites=perms)
                muted_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)

        embed = discord.Embed(title="Muted Users", color=discord.Color.green())
        if muted_users:
            embed.add_field(name="Successful Mutes", value='\n'.join(muted_users))
        if failed_users:
            embed.add_field(name="Failed Mutes", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="UnMute", aliases=[], help="UnMute a user from speaking in the server", usage="UnMute <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def unmute_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason="No Reason Provided"):
        """
        The UnMute command; UnMute a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to unmute from the server
        :param reason: Why the users were unmuted
        """
        unmuted_users = []
        failed_users = []
        for user in users:
            try:
                perms = {user: discord.PermissionOverwrite(send_messages=True, read_messages=True)}
                for channel in ctx.guild.channels:
                    await channel.edit(overwrites=perms)
                unmuted_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)

        embed = discord.Embed(title="UnMuted Users", color=discord.Color.green())
        if unmuted_users:
            embed.add_field(name="Successful UnMutes", value='\n'.join(unmuted_users))
        if failed_users:
            embed.add_field(name="Failed UnMutes", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}')
        await ctx.send(embed=embed)

    @commands.command(name="TempMute", aliases=[], help="Mutes a user and auto-unmutes them at a later time", usage="TempMute <user1> [user2] [user3] ... [reason]")
    @commands.has_permissions(manage_guild=True)
    async def tempmute_CMD(self, ctx, users: commands.Greedy[discord.Member], time, *, reason="No Reason Provided"):
        """
        The TempMute command; TempMute a user from the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to tempmute from the server
        :param time: The time in minutes to mute the user
        :param reason: Why the users were unmuted
        """
        time = int(time)

        tempmuted_users = []
        failed_users = []
        for user in users:
            try:
                perms = {user: discord.PermissionOverwrite(send_messages=True, read_messages=True)}
                for channel in ctx.guild.channels:
                    await channel.edit(overwrites=perms)
                tempmuted_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)

        embed = discord.Embed(title="TempMuted Users", color=discord.Color.green())
        if tempmuted_users:
            embed.add_field(name="Successful TempMutes", value='\n'.join(tempmuted_users))
        if failed_users:
            embed.add_field(name="Failed TempMutes", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: {reason}\nTime: {time} minute(s)')
        await ctx.send(embed=embed)

        await asyncio.sleep(time*60)
        
        unmuted_users = []
        failed_users = []
        for user in users:
            try:
                perms = {user: discord.PermissionOverwrite(send_messages=True, read_messages=True)}
                for channel in ctx.guild.channels:
                    await channel.edit(overwrites=perms)
                unmuted_users.append(user.name)
            except discord.errors.Forbidden:
                failed_users.append(user.name)

        embed = discord.Embed(title="UnMuted Users", color=discord.Color.green())
        if unmuted_users:
            embed.add_field(name="Successful UnMutes", value='\n'.join(unmuted_users))
        if failed_users:
            embed.add_field(name="Failed UnMutes", value='\n'.join(failed_users))
        embed.set_footer(text=f'Reason: Auto-Unmute')
        await ctx.send(embed=embed)

    @commands.command(name="Warn", aliases=[], help="Warn a user", usage="Warn <user1> [user2] [user3] ... <reason>")
    @commands.has_permissions(manage_guild=True)
    async def warn_CMD(self, ctx, users: commands.Greedy[discord.Member], *, reason):
        """
        The Warn command; Warn a user in the server and sends an embed message
        :param ctx: The context the command was called from
        :param users: All users to warn in the server
        :param reason: Why the users were warned; This is saved in the users warn history
        """
        warned_users = []
        for user in users:
            userWarns = User(bot=self.bot, ctx=ctx, user=user)
            userWarns.warn(reason)
            warned_users.append(user.name)
        embed = discord.Embed(title=f"Warned users", color=discord.Color.orange())
        embed.add_field(name=f"Warned {len(warned_users)} user(s)", value="\n".join(warned_users))
        embed.set_footer(text=reason)
        await ctx.send(embed=embed)

    @commands.command(name="Warnings", aliases=[], help="Displays a users warning history", usage="Warnings <user>")
    @commands.has_permissions(manage_guild=True)
    async def warnings_CMD(self, ctx, user: discord.Member = None):
        """
        The Warnings command; Shows all the users warnings
        :param ctx: The context the command was called from
        :param user: The users who's warnings we are checking
        """
        if not user:
            user = ctx.author
        userWarns = User(bot=self.bot, ctx=ctx, user=user)
        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name=f"{user.name}'s Warnings", value="\n".join([f"{int(index) + 1}: {warn}" for index, warn in userWarns.warns.items()]) if userWarns.warns else "None")
        await ctx.send(embed=embed)

    @commands.command(name="RemoveWarn", aliases=[], help="Removes a users warning", usage="RemoveWarn <user> <ID>")
    @commands.has_permissions(manage_guild=True)
    async def remove_CMD(self, ctx, user: discord.Member, warn_id: int):
        """
        The Remove command; Removes a warning from the users history
        :param ctx: The context the command was called from
        :param user: The users who's warnings we are checking
        :param warn_id: The ID of the warning we are removing
        """
        userWarns = User(bot=self.bot, ctx=ctx, user=user)
        userWarns.remove(warn_id-1)
        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name=f"{user.name}'s Warnings", value="\n".join([f"{int(index) + 1}: {warn}" for index, warn in userWarns.warns.items()]) if userWarns.warns else "None")
        embed.set_footer(text="Removed a warning, here is the users current warnings")
        await ctx.send(embed=embed)

    @commands.command(name="SetPrefix", aliases=['SP', 'Prefix'], help="Set my prefix in the server", usage="SetPrefix <prefix>")
    @commands.has_permissions(manage_guild=True)
    async def setprefix_CMD(self, ctx, prefix):
        server = Server(self.bot, ctx.guild)
        old = server.prefix
        server.updatePrefix(prefix)

        embed = discord.Embed(title="Prefix Changed!", color=discord.Color.green())
        embed.add_field(name="Old Prefix", value=old)
        embed.add_field(name="New Prefix", value=server.prefix)
        embed.set_footer(text="You can also @mention me as a prefix")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Moderation(bot))
