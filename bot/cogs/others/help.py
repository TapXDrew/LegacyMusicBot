import discord
from discord.ext import commands


class Help(commands.Cog):
    """
    Command file to be loaded into a discord bot
    """
    def __init__(self, bot):
        """
        Initializes the bot
        :param bot: discord.Bot
        """
        self.bot = bot  # Lets us use the bot in various other parts of the bot to access information like the voice state of the bot

    @commands.command(name='Help', help="The command you are looking at", usage="Help [command]")
    async def help(self, ctx, search_command=None):
        """
        Help command shows all other commands
        :param ctx: Information on the context of where the command was called
        :param search_command: Shows a more detailed explanation of the command and how to use it
        """
        music_commands = "Music Commands", [command for command in self.bot.get_cog("Music").get_commands()]
        musicMod_commands = "Music Moderation Commands", [command for command in self.bot.get_cog("MusicModeration").get_commands()]
        moderation_commands = "Moderation Commands", [command for command in self.bot.get_cog("Moderation").get_commands()]
        general_commands = "General Commands", [command for command in self.bot.get_cog("General").get_commands()]

        page_view = [music_commands, musicMod_commands, moderation_commands, general_commands]

        view = 0
        page = view+1
        pages = 4

        if not search_command:
            embed = discord.Embed(title=page_view[view][0], color=discord.Color.green())
            for command in page_view[view][1]:
                embed.add_field(name=command.qualified_name, value=command.help, inline=False)
            embed.set_footer(text=f"Page {page}/{pages} | Look at more info on a command with {self.bot.prefix}Help <command>")
            sentMsg = await ctx.send(embed=embed)

            left = "\N{BLACK LEFT-POINTING TRIANGLE}"
            stop = "\N{BLACK SQUARE FOR STOP}"
            right = "\N{BLACK RIGHT-POINTING TRIANGLE}"

            for reaction in [left, stop, right]:
                await sentMsg.add_reaction(reaction)

            while True:
                react, user = await self.bot.wait_for('reaction_add', check=lambda u_react, u_user: u_user.id == ctx.author.id, timeout=20.0)
                if react.emoji == left:
                    view -= 1
                elif react.emoji == stop:
                    break
                elif react.emoji == right:
                    view += 1
                else:
                    continue
                if view < 0:
                    view = 0
                elif view > pages-1:
                    view = pages-1
                page = view + 1
                await react.remove(ctx.author)

                newEmbed = discord.Embed(title=page_view[view][0], color=discord.Color.green())
                for command in page_view[view][1]:
                    newEmbed.add_field(name=command.qualified_name, value=command.help, inline=False)
                newEmbed.set_footer(text=f"Page {page}/{pages} | Look at more info on a command with {self.bot.prefix}Help <command>")
                await sentMsg.edit(embed=newEmbed)
        else:
            for command in self.bot.commands:
                if command.name.lower() == search_command.lower() or search_command.lower() in [aliases.lower() for aliases in command.aliases]:
                    embed = discord.Embed(title=command.name, color=discord.Color.green())
                    embed.add_field(name="Prefix", value=self.bot.prefix, inline=False)
                    embed.add_field(name="Help", value=command.help, inline=False)
                    embed.add_field(name="Usage", value=self.bot.prefix+command.usage, inline=False)
                    embed.add_field(name="Aliases", value=', '.join(command.aliases) if command.aliases else "No Aliases", inline=False)
                    embed.set_footer(text="<> are required command parameters while [] is optional")
                    return await ctx.send(embed=embed)
            await ctx.send("Sorry but I could not find that command!")


def setup(bot):
    bot.add_cog(Help(bot))
