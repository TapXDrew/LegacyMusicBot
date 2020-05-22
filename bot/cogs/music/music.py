import asyncio
import json
import math
import os
import random
import re
import urllib.parse
import urllib.request

import discord
import youtube_dl
from discord.ext import commands
from path import Path

from bot.utils.queues import SavedQueues
from bot.utils.servers import Server
from bot.utils.user import User


Path(os.getcwd()+'/bot/audio_cache').cd()


regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


class Queue:
    """
    Queue
    -----
    Create an object containing the next song to be streamed in discord
    """

    def __init__(self):
        """
        Initializes the queue list
        """
        self.queue = list()
        self.repeat = False

    def put(self, item, place=0):
        """
        Inserts an item the index 0 of self.queue
        """
        self.queue.insert(place, item)
        return True

    def get(self):
        """
        Gets the last item in the list so that it is grabbing the next item to be played and removes it from the list
        -----
        Returns the song to be played if any, otherwise returns False
        """
        if len(self.queue) > 0:
            removed = self.queue.pop()
            return removed
        return False

    def next_up(self):
        """
        Returns the next song in the queue
        """
        if len(self.queue) > 0:
            return self.queue[-1].title
        return None

    def just_added(self):
        """
        Returns the newest song in the queue
        """
        if len(self.queue) > 0:
            return self.queue[0]
        return None

    def remove(self, place):
        """
        Removes an item from the queue based on the index
        """
        if len(self.queue) >= place:
            return self.queue.pop(place - 1)
        return False

    def find(self, place):
        """
        Finds an item from the queue based on the index
        """
        if len(self.queue) >= place:
            return self.queue[place - 1]
        return False


class AudioSourcePlayer(discord.PCMVolumeTransformer):  # This is our video download/player so we can send a stream of audio to a Voice Channel
    def __init__(self, source, *, data):
        super().__init__(source, 0.5)

        # Video Info
        self.data = data
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.get_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

        # Added Info
        self.ctx = data.get('ctx')
        self.requester = data.get('requester')
        self.channel = self.ctx.channel
        self.filename = data.get('filename')

        self.repeat = False

    @staticmethod
    def get_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)

    @classmethod
    async def download(cls, url, *, loop=None, stream=False, ctx):
        youtube_dl.utils.bug_reports_message = lambda: ''
        ffmpeg_options = {'options': '-vn'}
        # before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                               'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
                               'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True,
                               'default_search': 'auto', 'source_address': '0.0.0.0'}
        ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        data["ctx"] = ctx if ctx else "No Additional Information"  # Stores the context of the song
        data['requester'] = ctx.author if ctx.author else "Auto-Play"  # Store the song requester

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        data['filename'] = filename
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    """
    Command file to be loaded into a discord bot
    """

    def __init__(self, bot):
        """
        Initializes the bot to be used for music
        :param bot: discord.Bot
        """
        self.user = None  # This lets us check music permissions for a given user
        self.server = None  # Info on a given server

        self.bot = bot  # Lets us use the bot in various other parts of the bot to access information like the voice state of the bot
        self.players = {}  # Each servers' music player is stored here so we can get information on the current song, pause, play, ect while being server exclusive
        self.queues = {}  # Each servers' Queue object is stored here
        self.play_status = {}  # Stores information on if the server will play music or not, changed with any play commands and the stop command

        self.config = json.load(open(self.bot.home_dir + '/bot/config/config.json'))

        self.FailEmbed = int(self.config["Embeds Colors"]["Fail Embed"], 16)
        self.SuccessEmbed = int(self.config["Embeds Colors"]["Success Embed"], 16)
        self.VoteEmbed = int(self.config["Embeds Colors"]["Vote Embed"], 16)

    def cog_check(self, ctx):
        self.config = json.load(open(self.bot.home_dir + '/bot/config/config.json'))  # Updates the config file to make sure we have the most relevant information
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

    # Extra Functions
    @staticmethod
    def get_songs(song):
        """
        Gets a video link from youtube based on the param song
        :param song: A song name or title to search on youtube and return a video ID
        -----
        If no video is found then return False, otherwise return the video ID
        """
        query_string = urllib.parse.urlencode({"search_query": song})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'href=\"/watch\?v=(.{11})', html_content.read().decode())
        try:
            return search_results[0:20] if len(search_results*2) >= 20 else search_results[0:len(search_results)]
        except IndexError:
            return False

    @staticmethod
    def get_song(song, index=0):
        """
        Gets a video link from youtube based on the param song
        :param song: A song name or title to search on youtube and return a video ID
        :param index: The song index to be returned
        -----
        If no video is found then return False, otherwise return the video ID
        """
        query_string = urllib.parse.urlencode({"search_query": song})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'href=\"/watch\?v=(.{11})', html_content.read().decode())
        try:
            return search_results[index]
        except IndexError:
            return False

    async def play_next_song(self, ctx, queue_type='Player'):
        """
        Plays the next queued song if the bot is not already playing a song in the server
        :param ctx: Information on the context of where the command was called
        :param queue_type: How the command was called
        """
        self.play_status[ctx.guild.id] = True
        queue = self.queues[ctx.guild.id]  # Gets the current servers queue
        player = self.players[ctx.guild.id]  # Current player for the guild
        status = self.play_status[ctx.guild.id]
        if not ctx.message.guild.voice_client:
            return
        if ctx.message.guild.voice_client.is_playing() and queue_type == 'Player' or ctx.message.guild.voice_client.is_paused() and queue_type == 'Player':  # Checking if we send a message saying that the song is queued or will now play
            embed = discord.Embed(title=f"{queue.just_added().title} has been added to the queue", color=self.SuccessEmbed, inline=False)
            embed.add_field(name=f"Song length", value=queue.just_added().duration, inline=False)
            embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
            await ctx.send(embed=embed)
        while True:
            await asyncio.sleep(2)
            if ctx.message.guild.voice_client.is_playing() or ctx.message.guild.voice_client.is_paused():  # If the bot is currently playing a song or has a paused song, then we wait 5 seconds then check again
                await asyncio.sleep(3)
                continue
            else:
                try:
                    if not self.play_status[ctx.guild.id]:
                        return
                    elif player and player.repeat:
                        result = self.get_song(player.title)  # Gets a video ID for the song
                        player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                    elif queue.repeat:
                        result = self.get_song(player.title)  # Gets a video ID for the song
                        player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                        queue.put(player)
                        player = queue.get()
                    else:
                        player = queue.get()  # Gets the next song to play on the server
                except youtube_dl.utils.DownloadError:
                    return
                if not player:  # If there is no next song, we auto play music
                    if not self.server.ap:
                        return
                    with open(self.bot.home_dir+'/bot/config/_autoplaylist.txt', 'r+') as playlist:
                        songs = [song.strip() for song in playlist.readlines()]
                    try:
                        ctx.author = None
                        await self.play(ctx=ctx, song=random.choice(songs), queue_type='Auto')
                    except youtube_dl.utils.DownloadError:
                        continue
                    return
                else:  # There is still a song on queue so we will now play it
                    if status:
                        self.players[ctx.guild.id] = player  # Either adds the player to the dict using the server ID or updates the current player
                        ctx.guild.voice_client.play(player, after=lambda _: os.remove(self.players[ctx.guild.id].filename))  # Plays audio in the voice chat
                        embed = discord.Embed(color=self.SuccessEmbed)
                        embed.add_field(name=f"{player.title} is now playing!", value=f"Next Up: {queue.next_up() if queue.next_up() else 'Nothing - Request one!'}", inline=False)
                        embed.add_field(name=f"Song length", value=player.duration, inline=False)
                        embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
                        await ctx.send(embed=embed)
                    else:
                        return
            continue

    async def start_vote(self, vote_type, ctx):
        if 'all' in self.user.perms or not self.server.ps:
            return True
        player = self.players[ctx.guild.id]
        reactions = {}
        vote = 1
        if vote_type == "Skip":
            embed = discord.Embed(title=f"Vote Skip started", color=self.VoteEmbed)
            embed.add_field(name="React with :thumbsup: to skip the song, :thumbsdown: to continue",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the song will NOT be skipped")
        elif vote_type == "Queue Remove":
            embed = discord.Embed(title=f"Vote to remove an item from queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to remove `{player.title}`, :thumbsdown: to continue",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the song will NOT be removed")
        elif vote_type == "Queue Clear":
            embed = discord.Embed(title=f"Vote to clear the queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to clear the queue, :thumbsdown: to keep the queue",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be cleared")
        elif vote_type == "Queue Shuffle":
            embed = discord.Embed(title=f"Vote to shuffle the queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to shuffle, :thumbsdown: to keep the order",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be shuffled")
        elif vote_type == "Queue Repeat":
            embed = discord.Embed(title=f"Vote to repeat the queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to repeat, :thumbsdown: to not repeat",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be repeated")
        elif vote_type == "Song Repeat":
            embed = discord.Embed(title=f"Vote to repeat the song", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to repeat, :thumbsdown: to not repeat",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the song will NOT be repeated")
        elif vote_type == "Stop":
            embed = discord.Embed(title=f"Vote to stop all music", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to stop the music, :thumbsdown: to continue listening",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the music will continue")
        elif vote_type == "Queue Load":
            embed = discord.Embed(title=f"Vote to load a queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to load, :thumbsdown: to not load",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be loaded")
        elif vote_type == "Delete Queue":
            embed = discord.Embed(title=f"Vote to delete a queue", color=self.VoteEmbed)
            embed.add_field(name=f"React with :thumbsup: to delete, :thumbsdown: to keep",
                            value=f"Majority wins. You have 30 seconds")
            embed.set_footer(text=f"In the event of a tie, the queue will NOT be deleted")
        else:
            return False
        message = await ctx.send(embed=embed)
        for emote in ["👍", "👎"]:
            await message.add_reaction(emote)
        for _ in range(30):
            try:
                react, user = await self.bot.wait_for('reaction_add', timeout=1)
                if react.emoji == "👍":
                    reactions[user.id] = True
                elif react.emoji == "👎":
                    reactions[user.id] = False
            except Exception:
                continue
        for user, react in reactions.items():
            if user == ctx.author.id or user == self.bot.user:
                continue
            elif react:
                vote += 1
            else:
                vote -= 1
        if vote >= 0:
            return True
        return False

    # noinspection PyTypeChecker
    async def auto_join_channels(self):
        for guild in self.bot.guilds:
            self.server = Server(bot=self.bot, guild=guild)
            if self.server.auto_connect:
                await self.join(ctx=None, channel=self.server.auto_connect, auto_connect=guild)

    # Commands
    @commands.command(name='Join', help="Joins the bot to either your voice channel or a specified channel", usage="Join [channel]", aliases=['summon'])
    async def join(self, ctx, channel: discord.VoiceChannel = None, auto_connect=False):
        """
        Joins the voice channel that the author is in or, if specified, joins the channel specified in the channel param
        :param ctx: Information on the context of where the command was called
        :param channel: If a channel is specified then we will join it, otherwise we join the current voice channel the message author is in, if any
        :param auto_connect: Are we auto-joining a channel
        """
        if not ctx:
            if self.server.auto_connect:
                auto = self.bot.get_channel(self.server.auto_connect)
                return await auto.connect()
        else:
            if ctx.guild.voice_client and channel:
                await ctx.guild.voice_client.move_to(channel)
            elif auto_connect:
                auto = self.bot.get_channel(channel)
                return await auto.connect()
            elif channel:
                return await channel.connect()
            elif ctx.author.voice:
                return await ctx.author.voice.channel.connect()  # Joins the VC that the command author is in
            elif self.server.auto_connect:
                auto = self.bot.get_channel(self.server.auto_connect)
                return await auto.connect()
            else:
                embed = discord.Embed(title="Failed to join a voice channel", color=self.FailEmbed)
                embed.add_field(name="I cant play music if I cant talk!", value="Please join a voice channel before trying to play music or set an auto-join channel!!")
                await ctx.send(embed=embed)

    @commands.command(name='Leave', help="Leaves the current voice channel", usage="Leave")
    async def leave(self, ctx):
        """
        Leaves the current voice channel if the bot is in one
        :param ctx: Information on the context of where the command was called
        """
        if ctx.guild.voice_client:  # Checks if the bot is already in a voice channel, if so we leave it
            await ctx.guild.voice_client.disconnect()

    @commands.command(name='Play', help="Plays a specified song by song name or URL", usage="Play <song>",
                      aliases=['P', 'URL', 'Song', 'Sing', 'Stream'])
    async def play(self, ctx, *, song=None, queue_type='Player'):
        """
        Adds the specified song to the queue to be played
        :param ctx: Information on the context of where the command was called
        :param song: The song to be queued
        :param queue_type: How the command was called
        """
        queue = self.queues[ctx.guild.id]

        titles = []

        if not ctx.message.guild.voice_client:
            return

        if song is None:
            if not self.play_status[ctx.guild.id]:
                await self.resume(ctx)
            if not ctx.message.guild.voice_client.is_playing():
                return await self.play_next_song(ctx, queue_type="Internal")  # Starts to play queued songs
        else:
            async with ctx.typing():
                try:
                    if re.match(regex, song):
                        player = await AudioSourcePlayer.download(song, loop=self.bot.loop, ctx=ctx, stream=False)
                        queue.put(player)
                        found_video = True
                    else:
                        await ctx.send("Fetching Results...")
                        players = []
                        for index, searching in enumerate(self.get_songs(song)):
                            if index % 2 != 0:
                                continue
                            try:
                                player = await AudioSourcePlayer.download(searching, loop=self.bot.loop, ctx=ctx, stream=True)
                                if player.title in titles:
                                    continue
                                players.append(player)
                                titles.append(player.title)
                            except youtube_dl.utils.DownloadError:
                                continue
                        embed = discord.Embed(title="Here are the song results that I came up with!", color=discord.Color.green())
                        embed.add_field(name="Song Names (Select an option)", value="\n".join([f"**{number+1})** {player.title}" for number, player in enumerate(players)]))
                        embed.set_footer(text="Select a song by sending the item number")
                        try:
                            await ctx.send(embed=embed)
                        except discord.errors.HTTPException:
                            await ctx.send(f"Sorry bit I did not find any video matches! please try again with new keywords")
                        while True:
                            msg = await self.bot.wait_for('message', check=lambda message: message.author.id == ctx.author.id, timeout=30.0)
                            try:
                                message_num = int(msg.content)
                                if message_num in range(len(players)+1):
                                    player = await AudioSourcePlayer.download(players[message_num-1].url, loop=self.bot.loop, ctx=ctx, stream=False)
                                    queue.put(player)  # Adds a song to the servers queue system
                                    found_video = True
                                    break
                                else:
                                    await ctx.send("That is not a valid option!")
                            except ValueError:
                                await ctx.send("That is not a valid option!")
                except youtube_dl.utils.DownloadError:
                    found_video = False
            if found_video:
                return await self.play_next_song(ctx, queue_type)  # Starts to play queued songs
            return await ctx.send("Sorry but I cant find that video! Try some different key words")

    @commands.command(name='Pause', help="Pauses the current song", usage="Pause")
    async def pause(self, ctx):
        """
        Pauses the current servers audio stream
        :param ctx: Information on the context of where the command was called
        """
        self.play_status[ctx.guild.id] = False
        player = self.players[ctx.guild.id]
        ctx.message.guild.voice_client.pause()  # Pauses the audio stream
        embed = discord.Embed(color=self.SuccessEmbed)
        embed.add_field(name=f"Paused {player.title}", value=f"{self.bot.prefix}Resume to resume the song")
        await ctx.send(embed=embed)

    @commands.command(name='Resume', help="Resumes the current song", usage="Resume")
    async def resume(self, ctx):
        """
        Resumes the current servers audio stream
        :param ctx: Information on the context of where the command was called
        """
        self.play_status[ctx.guild.id] = True
        player = self.players[ctx.guild.id]
        ctx.message.guild.voice_client.resume()  # Resumes the audio stream
        await ctx.send(f"Resumed {player.title}")

    @commands.command(name='Skip', help="Skips the current song", usage="Skip")
    async def skip(self, ctx):
        """
        Skips the current song being played
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        op = self.players[ctx.guild.id]
        if 'skip' in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Skip", ctx)
        if passed:
            if player == op:
                ctx.message.guild.voice_client.stop()  # Kills the audio stream
                await ctx.send(f"Sorry {player.requester}, but we decided to skip `{player.title}`")
                return await self.play_next_song(ctx)
        else:
            await ctx.send(f"The people have spoken! We will continue playing {player.title}!")

    @commands.command(name='Stop', help="Skips the current song and cancels the next song from playing", usage="Stop", aliases=['Quit'])
    async def stop(self, ctx):
        """
        Stops all music
        :param ctx: Information on the context of where the command was called
        """
        if 'stop' in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Stop", ctx)
        if passed:
            self.play_status[ctx.guild.id] = False
            ctx.message.guild.voice_client.stop()  # Kills the audio stream
            await ctx.send(f"Ok! If you want to continue playing music do `{self.bot.prefix}play`!")
        else:
            await ctx.send(f"The party never stops!")

    @commands.command(name='Volume', help="Changes the bots player volume", usage="Volume <volume>", aliases=['Vol'])
    async def volume(self, ctx, vol: int = None):
        """
        Sets the volume for the player
        :param ctx: Information on the context of where the command was called
        :param vol: the volume for the player, 0-100
        """
        player = self.players[ctx.guild.id]
        if vol is None:
            return await ctx.send(f"Player volume set to {player.volume}")
        if vol < 0:
            vol = 0
        elif vol > 100:
            vol = 100
        player.volume = float(vol / 100)
        return await ctx.send(f"Set the volume to {vol}%")

    @commands.command(name='NowPlaying', help="Information on the current song", usage="NowPlaying",
                      aliases=['Current', "NP"])
    async def nowplaying(self, ctx):
        """
        Displays the current song name along with the next song in the queue
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]
        embed = discord.Embed(title='Song Information', color=self.SuccessEmbed)
        embed.add_field(name=f"Current Song: {player.title} | Requested by *{player.requester}*", value=f"Next Up: {queue.next_up() if queue.next_up() else 'Nothing - Request one!'}")
        embed.add_field(name=f"Song Artist", value=player.data['artist'] if player.data['artist'] else "Not Found")
        embed.set_footer(text=f"Queue Length: {len(queue.queue)}")
        await ctx.send(embed=embed)

    @commands.command(name='Queue', help="Displays the current song queue", usage="Queue")  # Very messy, needs to be cleaned up. Maybe with a pagination class
    async def queue(self, ctx):
        """Displays the current song queue in a paginated embed
        :param ctx: Information on the context of where the command was called
        """
        queue = self.queues[ctx.guild.id]

        first = 0
        second = 10
        curr_page = 1
        left = "\N{BLACK LEFT-POINTING TRIANGLE}"
        stop = "\N{BLACK SQUARE FOR STOP}"
        right = "\N{BLACK RIGHT-POINTING TRIANGLE}"

        total = [f"{enum + 1}. {song.title} - Requested by *{song.requester}*" for enum, song in
                 enumerate(queue.queue[::-1])]

        if len(total) > 10:
            embed = discord.Embed(color=discord.Color.teal())
            embed.add_field(name=f"Music Queue", value='\n'.join(total[first:second]))
            embed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(left)
            await msg.add_reaction(stop)
            await msg.add_reaction(right)

            while True:
                react, user = await self.bot.wait_for('reaction_add',
                                                      check=lambda u_react, u_user: u_user.id == ctx.author.id,
                                                      timeout=20.0)

                if react.emoji == left:
                    first -= 10
                    second -= 10
                    curr_page -= 1
                    if first < 0:
                        first = 0
                    if second < 10:
                        second = 10
                    if curr_page < 0:
                        curr_page = 0

                elif react.emoji == stop:
                    break

                elif react.emoji == right:
                    first += 10
                    second += 10
                    curr_page += 1
                    if first > len(total) - 10:
                        first = len(total) - 10
                    if second > len(total):
                        second = len(total)
                    if curr_page > math.ceil(len(total) / 10):
                        curr_page = math.ceil(len(total) / 10)

                newEmbed = discord.Embed(color=discord.Color.teal())
                newEmbed.add_field(name=f"Music Queue", value='\n'.join(total[first:second]))
                newEmbed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
                await msg.edit(embed=newEmbed)
        else:
            if len(total) == 0:
                embed = discord.Embed(color=discord.Color.teal())
                embed.add_field(name=f"Music Queue",
                                value=f"There are currently no songs in the queue! Add one using the `{self.bot.prefix}play`, `{self.bot.prefix}url` or `{self.bot.prefix}stream` commands!")
                embed.set_footer(text="Total: 0 | Page 1/1")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=discord.Color.teal())
                embed.add_field(name=f"Music Queue", value='\n'.join(total))
                embed.set_footer(text=f"Total: {len(total)} | Page {curr_page}/{math.ceil(len(total) / 10)}")
                await ctx.send(embed=embed)

    @commands.command(name='Remove', help="Removes a song from the current queue", usage="Remove <ID>")
    async def remove(self, ctx, song_num: int):
        """
        Removes an item from the queue
        :param ctx: Information on the context of where the command was called
        :param song_num: The song number in the queue to remove
        """
        queue = self.queues[ctx.guild.id]
        song_num -= 1
        song = queue.find(song_num)
        if not song:
            embed = discord.Embed(title="Failed to remove song", color=self.FailEmbed)
            embed.add_field(name="Sorry but I could not find that song!",
                            value="Please make sure that you used the correct song ID!")
            embed.set_footer(text=f"Example: {self.bot.prefix}{ctx.command.qualified_name} 1")
            return await ctx.send(embed=embed)

        if song.requester == ctx.author or "queueremove" in self.user.perms:
            passed = True
        else:
            passed = self.start_vote("Queue Remove", ctx)

        if passed:
            queue.remove(song_num)
            embed = discord.Embed(title="Removed a song", color=self.SuccessEmbed)
            embed.add_field(name=song.title, value="We have removed the song from the queue!")
            return await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Failed to remove song", color=self.FailEmbed)
            embed.add_field(name="The people have spoken!", value=f"{song.title} stays!")
            return await ctx.send(embed=embed)

    @commands.command(name="Clear", help="Clears the current song queue", usage="Clear", aliases=['qClear'])
    async def clear(self, ctx):
        """
        Clears the queue of all songs
        :param ctx: Information on the context of where the command was called
        """
        queue = self.queues[ctx.guild.id]
        if "queueclear" in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Queue Clear", ctx)
        if passed:
            for song in range(len(queue.queue)):
                queue.remove(song)
            embed = discord.Embed(title="The queue has been cleared!", color=self.SuccessEmbed)
            embed.add_field(name="The current song will continue to be played",
                            value=f"You can stop it with the `{self.bot.prefix}stop` or `{self.bot.prefix}skip` commands")
            embed.set_footer(text=f"After this song is finished, an auto playlist will start")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="The queue stays!", color=self.SuccessEmbed)
            embed.add_field(name="The queue may not be cleared but at least you have some 🎵music🎵 playing",
                            value=f"If you have your own song in the queue you wish to remove, use {self.bot.prefix}remove <song_id>")
            await ctx.send(embed=embed)

    @commands.command(name='Save', help="Saves the queue to be loaded later", usage="!Save")
    async def save(self, ctx):
        """
        Saves the current queue into the servers saved queue list
        :param ctx: Information on the context of where the command was called
        """
        player = self.players[ctx.guild.id]
        queue = self.queues[ctx.guild.id]  # Our queue list
        saved = SavedQueues(bot=self.bot, ctx=ctx)  # All of our saved queues
        queues = eval(saved.get_saved_queues())  # Get our saved queues
        queues.update({f'{len(queues.keys())}': [player.title] + [song.title for song in queue.queue]})
        saved.update(queues)
        await ctx.send(f"I saved the queue for you! Check it out with `{self.bot.prefix}Saved`")

    @commands.command(name='Delete', help="Deletes a saved audio queue", usage="Delete <ID>")
    async def delete(self, ctx, qid: int):
        """
        Deletes a queue from the list of saved queues
        :param ctx: Information on the context of where the command was called
        :param qid: The queue id to delete from
        """
        saved = SavedQueues(bot=self.bot, ctx=ctx)  # All of our saved queues
        queues = eval(saved.get_saved_queues())  # Get our saved queues

        qid = str(qid - 1)

        if qid not in queues:
            embed = discord.Embed(title="Failed to delete queue", color=self.FailEmbed)
            embed.add_field(name="Sorry but I could not find a queue with that ID!",
                            value="Please make sure that you used the correct queue ID!")
            embed.set_footer(text=f"Example: {self.bot.prefix}{ctx.command.qualified_name} 1")
            return await ctx.send(embed=embed)
        if "queuedelete" in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Delete Queue", ctx)
        if passed:
            queues.pop(qid)
            saved.update(queues)
            await ctx.send(f"Ok, I removed that from the saved queue list")
        else:
            await ctx.send("This queue...I like it. It stays, for now")

    @commands.command(name='Load', help="Loads a saved audio queue", usage="Load <ID>")
    async def load(self, ctx, queue_id: int):
        """
        Loads the specified queue into the current queue
        :param ctx: Information on the context of where the command was called
        :param queue_id: The queue id to load into the current queue
        """
        saved = SavedQueues(bot=self.bot, ctx=ctx)
        queues = eval(saved.get_saved_queues())
        if "queueload" in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Queue Load", ctx)
        if passed:
            try:
                queue_to_load = queues[str(queue_id - 1)]
                message = await ctx.send(f"Loading Queue `{queue_id}`\n0% Done")
            except KeyError:
                return await ctx.send(
                    f"Sorry but that queue does not seem to exist! Use `{self.bot.prefix}Saved` to view a list of all saved queues")
            percent = 0
            percent_per_song = 100 / len(queue_to_load)
            async with ctx.typing():
                for song in queue_to_load:
                    result = self.get_song(song)  # Gets a video ID for the song
                    player = await AudioSourcePlayer.download(result, loop=self.bot.loop, ctx=ctx)  # Creates a player
                    queue = self.queues[ctx.guild.id]
                    queue.put(player)  # Adds a song to the servers queue system
                    percent += percent_per_song
                    await message.edit(content=f"Loading Queue...\n{str(percent)[:4]}% Done")

            await ctx.send(f"Queue Loaded!")
            return await self.play_next_song(ctx, 'Auto')  # Starts to play queued songs
        else:
            await ctx.send("Sorry, but people don't seem to like this queue")

    @commands.command(name='Saved', help="Shows all saved audio queues", usage="Saved", aliases=['Queues'])
    async def saved(self, ctx):
        """
        List of all saved queues the server has
        :param ctx: Information on the context of where the command was called
        """
        async with ctx.typing():
            saved = SavedQueues(bot=self.bot, ctx=ctx)
            queues = eval(saved.get_saved_queues())

            if not queues:
                return await ctx.send(f"You have no saved queues! Save one with `{self.bot.prefix}Save`")

            saved_queues = []
            current_page = 0
            left = "\N{BLACK LEFT-POINTING TRIANGLE}"
            stop = "\N{BLACK SQUARE FOR STOP}"
            right = "\N{BLACK RIGHT-POINTING TRIANGLE}"
            for queue, songs in queues.items():
                saved_queues.append([f"Queue ID: {int(queue) + 1:,}", '\n'.join(songs),
                                     f"Page {int(queue) + 1:,} / {len(queues):,} | Total: {len(songs):,}"])
            embed = discord.Embed(title="Saved Queues", color=self.SuccessEmbed)
            embed.add_field(name=saved_queues[0][0], value=saved_queues[0][1])
            embed.set_footer(text=saved_queues[0][2])
            message = await ctx.send(embed=embed)
        for reaction in [left, stop, right]:
            await message.add_reaction(reaction)
        while True:
            react, user = await self.bot.wait_for('reaction_add',
                                                  check=lambda u_react, u_user: u_user.id == ctx.author.id,
                                                  timeout=20.0)
            if react.emoji == left:
                current_page -= 1
            elif react.emoji == stop:
                break
            elif react.emoji == right:
                current_page += 1
            else:
                continue
            if current_page < 0:
                current_page = 0
            elif current_page > len(saved_queues) - 1:
                current_page = len(saved_queues) - 1

            await react.remove(ctx.author)

            embed = discord.Embed(title="Saved Queues", color=self.SuccessEmbed)
            embed.add_field(name=saved_queues[current_page][0], value=saved_queues[current_page][1])
            embed.set_footer(text=saved_queues[current_page][2])
            await message.edit(embed=embed)
        await react.remove(ctx.author)

    @commands.command(name='Repeat', help="Lets the user either repeat a song or the current queue", usage="Repeat <song | queue>")
    async def repeat(self, ctx, *, repeat_type='song'):
        """
        Plays the queue on loop, including the current song
        :param ctx: Information on the context of where the command was called
        :param repeat_type: The type of item we will repeat
        """
        player = self.players[ctx.guild.id]
        if not player:
            return await ctx.send(f"I cant repeat a {repeat_type} that is not playing")
        if repeat_type == 'song':
            if "songrepeat" in self.user.perms:
                passed = True
            else:
                passed = await self.start_vote("Song Repeat", ctx)
            if passed:
                player.repeat = not player.repeat
                embed = discord.Embed(title="Song Repeat has been toggled!", color=self.SuccessEmbed)
                embed.add_field(name=f"Song repeat is set to {player.repeat}!",
                                value="The current song will now be repeated" if player.repeat else "The song will no longer repeat itself")
                await ctx.send(embed=embed)
            else:
                return await ctx.send("Songs tend to get a but annoying after a while...lets mix things up")
        elif repeat_type.lower() == 'queue':
            queue = self.queues[ctx.guild.id]
            if "queuerepeat" in self.user.perms:
                passed = True
            else:
                passed = await self.start_vote("Queue Repeat", ctx)
            if passed:
                queue.repeat = not queue.repeat
                embed = discord.Embed(title="Queue Repeat has been toggled!", color=self.SuccessEmbed)
                embed.add_field(name=f"Queue repeat is set to {queue.repeat}!",
                                value="The current song and the queue will now be repeated" if queue.repeat else "The queue will no longer repeat itself")
                await ctx.send(embed=embed)
            else:
                return await ctx.send("I would rather not listen to a playlist over and over...sorry")
        else:
            return

    @commands.command(name='Shuffle', help="Shuffles the current queue", usage="Shuffle")
    async def shuffle(self, ctx):
        """
        Shuffles the current queue
        :param ctx: Information on the context of where the command was called
        """
        if "queueshuffle" in self.user.perms:
            passed = True
        else:
            passed = await self.start_vote("Queue Shuffle", ctx)
        if passed:
            queue = self.queues[ctx.guild.id]
            random.shuffle(queue.queue)
            embed = discord.Embed(name="Shuffled!", color=self.SuccessEmbed)
            embed.add_field(name="I have shuffled the queue!",
                            value=f"Use `{self.bot.prefix}queue` to view the new queue order")
            await ctx.send(embed=embed)
        else:
            return await ctx.send("I like the current playlist order. Lets keep it")

    # Command Checks
    @play.before_invoke
    async def voice_check(self, ctx):
        """
        This will make sure that the bot is in a voice channel before any voice command is ran
        :param ctx: Information on the context of where the command was called
        """
        if not ctx.message.guild.voice_client:
            await self.join(ctx)

    async def cog_before_invoke(self, ctx):
        """
        This will make sure that the current guild has a player, queue, and player_status set up in the server
        This is ran before every command in this cog
        :param ctx: Information on the context of where the command was called
        """
        if ctx.guild.id not in self.players:
            self.players[ctx.guild.id] = None

        if ctx.guild.id not in self.play_status:
            self.play_status[ctx.guild.id] = True

        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = Queue()

    # Bot Events
    @commands.Cog.listener()
    async def on_ready(self):
        await self.auto_join_channels()


def setup(bot):
    bot.add_cog(Music(bot))
