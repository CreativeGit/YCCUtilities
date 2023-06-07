from discord.ext import commands
from discord import (
    Message,
    Embed,
    User,
    Forbidden,
    HTTPException,
    utils)
from datetime import timedelta
from math import floor
from time import time
from typing import Union
from aiogoogletrans import Translator
from aiogoogletrans import LANGUAGES
from asyncio import sleep
from discord.ext.commands.view import StringView
from core.duration import DurationConverter


class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time()
        self.afk_mapping = {}

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot:
            return

        if message.author in self.afk_mapping:
            self.afk_mapping.pop(message.author)
            await self.bot.embed_success(
                commands.Context(message=message, bot=self.bot, view=StringView('')),
                f'Removed {message.author.mention}\'s AFK.')
            if message.author.nick.startswith('[AFK] '):
                try:
                    await message.author.edit(nick=message.author.nick[6:])
                except (HTTPException, Forbidden):
                    pass
            return

        for member in self.afk_mapping:
            if member in message.mentions:
                try:
                    await message.reply(f'*`{member.name}` is AFK: `{self.afk_mapping[member]}`.*', delete_after=6)
                    break
                except Forbidden:
                    break

    @commands.command(
        brief='',
        description='Check the bot\'s current latency.',
        extras=0)
    @commands.guild_only()
    async def ping(self, ctx: commands.Context):
        await ctx.send(embed=Embed(
            colour=0x337fd5, description=f'***Pong! Latency: `{round(self.bot.latency, 3)}s`***'))

    @commands.command(
        brief='',
        description='Check the bot\'s current uptime.',
        extras=0)
    @commands.guild_only()
    async def uptime(self, ctx: commands.Context):
        await ctx.send(embed=Embed(
            colour=0x337fd5, description=f'***Current uptime: `{timedelta(seconds=floor(time() - self.start_time))}`***'
                                         f'\n\n***Online since: <t:{floor(self.start_time)}:F>***'))

    @commands.command(
        brief=' opt<user>',
        aliases=['av'],
        description='View a user\'s global avatar. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def avatar(self, ctx: commands.Context, *, user: User = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        elif not user:
            user = ctx.author

        avatar_embed = Embed(colour=0x337fd5, title=f'{user}\'s avatar:')
        avatar_embed.set_image(url=user.avatar.url if user.avatar else user.default_avatar.url)
        await ctx.send(embed=avatar_embed)

    @commands.command(
        brief=' opt<user>',
        aliases=['ui', 'whois'],
        description='View information about a user. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, *, user: User = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        elif not user:
            user = ctx.author
        member = await self.bot.get_or_fetch_member(user.id)

        bool_dict = {True: '**Yes**', False: '**No**'}

        user_info_embed = Embed(colour=0x337fd5, title=user.name, description=user.mention)

        user_info_embed.set_author(name='User Info', icon_url=self.bot.user.avatar.url)
        user_info_embed.set_thumbnail(url=user.avatar if user.avatar else user.default_avatar)
        user_info_embed.set_footer(text=f'User ID: {user.id}')

        user_info_embed.add_field(name='In Guild:', value=bool_dict[bool(member)], inline=True)

        user_info_embed.add_field(name='Banned:',
                                  value=bool_dict[user.id in self.bot.banned_user_ids],
                                  inline=True)

        user_info_embed.add_field(name='Muted:',
                                  value='**`None`**' if not member else bool_dict[member.is_timed_out()],
                                  inline=True)

        user_info_embed.add_field(name=f'Roles: [{len(member.roles) - 1 if member else 0}]',
                                  value='**`None`**' if not member or len(member.roles) < 2 else
                                  ' '.join([role.mention for role in member.roles[1:]]),
                                  inline=False)

        user_info_embed.add_field(name='Created At:',
                                  value=f'<t:{floor(user.created_at.timestamp())}:F>',
                                  inline=True)

        user_info_embed.add_field(name='Joined Guild On:',
                                  value=f'<t:{floor(member.joined_at.timestamp())}:F>' if member else '**`None`**',
                                  inline=True)

        perm_level = self.bot.member_clearance(member)
        user_info_embed.add_field(name='Guild Permission Level:',
                                  value=f'`Level {perm_level}` **({self.bot.clearance_mapping()[perm_level]})**',
                                  inline=False)

        await ctx.send(embed=user_info_embed)

    @commands.command(
        brief='',
        aliases=['si'],
        description='View information about the guild. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        guild = self.bot.guild

        guild_info_embed = Embed(colour=0x337fd5, title=guild)

        guild_info_embed.set_author(name='Server Info', icon_url=self.bot.user.avatar.url)
        guild_info_embed.set_thumbnail(url=guild.icon.url if guild.icon else self.bot.user.avatar.url)
        guild_info_embed.set_footer(text=f'Guild ID: {guild.id}')

        guild_info_embed.add_field(name='Owner:', value=guild.owner.mention, inline=True)

        guild_info_embed.add_field(name='Member Count:', value=f'**{len(guild.members)}**', inline=True)

        guild_info_embed.add_field(name='Bot Count:',
                                   value=f'**{len([member for member in guild.members if member.bot])}**',
                                   inline=True)

        guild_info_embed.add_field(name='Text Channels:',
                                   value=f'**{len(guild.text_channels)}**',
                                   inline=True)

        guild_info_embed.add_field(name='Voice Channels:',
                                   value=f'**{len(guild.voice_channels)}**',
                                   inline=True)

        guild_info_embed.add_field(name='Category Channels:',
                                   value=f'**{len(guild.categories)}**',
                                   inline=True)

        role_list = [role.mention for role in guild.roles[1:]]
        role_list.reverse()

        extra_roles_str = ''

        if len(role_list) > 15:
            role_list = role_list[:15]

            extra_roles_str = f'**. . . (+ {len(guild.roles) - 16} more)**'

        guild_info_embed.add_field(name=f'Roles: [{len(guild.roles) - 1}]',
                                   value=f'{" ".join(role_list)} {extra_roles_str}',
                                   inline=False)

        guild_info_embed.add_field(name='Created At:',
                                   value=f'<t:{floor(guild.created_at.timestamp())}:F>',
                                   inline=False)

        await ctx.send(embed=guild_info_embed)

    @commands.command(
        brief=' opt<target-lang> *opt<message>',
        aliases=['t'],
        description='Translate the contents of a message into another language. The default target language is `en` '
                    '(English), and `<message>` can be a message ID, link or just the contents you wish to translate. '
                    'The command can also be invoked whilst replying to another message to translate the contents of '
                    'that message. Requires <required-role> or higher.',
        extras=1)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.guild_only()
    async def translate(self, ctx: commands.Context, target: str = 'en', *, message: Union[Message, str] = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        elif ctx.message.reference:
            message_object = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            quote = message_object.content
        elif type(message) == Message:
            quote = message.content
        else:
            quote = message

        if target.lower() not in LANGUAGES.keys():
            target = 'en'

        translation = await Translator().translate(quote, dest=target.lower())

        translation_embed = Embed(colour=0x337fd5, title='Translation Results')

        if ctx.message.reference:
            message_object = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            translation_embed.description = f'**[Message Link]({message_object.jump_url})**'
        elif type(message) == Message:
            translation_embed.description = f'**[Message Link]({message.jump_url})**'

        translation_embed.add_field(name='Detected Language:', value=LANGUAGES[translation.src].capitalize(),
                                    inline=True)
        translation_embed.add_field(name='Target Language:', value=LANGUAGES[translation.dest].capitalize(),
                                    inline=True)
        translation_embed.add_field(name='Original Message:', value=quote, inline=False)
        translation_embed.add_field(name='Translated Message:', value=translation.text, inline=False)

        await ctx.send(embed=translation_embed)

    @commands.command(
        brief=' opt<message>',
        description='"Quote" a message, recreating the contents of the message. You can specify a message ID/link or '
                    'reply to the message you wish to quote. Requires <required-role> or higher.',
        extras=1)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.guild_only()
    async def quote(self, ctx, message: Message = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        elif ctx.message.reference:
            quoted_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        else:
            quoted_message = message

        quote_embed = Embed(
            colour=0x337fd5,
            description=f'***"{quoted_message.content}"***\n\n- Said by {quoted_message.author.mention} on '
                        f'<t:{int(round(quoted_message.created_at.timestamp()))}:F>.')

        await ctx.channel.send(embed=quote_embed)
        await ctx.message.delete()

    @commands.command(
        brief=' <duration> *<reason>',
        description='Set a reminder and have the bot DM you after the specified duration has passed. Requires '
                    '<required-role> or higher.',
        extras=1)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.guild_only()
    async def remind(self, ctx, duration: str, *, reminder: str):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        time_now = time()

        resolved_duration = DurationConverter(duration).get_resolved_duration()

        if not resolved_duration or resolved_duration < 1:
            await self.bot.embed_error(ctx, 'Please specify a valid duration.')
            return

        await self.bot.embed_success(ctx, f'Done! I will attempt to remind you '
                                          f'<t:{floor(utils.utcnow().timestamp() + resolved_duration)}:R>.')

        await sleep(resolved_duration)

        try:
            await ctx.author.send(embed=Embed(
                colour=0x337fd5,
                description=f'***You asked me on <t:{floor(time_now)}:F> to remind you about:*** {reminder}'))
        except Forbidden:
            pass

    @commands.command(
        brief=' *<reason>',
        description='Set your status as AFK. The bot will then notify any user who tries to ping you that you\'re AFK. '
                    'AFK status is removed when you next send a message. Requires <required-role> or higher.',
        extras=1)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def afk(self, ctx: commands.Context, *, reason: str = 'No reason given'):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        await self.bot.embed_success(ctx, f'Set status to AFK: `{reason}`.')
        try:
            await ctx.author.edit(nick=f'[AFK] {ctx.author.nick}' if ctx.author.nick else f'[AFK] {ctx.author.name}')
        except (Forbidden, HTTPException):
            pass
        await sleep(2)
        self.afk_mapping.update({ctx.author: reason})


async def setup(bot):
    await bot.add_cog(InfoCommands(bot))
