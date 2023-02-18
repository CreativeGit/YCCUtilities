import logging
from discord.ext import commands, tasks
from discord import (
    Member,
    VoiceState,
    utils,
    Message,
    Embed,
    User,
    Forbidden,
    HTTPException)
from math import floor
from asyncio import sleep
from core.duration import DurationConverter
from datetime import timedelta


class Dictio(dict):
    def sort(self, reverse: bool) -> dict:
        return {a: b for a, b in sorted(self.items(), key=lambda x: x[1], reverse=reverse)}


class UserStatistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_data = []
        self.vc_data_ongoing = []
        self.vc_data_done = []

    def cog_load(self):
        self.cycle_activity_data.start()

    def cog_unload(self):
        self.cycle_activity_data.stop()

    async def sorted_activity_data(self, resolved_duration: int):
        all_stats = await self.bot.activity_stats(resolved_duration)

        messages_by_member = Dictio({})
        for item in all_stats[0]:
            try:
                messages_by_member[item[0]] += 1
            except KeyError:
                messages_by_member[item[0]] = 1
        messages_by_member = messages_by_member.sort(reverse=True)

        messages_by_channel = Dictio({})
        for item in all_stats[0]:
            try:
                messages_by_channel[item[1]] += 1
            except KeyError:
                messages_by_channel[item[1]] = 1
        messages_by_channel = messages_by_channel.sort(reverse=True)

        vc_time_by_member = Dictio({})
        for item in all_stats[1]:
            try:
                vc_time_by_member[item[0]] += item[3] - item[2]
            except KeyError:
                vc_time_by_member[item[0]] = item[3] - item[2]
        vc_time_by_member = vc_time_by_member.sort(reverse=True)

        vc_time_by_channel = Dictio({})
        for item in all_stats[1]:
            try:
                vc_time_by_channel[item[1]] += item[3] - item[2]
            except KeyError:
                vc_time_by_channel[item[1]] = item[3] - item[2]
        vc_time_by_channel = vc_time_by_channel.sort(reverse=True)

        return messages_by_member, messages_by_channel, vc_time_by_member, vc_time_by_channel

    @tasks.loop(seconds=60)
    async def cycle_activity_data(self):
        await self.bot.wait_until_ready()
        await sleep(20)

        for entry in self.message_data:
            await self.bot.add_message_stat(entry[0], entry[1], entry[2])
        for entry in self.vc_data_done:
            await self.bot.add_vc_stat(entry[0], entry[1], entry[2], entry[3])

        try:
            active_role = self.bot.guild.get_role(self.bot.active_role.id)
        except AttributeError:
            active_role = None
        if active_role:
            all_stats = await self.sorted_activity_data(2592000)
            messages_by_member = all_stats[0]
            vc_time_by_member = all_stats[2]

            try:
                top_member_ids_1 = list(messages_by_member)[:10]
            except IndexError:
                top_member_ids_1 = list(messages_by_member)
            try:
                top_member_ids_2 = list(vc_time_by_member)[:10]
            except IndexError:
                top_member_ids_2 = list(vc_time_by_member)
            top_members = set(top_member_ids_1 + top_member_ids_2)

            members_in = [await self.bot.get_or_fetch_member(member) for member in top_members if member not in
                          [member.id for member in active_role.members]]
            members_out = [await self.bot.get_or_fetch_member(member) for member in
                           [member.id for member in active_role.members] if member not in top_members]

            for member in members_in:
                try:
                    await member.add_roles(self.bot.active_role)
                except (Forbidden, HTTPException, AttributeError):
                    logging.warning('Failed to add member\'s active role')
            for member in members_out:
                try:
                    await member.remove_roles(self.bot.active_role)
                except (Forbidden, HTTPException, AttributeError):
                    logging.warning('Failed to remove member\'s active role')

        self.message_data = []
        self.vc_data_done = []

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.author.bot and message.guild == self.bot.guild:
            self.message_data.append((message.author.id, message.channel.id, floor(message.created_at.timestamp())))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot or before.channel == after.channel:
            return
        if not before.channel:
            self.vc_data_ongoing.append((member.id, after.channel.id, floor(utils.utcnow().timestamp())))
        elif not after.channel:
            try:
                joined_log = [entry for entry in self.vc_data_ongoing if entry[0] == member.id][0]
                self.vc_data_ongoing.remove(joined_log)
                self.vc_data_done.append((joined_log[0], joined_log[1], joined_log[2],
                                         floor(utils.utcnow().timestamp())))
            except IndexError:
                logging.warning('Voice state update event ignored due to incomplete data')
        else:
            try:
                joined_log = [entry for entry in self.vc_data_ongoing if entry[0] == member.id][0]
                self.vc_data_ongoing.remove(joined_log)
                self.vc_data_done.append((joined_log[0], joined_log[1], joined_log[2],
                                         floor(utils.utcnow().timestamp())))
                self.vc_data_ongoing.append((member.id, after.channel.id, floor(utils.utcnow().timestamp())))
            except IndexError:
                logging.warning('Voice state update event ignored due to incomplete data')

    @commands.command(
        brief=' opt<time-elapsed>',
        description='View the activity statistics of the top user\'s and channels in the guild.',
        extras=0)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.guild_only()
    async def topstats(self, ctx: commands.Context, duration_since: str = '30d'):
        message = await ctx.send('Loading...')

        resolved_duration = DurationConverter(duration_since).get_resolved_duration()
        if not resolved_duration or not 60 <= resolved_duration <= 315532800:
            resolved_duration = 2592000

        all_stats = await self.sorted_activity_data(resolved_duration)
        messages_by_member = all_stats[0]
        messages_by_channel = all_stats[1]
        vc_time_by_member = all_stats[2]
        vc_time_by_channel = all_stats[3]

        since_time = floor(utils.utcnow().timestamp() - resolved_duration)

        all_stats_embed = Embed(colour=0x337fd5, title=ctx.guild, description=f'**Since <t:{since_time}:F>**')
        all_stats_embed.set_author(name='Top Statistics', icon_url=self.bot.user.avatar)
        all_stats_embed.set_thumbnail(url=ctx.guild.icon if ctx.guild.icon else self.bot.user.avatar)
        all_stats_embed.set_footer(text=f'Try out {self.bot.command_prefix}stats to view your own stats!')

        all_stats_embed.add_field(name='User Messages:',
                                  value='\n'.join([f'> <@{entry}>**: {"{:,}".format(messages_by_member[entry])}**'
                                                   for entry in list(messages_by_member)[:5]]), inline=False)
        all_stats_embed.add_field(name='Channel Messages:',
                                  value='\n'.join([f'> <#{entry}>**: {"{:,}".format(messages_by_channel[entry])}**'
                                                   for entry in list(messages_by_channel)[:5]]), inline=False)
        all_stats_embed.add_field(name='User VC Activity:',
                                  value='\n'.join([f'> <@{entry}>**: `{timedelta(seconds=vc_time_by_member[entry])}`**'
                                                   for entry in list(vc_time_by_member)[:5]]), inline=False)
        all_stats_embed.add_field(name='Channel VC Activity:',
                                  value='\n'.join([f'> <#{entry}>**: `{timedelta(seconds=vc_time_by_channel[entry])}`**'
                                                   for entry in list(vc_time_by_channel)[:5]]), inline=False)
        await message.delete()
        await ctx.send(embed=all_stats_embed)

    @commands.command(
        brief=' opt<user> opt<time-elapsed>',
        description='View your own or another user\'s activity statistics in the guild.',
        extras=0)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.guild_only()
    async def stats(self, ctx: commands.Context, user: User = None, duration_since: str = '30d'):
        message = await ctx.send('Loading...')
        if not user:
            user = ctx.author

        resolved_duration = DurationConverter(duration_since).get_resolved_duration()
        if not resolved_duration or not 60 <= resolved_duration <= 315532800:
            resolved_duration = 2592000

        all_stats = await self.sorted_activity_data(resolved_duration)
        messages_by_member = all_stats[0]
        vc_time_by_member = all_stats[2]

        try:
            messages_rank = list(messages_by_member).index(user.id) + 1
            message_count = messages_by_member[user.id]
        except ValueError:
            messages_rank = 'N/A'
            message_count = 0

        try:
            vc_rank = list(vc_time_by_member).index(user.id) + 1
            vc_time = vc_time_by_member[user.id]
        except ValueError:
            vc_rank = 'N/A'
            vc_time = 0

        since_time = floor(utils.utcnow().timestamp() - resolved_duration)

        stats_embed = Embed(colour=0x337fd5, title=user, description=f'**Since <t:{since_time}:F>**')
        stats_embed.set_author(name='User Statistics', icon_url=self.bot.user.avatar)
        stats_embed.set_thumbnail(url=user.avatar if user.avatar else ctx.guild.icon)
        stats_embed.set_footer(text=f'Try out {self.bot.command_prefix}topstats to view the top users!')

        stats_embed.add_field(name=f'Total Messages (Rank #{messages_rank})',
                              value=f'> **{"{:,}".format(message_count)}**',
                              inline=False)
        stats_embed.add_field(name=f'VC Activity (Rank #{vc_rank})',
                              value=f'> **`{timedelta(seconds=vc_time)}`**',
                              inline=False)

        await message.delete()
        await ctx.send(embed=stats_embed)

    @commands.command(
        brief=' opt<user> opt<time-elapsed>',
        description='View the modstats of a user. Requires <required-role> or higher.',
        extras=6)
    @commands.guild_only()
    async def modstats(self, ctx: commands.Context, user: User = None, duration_since: str = '30d'):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif not user:
            user = ctx.author

        resolved_duration = DurationConverter(duration_since).get_resolved_duration()
        if not resolved_duration or not 60 <= resolved_duration <= 315532800:
            resolved_duration = 2592000

        modstats = await self.bot.modstats(user.id, resolved_duration)

        since_time = floor(utils.utcnow().timestamp() - resolved_duration)

        modstats_embed = Embed(colour=0x337fd5, title=user, description=f'**Since <t:{since_time}:F>**')
        modstats_embed.set_author(name='User Moderation Statistics', icon_url=self.bot.user.avatar)
        modstats_embed.set_thumbnail(url=user.avatar if user.avatar else ctx.guild.icon)

        for item in modstats:
            modstats_embed.add_field(name=f'{item}s', value=f'> `{"{:,}".format(modstats[item])}`')
        modstats_embed.add_field(name='\u200b', value='\u200b')

        await ctx.send(embed=modstats_embed)


async def setup(bot):
    await bot.add_cog(UserStatistics(bot))
