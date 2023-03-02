from discord.ext import commands
from discord import (
    User,
    Member,
    Embed,
    Message,
    Forbidden,
    utils, abc)
from unicodedata import normalize
from random import randint
from core.modlogs import ModLogsByUser, BanAppealButton
from core.duration import DurationConverter
from math import floor
from typing import Union
from datetime import timedelta as time_d


class PunishmentCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locked_channels = {}
        self.lockdown_mapping = {}

    @commands.command(
        brief=' <member>',
        aliases=['dc'],
        description='Converts a member\'s nickname into standard English font. Requires <required-role> or higher.',
        extras=1)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def decancer(self, ctx: commands.Context, member: Member):
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 1:
            return

        new_nickname = normalize(
            'NFKD', member.display_name).encode('ascii', 'ignore').decode('utf-8')
        await member.edit(nick=new_nickname)
        await self.bot.embed_success(ctx, f'Changed {member.mention}\'s nickname.')

    @commands.command(
        brief=' <member>',
        aliases=['mn'],
        description='Assigns a randomly-generated nickname to a member. Requires <required-role> or higher.',
        extras=1)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def modnick(self, ctx: commands.Context, member: Member):
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 1:
            return

        await member.edit(nick=f'Moderated Nickname-{hex(randint(1, 10000000))}')
        await self.bot.embed_success(ctx, f'Changed {member.mention}\'s nickname.')

    @commands.command(
        brief=' <user> *opt<reason>',
        aliases=['n'],
        description='Add a note for a user. This will appear in their modlogs history. Requires <required-role> or '
                    'higher.',
        extras=1)
    @commands.guild_only()
    async def note(self, ctx: commands.Context, user: User, *, reason: str = 'No reason given.'):
        member = await self.bot.get_or_fetch_member(user.id)
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 1:
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Note', reason, 0, 0)
        await self.bot.embed_success(ctx, f'Note added for {user.mention}: {reason}')

    @commands.command(
        brief=' <member> *opt<reason>',
        description='Attempts to send a private message to a member. This message will appear in their modlogs history.'
                    ' Requires <required-role> or higher.',
        extras=1)
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.guild_only()
    async def dm(self, ctx: commands.Context, member: Member, *, reason: str = 'No reason given.'):
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 1:
            return

        try:
            await member.send(embed=Embed(colour=0x337fd5,
                                          description=f'***You received a DM from {ctx.guild}:*** {reason}'))
        except Forbidden:
            await self.bot.embed_error(ctx, f'Could not DM {member.mention}.')
            return

        user_logs = ModLogsByUser(member)
        await user_logs.add_log(ctx.author.id, 'Direct Message', reason, 0, 0)
        await self.bot.embed_success(ctx, f'Sent DM to {member.mention}: {reason}')

    @commands.command(
        brief=' <user> *opt<reason>',
        aliases=['w'],
        description='Formally warns a user, creates a new modlogs entry and DMs them the reason. Requires '
                    '<required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def warn(self, ctx: commands.Context, user: User, *, reason: str = 'No reason given.'):
        member = await self.bot.get_or_fetch_member(user.id)
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 1:
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Warn', reason, 0, 0)
        await self.bot.add_modstat(ctx.author.id, 'Warn')
        try:
            await user.send(embed=Embed(
                colour=0xf04a47, description=f'***You were warned in {ctx.guild} for:*** {reason}'))
            await self.bot.embed_success(ctx, f'Warned {user.mention}: {reason}')
        except Forbidden:
            await self.bot.embed_success(ctx, f'Warned {user.mention}: {reason} (I could not DM them)')

    @commands.command(
        brief=' <member> *opt<reason>',
        aliases=['k'],
        description='Kicks a member from the guild, creates a new modlogs entry and DMs them the reason. Requires '
                    '<required-role> or higher.',
        extras=3)
    @commands.bot_has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, member: Member, *, reason: str = 'No reason given.'):
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 3:
            return

        user_logs = ModLogsByUser(member)
        await user_logs.add_log(ctx.author.id, 'Kick', reason, 0, 0)
        await self.bot.add_modstat(ctx.author.id, 'Kick')
        try:
            await member.send(embed=Embed(colour=0xf04a47,
                                          description=f'***You were kicked from {ctx.guild} for:*** {reason}'))
            await self.bot.embed_success(ctx, f'Kicked {member.mention}: {reason}')
        except Forbidden:
            await self.bot.embed_success(ctx, f'Kicked {member.mention}: {reason} (I could not DM them)')

        await member.kick()

    @commands.command(
        brief=' <user> <duration> *opt<reason>',
        aliases=['m'],
        description='Puts a user in time-out, creates a new modlogs entry and DMs them the reason. Requires '
                    '<required-role> or higher.',
        extras=3)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(self, ctx: commands.Context, user: User, duration: str, *, reason: str = 'No reason given.'):
        member = await self.bot.get_or_fetch_member(user.id)
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 3:
            return
        elif member and member.is_timed_out():
            await self.bot.embed_error(ctx, f'{user.mention} is already muted.')
            return

        resolved_duration = DurationConverter(duration).get_resolved_duration()
        if not resolved_duration or not 60 <= resolved_duration <= 2419200:
            await self.bot.embed_error(ctx, 'Please specify a valid duration between 1 minute and 28 days.')
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Mute', reason, resolved_duration, 0)
        await self.bot.add_modstat(ctx.author.id, 'Mute')
        lasts_until = floor(utils.utcnow().timestamp() + resolved_duration)

        try:
            await user.send(embed=Embed(colour=0xf04a47,
                                        description=f'***You were muted in {ctx.guild} until <t:{lasts_until}:F> '
                                                    f'for:*** {reason}'))

            await self.bot.embed_success(
                ctx, f'Muted {user.mention} for `{time_d(seconds=resolved_duration)}`: {reason}')
        except Forbidden:
            await self.bot.embed_success(
                ctx, f'Muted {user.mention} for `{time_d(seconds=resolved_duration)}`: {reason} (I could not DM them)')

        if member:
            await member.timeout(time_d(seconds=resolved_duration))

    @commands.command(
        brief=' <user> <duration> *opt<reason>',
        aliases=['b'],
        description='Bans a user from the guild, creates a new modlogs entry and DMs them the reason. Duration can be '
                    '`perm` to make the ban permanent (lasts a very long time!). Requires <required-role> or higher.',
        extras=3)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, user: User, duration: str, *, reason: str = 'No reason given.'):
        member = await self.bot.get_or_fetch_member(user.id)
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 3:
            return
        elif user.id in self.bot.banned_user_ids:
            await self.bot.embed_error(ctx, f'{user.mention} is already banned.')
            return

        resolved_duration = DurationConverter(duration).get_resolved_duration()
        if not resolved_duration or resolved_duration < 60:
            await self.bot.embed_error(ctx, 'Please specify a valid duration greater than 1 minute.')
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Ban', reason, resolved_duration, 0)
        await self.bot.add_modstat(ctx.author.id, 'Ban')
        lasts_until = floor(utils.utcnow().timestamp() + resolved_duration)

        if resolved_duration == 1000000000:
            description = f'***You were permanently banned from {self.bot.guild} for:*** {reason}'
        else:
            description = f'***You were banned from {self.bot.guild} until <t:{lasts_until}:F> for:*** {reason}'

        try:
            ban_embed = Embed(colour=0xf04a47, description=description)
            ban_embed.set_footer(text=f'Guild ID: {self.bot.guild.id}')
            message = await user.send(embed=ban_embed)
            await message.edit(view=BanAppealButton(self.bot, message))

            await self.bot.embed_success(
                ctx, f'Banned {user.mention} for `{time_d(seconds=resolved_duration)}`: {reason}')

        except Forbidden:
            await self.bot.embed_success(
                ctx, f'Banned {user.mention} for `{time_d(seconds=resolved_duration)}`: {reason} (I could not DM them)')

        await self.bot.guild.ban(user)

    @commands.command(
        brief=' <user> <duration> <channel> *opt<reason>',
        aliases=['cb'],
        description='Blocks a user from viewing a specified guild channel, creates a new modlogs entry and DMs them '
                    'the reason. Requires <required-role> or higher.',
        extras=4)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def channelban(self, ctx: commands.Context, user: User, channel: abc.GuildChannel, duration: str, *,
                         reason: str = 'No reason given.'):
        member = await self.bot.get_or_fetch_member(user.id)
        if self.bot.member_clearance(member) or self.bot.member_clearance(ctx.author) < 4:
            return
        elif channel.overwrites_for(user).view_channel is False:
            await self.bot.embed_error(ctx, f'{user.mention} is already blocked from viewing {channel.mention}.')
            return

        resolved_duration = DurationConverter(duration).get_resolved_duration()
        if not resolved_duration or resolved_duration < 60:
            await self.bot.embed_error(ctx, 'Please specify a valid duration greater than 1 minute.')
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Channel Ban', reason, resolved_duration, channel.id)
        await self.bot.add_modstat(ctx.author.id, 'Channel Ban')
        lasts_until = floor(utils.utcnow().timestamp() + resolved_duration)

        if resolved_duration == 1000000000:
            description = f'***You were permanently blocked from viewing `#{channel.name}` in {self.bot.guild} ' \
                          f'for:*** {reason}'
        else:
            description = f'***You were blocked from viewing `#{channel.name}` in {self.bot.guild} until ' \
                          f'<t:{lasts_until}:F> for:*** {reason}'

        try:
            await user.send(embed=Embed(colour=0xf04a47, description=description))
            await self.bot.embed_success(
                ctx, f'Blocked {user.mention} from {channel.mention} for `{time_d(seconds=resolved_duration)}`: '
                     f'{reason}')
        except Forbidden:
            await self.bot.embed_success(
                ctx, f'Blocked {user.mention} from {channel.mention} for `{time_d(seconds=resolved_duration)}`: '
                     f'{reason} (I could not DM them)')

        if member:
            await channel.set_permissions(member, view_channel=False)

    @commands.command(
        brief=' <member> *opt<reason>',
        aliases=['um'],
        description='Unmutes a member who\'s in time-out, creates a new modlogs entry and DMs them the reason. Requires'
                    ' <required-role> or higher.',
        extras=5)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self, ctx: commands.Context, member: Member, *, reason: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        elif not member.is_timed_out():
            await self.bot.embed_error(ctx, f'{member.mention} is not timed out.')
            return

        user_logs = ModLogsByUser(member)
        await user_logs.add_log(ctx.author.id, 'Unmute', reason, 0, 0)
        await user_logs.remove_ongoing_logs('Mute', 0)

        try:
            await member.send(embed=Embed(
                colour=0xf04a47, description=f'***You were unmuted in {self.bot.guild} for:*** {reason}'))
            await self.bot.embed_success(ctx, f'Unmuted {member.mention}: {reason}')
        except Forbidden:
            await self.bot.embed_success(ctx, f'Unmuted {member.mention}: {reason} (I could not DM them)')

        await member.timeout(None)

    @commands.command(
        brief=' <user> *opt<reason>',
        aliases=['ub'],
        description='Unbans a user from the guild, creates a new modlogs entry and DMs them the reason. Requires '
                    '<required-role> or higher.',
        extras=6)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx: commands.Context, user: User, *, reason: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif user.id not in self.bot.banned_user_ids:
            await self.bot.embed_error(ctx, f'{user.mention} is not banned.')
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Unban', reason, 0, 0)
        await user_logs.remove_ongoing_logs('Ban', 0)

        try:
            await user.send(embed=Embed(
                colour=0xf04a47, description=f'***You were unbanned from {self.bot.guild} for:*** {reason}'))
            await self.bot.embed_success(ctx, f'Unbanned {user.mention}: {reason}')
        except Forbidden:
            await self.bot.embed_success(ctx, f'Unbanned {user.mention}: {reason} (I could not DM them)')

        await self.bot.guild.unban(user)

    @commands.command(
        brief=' <user> <channel> *opt<reason>',
        aliases=['ucb'],
        description='Unblocks a user from a specified guild channel, creates a new modlogs entry and DMs them the '
                    'reason. Requires <required-role> or higher.',
        extras=5)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unchannelban(self, ctx: commands.Context, user: User, channel: abc.GuildChannel, *,
                           reason: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        elif channel.overwrites_for(user).view_channel is not False:
            await self.bot.embed_error(ctx, f'{user.mention} is not blocked from viewing {channel.mention}.')
            return

        user_logs = ModLogsByUser(user)
        await user_logs.add_log(ctx.author.id, 'Channel Unban', reason, 0, channel.id)
        await user_logs.remove_ongoing_logs('Channel Ban', channel.id)

        try:
            await user.send(embed=Embed(
                colour=0xf04a47,
                description=f'***You were unblocked from viewing `#{channel}` in {self.bot.guild} for:*** {reason}'))
            await self.bot.embed_success(ctx, f'Unblocked {user.mention} from {channel.mention}: {reason}')
        except Forbidden:
            await self.bot.embed_success(ctx, f'Unblocked {user.mention} from {channel.mention}: {reason} '
                                              f'(I could not DM them)')

        if ctx.guild.get_member(user.id):
            await channel.set_permissions(self.bot.guild.get_member(user.id), overwrite=None)

    @commands.command(
        brief=' <check> <amount>',
        description='Purge the most recent `X` messages that pass a specific check. This check can be a specified user,'
                    ' `bots` to target all bot messages, `self` to target this bot\'s own messages or `all` to target '
                    'all messages. Requires <required-role> or higher.',
        extras=4)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.guild_only()
    async def purge(self, ctx: commands.Context, check: Union[User, str], count: int):
        if (type(check) == User and await self.bot.get_or_fetch_member(check.id)) or \
                self.bot.member_clearance(ctx.author) < 4:
            return
        elif not 0 < count <= 100:
            await self.bot.embed_error(ctx, 'Enter a valid amount between 1 and 100.')
            return

        purge_limit = 0

        if type(check) == User:
            await ctx.message.delete()

            def author_is_user(message: Message):
                return message.author.id == check.id

            user_message_count = 0
            async for channel_message in ctx.channel.history(limit=1500):
                purge_limit += 1
                if channel_message.author.id == check.id:
                    user_message_count += 1
                if user_message_count == count:
                    break

            purged_messages = await ctx.channel.purge(limit=purge_limit, check=author_is_user)

        elif check.lower() == 'bots':
            await ctx.message.delete()

            def author_is_bot(message: Message):
                return message.author.bot

            bot_message_count = 0
            async for channel_message in ctx.channel.history(limit=1500):
                purge_limit += 1
                if channel_message.author.bot:
                    bot_message_count += 1
                if bot_message_count == count:
                    break

            purged_messages = await ctx.channel.purge(limit=purge_limit, check=author_is_bot)

        elif check.lower() == 'self':
            await ctx.message.delete()

            def author_is_me(message: Message):
                return message.author.id == self.bot.user.id

            self_message_count = 0
            async for channel_message in ctx.channel.history(limit=1500):
                purge_limit += 1
                if channel_message.author.id == self.bot.user.id:
                    self_message_count += 1
                if self_message_count == count:
                    break

            purged_messages = await ctx.channel.purge(limit=purge_limit, check=author_is_me)

        elif check.lower() == 'all':
            await ctx.message.delete()

            purged_messages = await ctx.channel.purge(limit=count)

        else:
            await self.bot.embed_error(ctx, 'Please specify a valid check and amount. (Limit: 100)')
            return

        await ctx.send(embed=Embed(
            colour=0x43b582, description=f'*Successfully purged {len(purged_messages)} messages.*'), delete_after=5)

    @commands.command(
        brief=' <duration>',
        aliases=['sm'],
        description='Sets a slow-mode timer for the current channel. Type `off` to disable entirely. Requires '
                    '<required-role> or higher.',
        extras=5)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(self, ctx: commands.Context, duration: str):
        if self.bot.member_clearance(ctx.author) < 5:
            return

        if duration.lower() == 'off':
            await ctx.channel.edit(slowmode_delay=0)
            await self.bot.embed_success(ctx, 'Slowmode disabled.')
            return

        resolved_duration = DurationConverter(duration).get_resolved_duration()
        if not resolved_duration or not 1 <= resolved_duration <= 21600:
            await self.bot.embed_error(ctx, 'Specify a valid duration between 1 second and 6 hours.')
            return

        await ctx.channel.edit(slowmode_delay=resolved_duration)
        await self.bot.embed_success(ctx, f'Slowmode set to `{time_d(seconds=resolved_duration)}`.')

    @commands.command(
        brief=' opt<channel>',
        description='Locks a channel, preventing all non-staff users from communicating in it. Requires <required-role>'
                    ' or higher.',
        extras=5)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def lock(self, ctx: commands.Context, channel: abc.GuildChannel = None):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        elif self.lockdown_mapping:
            await self.bot.embed_error(ctx, 'Guild is currently under lockdown.')
            return

        if not channel:
            channel = ctx.channel
        if channel.id in self.locked_channels:
            await self.bot.embed_error(ctx, f'{channel.mention} is already locked.')
            return

        self.locked_channels.update({channel.id: (channel.overwrites_for(channel.guild.default_role),
                                                  channel.overwrites_for(self.bot.staff),
                                                  channel.overwrites_for(self.bot.helper),
                                                  channel.overwrites_for(self.bot.user))})

        everyone_overwrites = channel.overwrites_for(channel.guild.default_role)
        staff_overwrites = channel.overwrites_for(self.bot.staff)
        helper_overwrites = channel.overwrites_for(self.bot.helper)
        self_overwrites = channel.overwrites_for(self.bot.user)

        everyone_overwrites.update(send_messages=False, add_reactions=False, connect=False,
                                   send_messages_in_threads=False)
        staff_overwrites.update(send_messages=True, add_reactions=True, connect=True, send_messages_in_threads=True)
        helper_overwrites.update(send_messages=True, add_reactions=True, connect=True, send_messages_in_threads=True)
        self_overwrites.update(send_messages=True, add_reactions=True, connect=True, send_messages_in_threads=True)

        await channel.set_permissions(channel.guild.default_role, overwrite=everyone_overwrites)
        await channel.set_permissions(self.bot.staff, overwrite=staff_overwrites)
        await channel.set_permissions(self.bot.helper, overwrite=helper_overwrites)
        await channel.set_permissions(self.bot.user, overwrite=self_overwrites)

        await self.bot.embed_success(ctx, f'{channel.mention} has been locked.')

    @commands.command(
        brief=' opt<channel>',
        description='Unlocks a locked channel, reverting all permission overwrites to their previous states. Requires '
                    '<required-role> or higher.',
        extras=5)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unlock(self, ctx: commands.Context, channel: abc.GuildChannel = None):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        elif self.lockdown_mapping:
            await self.bot.embed_error(ctx, 'Guild is currently under lockdown.')
            return

        if not channel:
            channel = ctx.channel
        if channel.id not in self.locked_channels:
            await self.bot.embed_error(ctx, f'{channel.mention} is not locked.')
            return

        original_overwrites = self.locked_channels[channel.id]
        self.locked_channels.pop(channel.id)

        everyone_overwrites = original_overwrites[0]
        staff_overwrites = original_overwrites[1]
        helper_overwrites = original_overwrites[2]
        self_overwrites = original_overwrites[3]

        await channel.set_permissions(channel.guild.default_role, overwrite=everyone_overwrites)
        await channel.set_permissions(self.bot.staff, overwrite=staff_overwrites)
        await channel.set_permissions(self.bot.helper, overwrite=helper_overwrites)
        await channel.set_permissions(self.bot.user, overwrite=self_overwrites)

        await self.bot.embed_success(ctx, f'{channel.mention} has been unlocked.')

    @commands.command(
        brief='',
        description='Puts the guild under lockdown, denying the `view channel` permission for the `@everyone` role in '
                    'all public channels. Requires <required-role> or higher.',
        extras=6)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def lockdown(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif self.lockdown_mapping:
            await self.bot.embed_error(ctx, 'Guild is already under lockdown.')
            return

        loading_message = await ctx.send('Working...')

        public_channels = [channel for channel in self.bot.guild.channels if
                           channel.overwrites_for(self.bot.guild.default_role).view_channel is not False]

        for channel in public_channels:
            self.lockdown_mapping[channel] = (channel.overwrites_for(self.bot.guild.default_role),
                                              channel.overwrites_for(self.bot.staff),
                                              channel.overwrites_for(self.bot.helper),
                                              channel.overwrites_for(self.bot.user))

            everyone_overwrites = channel.overwrites_for(self.bot.guild.default_role)
            staff_overwrites = channel.overwrites_for(self.bot.staff)
            helper_overwrites = channel.overwrites_for(self.bot.helper)
            self_overwrites = channel.overwrites_for(self.bot.user)

            everyone_overwrites.update(view_channel=False)
            staff_overwrites.update(view_channel=True)
            helper_overwrites.update(view_channel=True)
            self_overwrites.update(view_channel=True)

            await channel.set_permissions(self.bot.guild.default_role, overwrite=everyone_overwrites)
            await channel.set_permissions(self.bot.staff, overwrite=staff_overwrites)
            await channel.set_permissions(self.bot.helper, overwrite=helper_overwrites)
            await channel.set_permissions(self.bot.user, overwrite=self_overwrites)

        await loading_message.delete()
        await self.bot.embed_success(ctx, f'Locked {len(public_channels)} channels.')

    @commands.command(
        brief='',
        description='Removes the guild from lockdown, reverting all affected channel\'s permission overwrites to their '
                    'original states. Requires <required-role> or higher.',
        extras=6)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def lockdownend(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif not self.lockdown_mapping:
            await self.bot.embed_error(ctx, 'Guild is not under lockdown.')
            return

        loading_message = await ctx.send('Working...')

        for channel in self.lockdown_mapping:
            everyone_overwrites = self.lockdown_mapping[channel][0]
            staff_overwrites = self.lockdown_mapping[channel][1]
            helper_overwrites = self.lockdown_mapping[channel][2]
            self_overwrites = self.lockdown_mapping[channel][3]

            await channel.set_permissions(self.bot.guild.default_role, overwrite=everyone_overwrites)
            await channel.set_permissions(self.bot.staff, overwrite=staff_overwrites)
            await channel.set_permissions(self.bot.helper, overwrite=helper_overwrites)
            await channel.set_permissions(self.bot.user, overwrite=self_overwrites)

        await loading_message.delete()
        await self.bot.embed_success(ctx, f'Unlocked {len(self.lockdown_mapping)} channels.')
        self.lockdown_mapping = {}


async def setup(bot):
    await bot.add_cog(PunishmentCommands(bot))
