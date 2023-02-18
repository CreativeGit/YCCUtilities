import logging
from discord.ext import commands
from discord.ext.commands.view import StringView
from discord import (
    Message,
    Member,
    VoiceState,
    abc,
    Embed,
    Forbidden,
    Role,
    HTTPException,
    User,
    Guild,
    utils)
from core.pageviewer import BulkDeletionViewer
from math import floor
from typing import Union
from datetime import timedelta


class EventListeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def warning(message: str):
        logging.warning(f'Could not log event: "{message}" - Missing permissions')

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.guild != self.bot.guild or not message.content.startswith(self.bot.command_prefix) or \
                not self.bot.member_clearance(message.author):
            return

        for faq in await self.bot.faq_commands():
            if message.content and message.content.lower() == f'{self.bot.command_prefix}{faq[0]}':
                try:
                    await message.delete()
                    await message.channel.send(faq[1])
                except Forbidden:
                    logging.warning('Could not send FAQ response - Missing permissions')
                return

        for command in await self.bot.custom_commands():
            if message.content.lower().startswith(f'{self.bot.command_prefix}{command[0]}'):

                ctx = commands.Context(message=message, bot=self.bot, view=StringView(''))
                cor_cmd = self.bot.get_command(command[1])

                try:
                    member = await commands.MemberConverter().convert(ctx, message.content.split(' ')[1])
                except IndexError:
                    help_embed = Embed(
                        colour=0x337fd5,
                        title=f'{self.bot.command_prefix}{command[0]} Command',
                        description=f'This is a user-created custom command. '
                                    f'{command[1].capitalize()}s the specified member'
                                    f'{" for the corresponding duration" if command[3] else " "} '
                                    f'and creates a new entry in their modlogs history. '
                                    f'Requires {self.bot.clearance_mapping()[cor_cmd.extras]} or higher.')

                    help_embed.set_author(name='Help Menu', icon_url=self.bot.user.avatar)
                    help_embed.set_footer(text=f'Use {self.bot.command_prefix}help to view all commands.')

                    help_embed.add_field(name='Reason:', value=f'`{command[2]}`')
                    if command[3]:
                        help_embed.add_field(name='Duration:', value=f'`{timedelta(seconds=command[3])}`')

                    help_embed.add_field(
                        name='Usage:', value=f'`{self.bot.command_prefix}{command[0]} <member>`', inline=False)
                    help_embed.add_field(
                        name='Aliases:', value='`None`', inline=False)

                    await ctx.send(embed=help_embed)
                    return
                except commands.CommandError:
                    await self.bot.embed_error(ctx, 'Member not found.')
                    return

                if command[1] in ['Warn', 'Kick']:
                    await ctx.invoke(cor_cmd, member, reason=command[2])
                elif command[1] in ['Mute', 'Ban']:
                    await ctx.invoke(cor_cmd, member, f'{command[3]}s', reason=command[2])

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        if not self.bot.log_channel or message.author.id == self.bot.user.id or message.guild != self.bot.guild:
            return

        deleted_message_embed = Embed(
            colour=0xf04a47, description=f'{message.author.mention} (In {message.channel.mention})')
        deleted_message_embed.set_author(name='Message Deleted', icon_url=self.bot.user.avatar)
        deleted_message_embed.set_thumbnail(
            url=message.author.avatar if message.author.avatar else message.author.default_avatar)
        deleted_message_embed.set_footer(text=f'User ID: {message.author.id}')
        deleted_message_embed.add_field(name='Message Content:', value=message.content if message.content else '`None`')

        try:
            await self.bot.log_channel.send(embed=deleted_message_embed)
        except Forbidden:
            self.warning('message deleted')

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, payload: list[Message]):
        if not self.bot.log_channel or payload[0].guild != self.bot.guild:
            return

        payload_embed = Embed(colour=0xf04a47, description=f'**{len(payload)} Messages Deleted**')
        payload_embed.set_author(name='Bulk Message Deletion', icon_url=self.bot.user.avatar)
        payload_embed.set_thumbnail(
            url=payload[0].guild.icon if payload[0].guild.icon else self.bot.user.avatar)
        payload_embed.set_footer(text=f'Channel ID: {payload[0].channel.id}')
        payload_embed.add_field(name='Channel:', value=payload[0].channel.mention)

        try:
            message = await self.bot.log_channel.send(embed=payload_embed)
            await message.edit(view=BulkDeletionViewer(message, payload))
        except Forbidden:
            self.warning('bulk message deletion')

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if not self.bot.log_channel or before.author.id == self.bot.user.id or before.guild != self.bot.guild or \
                before.content == after.content:
            return

        edited_message_embed = Embed(
            colour=0x337fd5, description=f'{after.author.mention} **([Jump to Message]({after.jump_url}))**')
        edited_message_embed.set_author(name='Message Edited', icon_url=self.bot.user.avatar.url)
        edited_message_embed.set_thumbnail(
            url=after.author.avatar if after.author.avatar else after.author.default_avatar)
        edited_message_embed.set_footer(text=f'User ID: {after.author.id}')
        edited_message_embed.add_field(
            name='Message Content Before:', value=before.content if before.content else '`None`', inline=False)
        edited_message_embed.add_field(
            name='Message Content After:', value=after.content if after.content else '`None`', inline=False)

        try:
            await self.bot.log_channel.send(embed=edited_message_embed)
        except Forbidden:
            self.warning('message edited')

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: Role):
        if not self.bot.log_channel or role.guild != self.bot.guild:
            return

        new_role_embed = Embed(colour=0x43b582, description=role.mention)
        new_role_embed.set_author(name='Role Created', icon_url=self.bot.user.avatar)
        new_role_embed.set_thumbnail(url=role.guild.icon if role.guild.icon else None)
        new_role_embed.set_footer(text=f'Role ID: {role.id}')
        new_role_embed.add_field(name='Role Created:', value=f'<t:{floor(role.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=new_role_embed)
        except Forbidden:
            self.warning('guild role created')

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: Role):
        await self.bot.auto_del_assignment(role.id)
        if not self.bot.log_channel or role.guild != self.bot.guild:
            return

        deleted_role_embed = Embed(colour=0xf04a47, description=f'`{role.name}`')
        deleted_role_embed.set_author(name='Role Deleted', icon_url=self.bot.user.avatar)
        deleted_role_embed.set_thumbnail(url=role.guild.icon if role.guild.icon else None)
        deleted_role_embed.set_footer(text=f'Role ID: {role.id}')
        deleted_role_embed.add_field(name='Role Created:', value=f'<t:{floor(role.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=deleted_role_embed)
        except Forbidden:
            self.warning('guild role deleted')

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role):
        if not self.bot.log_channel or before.guild != self.bot.guild or \
                (before.name == after.name and before.colour == after.colour and before.icon == after.icon):
            return

        role_update_embed = Embed(colour=after.colour, description=after.mention)
        role_update_embed.set_author(name='Role Updated', icon_url=self.bot.user.avatar.url)
        role_update_embed.set_thumbnail(
            url=after.display_icon if after.display_icon else after.guild.icon if after.guild.icon else
            self.bot.user.avatar)
        role_update_embed.set_footer(text=f'Role ID: {after.id}')
        role_update_embed.add_field(name='Before:',
                                    value=f'Name: `{before.name}`\nColour: `#{before.colour}`',
                                    inline=True)
        role_update_embed.add_field(name='After:',
                                    value=f'Name: `{after.name}`\nColour: `#{after.colour}`',
                                    inline=True)
        try:
            await self.bot.log_channel.send(embed=role_update_embed)
        except Forbidden:
            self.warning('guild role updated')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: abc.GuildChannel):
        if not self.bot.log_channel or channel.guild != self.bot.guild:
            return

        new_channel_embed = Embed(colour=0x43b582, description=channel.mention)
        new_channel_embed.set_author(name='Channel Created', icon_url=self.bot.user.avatar)
        new_channel_embed.set_thumbnail(url=channel.guild.icon if channel.guild.icon else None)
        new_channel_embed.set_footer(text=f'Channel ID: {channel.id}')
        new_channel_embed.add_field(name='Channel Created:', value=f'<t:{floor(channel.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=new_channel_embed)
        except Forbidden:
            self.warning('guild channel created')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: abc.GuildChannel):
        if not self.bot.log_channel or channel.guild != self.bot.guild:
            return

        deleted_channel_embed = Embed(colour=0xf04a47, description=f'`{channel.name}`')
        deleted_channel_embed.set_author(name='Channel Deleted', icon_url=self.bot.user.avatar)
        deleted_channel_embed.set_thumbnail(url=channel.guild.icon if channel.guild.icon else None)
        deleted_channel_embed.set_footer(text=f'Channel ID: {channel.id}')
        deleted_channel_embed.add_field(name='Channel Created:', value=f'<t:{floor(channel.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=deleted_channel_embed)
        except Forbidden:
            self.warning('guild channel deleted')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if not self.bot.log_channel or member.guild != self.bot.guild:
            return

        vc_embed = Embed(colour=0xffffff, description=member.mention)
        vc_embed.set_thumbnail(url=member.avatar if member.avatar else member.default_avatar)
        vc_embed.set_footer(text=f'User ID: {member.id}')
        if not before.channel:
            vc_embed.colour = 0x43b582
            vc_embed.set_author(name='Member Joined VC', icon_url=self.bot.user.avatar)
            vc_embed.add_field(name='Joined:', value=after.channel.mention)
        elif not after.channel:
            vc_embed.colour = 0xf04a47
            vc_embed.set_author(name='Member Left VC', icon_url=self.bot.user.avatar)
            vc_embed.add_field(name='Left:', value=before.channel.mention, inline=False)
        elif before.channel != after.channel:
            vc_embed.colour = 0x337fd5
            vc_embed.set_author(name='Member Switched VCs', icon_url=self.bot.user.avatar)
            vc_embed.add_field(name='Before:', value=before.channel.mention, inline=True)
            vc_embed.add_field(name='After:', value=after.channel.mention, inline=True)
        else:
            return

        try:
            await self.bot.log_channel.send(embed=vc_embed)
        except Forbidden:
            self.warning('guild member voice state updated')

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild != self.bot.guild:
            return

        ongoing_logs = await self.bot.ongoing_cases()
        for entry in ongoing_logs:
            if entry[2] == 'Channel Ban' and entry[0] == member.id:
                channel = await self.bot.get_or_fetch_channel(entry[4])
                try:
                    await channel.set_permissions(member, view_channel=False)
                except (Forbidden, HTTPException):
                    logging.warning('Failed to enforce channel-ban on a re-joining member')
            if entry[2] == 'Mute' and entry[0] == member.id:
                try:
                    await member.timeout(timedelta(seconds=floor(entry[3] - utils.utcnow().timestamp())))
                except (Forbidden, HTTPException):
                    logging.warning('Failed to enforce time-out on a re-joining member')

        pers_roles_data = await self.bot.role_assignments('persistent_roles')
        for entry in pers_roles_data:
            if entry[1] == member.id:
                try:
                    role = self.bot.guild.get_role(entry[0])
                    await member.add_roles(role)
                except (Forbidden, HTTPException):
                    logging.warning('Failed to assign new member their persistent role')

        if self.bot.general:
            try:
                await self.bot.general.send(self.bot.welcome_message.replace('<member>', member.mention))
            except (Forbidden, HTTPException):
                logging.warning('Failed to send member welcome message')

        if not self.bot.log_channel:
            return

        member_join_embed = Embed(colour=0x43b582, description=member.mention)
        member_join_embed.set_author(name='Member Joined', icon_url=self.bot.user.avatar)
        member_join_embed.set_thumbnail(url=member.avatar if member.avatar else member.default_avatar)
        member_join_embed.set_footer(text=f'User ID: {member.id}')
        member_join_embed.add_field(name='Account Created:', value=f'<t:{floor(member.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=member_join_embed)
        except Forbidden:
            self.warning('member joined guild')

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if not self.bot.log_channel or member.guild != self.bot.guild:
            return

        member_remove_embed = Embed(colour=0xf04a47, description=member.mention)
        member_remove_embed.set_author(name='Member Left', icon_url=self.bot.user.avatar)
        member_remove_embed.set_thumbnail(url=member.avatar if member.avatar else member.default_avatar)
        member_remove_embed.set_footer(text=f'User ID: {member.id}')
        member_remove_embed.add_field(name='Account Created:', value=f'<t:{floor(member.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=member_remove_embed)
        except Forbidden:
            self.warning('member left guild')

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if not self.bot.log_channel or before.guild != self.bot.guild:
            return

        member_update_embed = Embed(colour=0x337fd5, description=after.mention)
        member_update_embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
        member_update_embed.set_footer(text=f'User ID: {after.id}')

        if before.nick != after.nick:
            member_update_embed.set_author(name='Member Nickname Changed', icon_url=self.bot.user.avatar.url)
            member_update_embed.add_field(name='Before:', value=before.nick if before.nick else before.name)
            member_update_embed.add_field(name='After:', value=after.nick if after.nick else after.name)

        elif not before.is_timed_out() and after.is_timed_out():
            member_update_embed.set_author(name='Member Timed Out', icon_url=self.bot.user.avatar.url)
            member_update_embed.add_field(name='Timed Out Until:',
                                          value=f'<t:{floor(after.timed_out_until.timestamp())}:F>')

        elif before.is_timed_out() and not after.is_timed_out():
            member_update_embed.set_author(name='Member Timeout Removed', icon_url=self.bot.user.avatar.url)
            member_update_embed.add_field(name='Account Created:', value=f'<t:{floor(after.created_at.timestamp())}:F>')

        elif len(before.roles) < len(after.roles):
            member_update_embed.set_author(name='Member Role(s) Added', icon_url=self.bot.user.avatar.url)
            member_update_embed.add_field(name='Role(s):', value=' '.join([role.mention for role in after.roles[1:]
                                                                           if role not in before.roles]))

        elif len(before.roles) > len(after.roles):
            member_update_embed.set_author(name='Member Role(s) Removed', icon_url=self.bot.user.avatar.url)
            member_update_embed.add_field(name='Role(s):', value=' '.join([role.mention for role in before.roles[1:]
                                                                           if role not in after.roles]))

        else:
            return

        try:
            await self.bot.log_channel.send(embed=member_update_embed)
        except Forbidden:
            self.warning('member updated')

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, member: Union[User, Member]):
        if member.id not in self.bot.banned_user_ids:
            self.bot.banned_user_ids.append(member.id)

        if not self.bot.log_channel or guild != self.bot.guild:
            return

        ban_embed = Embed(colour=0xf04a47, description=member.mention)
        ban_embed.set_author(name='Member Banned', icon_url=self.bot.user.avatar)
        ban_embed.set_thumbnail(url=member.avatar if member.avatar else member.default_avatar)
        ban_embed.set_footer(text=f'User ID: {member.id}')
        ban_embed.add_field(name='Account Created:', value=f'<t:{floor(member.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=ban_embed)
        except Forbidden:
            self.warning('user banned')

    @commands.Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        if user.id in self.bot.banned_user_ids:
            self.bot.banned_user_ids.remove(user.id)

        if not self.bot.log_channel or guild != self.bot.guild:
            return

        ban_embed = Embed(colour=0x43b582, description=user.mention)
        ban_embed.set_author(name='User Unbanned', icon_url=self.bot.user.avatar)
        ban_embed.set_thumbnail(url=user.avatar if user.avatar else user.default_avatar)
        ban_embed.set_footer(text=f'User ID: {user.id}')
        ban_embed.add_field(name='Account Created:', value=f'<t:{floor(user.created_at.timestamp())}:F>')
        try:
            await self.bot.log_channel.send(embed=ban_embed)
        except Forbidden:
            self.warning('user unbanned')


async def setup(bot):
    await bot.add_cog(EventListeners(bot))
