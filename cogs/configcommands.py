import logging
from discord.ext import commands
from discord import (
    Embed,
    User,
    TextChannel,
    NotFound,
    HTTPException,
    Forbidden
)
from datetime import timedelta
from core.pageviewer import PageButtons
from core.duration import DurationConverter
from core.miscviews import RulesButtons, RolesView
from json import loads


class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def parse_embed_json(self, ctx: commands.Context):
        try:
            json_file = ctx.message.attachments[0]
            json_data = loads(await json_file.read())
            return [Embed().from_dict(embed) for embed in json_data['embeds']]
        except IndexError:
            await self.bot.embed_error(ctx, 'No attached file found.')
        except KeyError:
            await self.bot.embed_error(ctx, 'Unknown/invalid file.')

    @commands.command(
        brief=' <shortcut> *<response>',
        description='Add a custom FAQ command. The bot will then send the specified response when the command is used. '
                    'Requires <required-role> or higher. The FAQ command itself requires Community Helper or higher.',
        extras=6)
    @commands.guild_only()
    async def addfaq(self, ctx: commands.Context, shortcut: str, *, response: str):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif shortcut.lower() in await self.bot.get_commands():
            await self.bot.embed_error(ctx, 'Shortcut clashes with an existing command/alias.')
            return

        await self.bot.add_faq(shortcut.lower(), response)
        await self.bot.embed_success(
            ctx, f'FAQ command added! Use `{self.bot.command_prefix}{shortcut}` to try it out!')

    @commands.command(
        brief=' <shortcut>',
        description='Remove an existing FAQ command. Requires <required-role> or higher.',
        extras=6)
    @commands.guild_only()
    async def delfaq(self, ctx: commands.Context, shortcut: str):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        elif shortcut.lower() not in [entry[0] for entry in await self.bot.faq_commands()]:
            await self.bot.embed_error(ctx, 'FAQ command not found.')
            return

        await self.bot.del_faq(shortcut.lower())
        await self.bot.embed_success(ctx, f'FAQ command deleted.')

    @commands.command(
        brief='',
        description='View a list of all FAQ commands. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def faqlist(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        current_faqs = await self.bot.faq_commands()
        if not current_faqs:
            await self.bot.embed_error(
                ctx, f'No FAQ commands found. Use `{self.bot.command_prefix}addfaq` to create one!')
            return

        page_count = 1
        embed_pages = {1: Embed(colour=0x337fd5, title='FAQ Commands (Page 1/<page-count>)')}

        field_count = 0
        for faq in current_faqs:
            if len(embed_pages[page_count]) + len(faq[1]) < 5000 and field_count < 7:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages.update({page_count: Embed(
                    colour=0x337fd5, title=f'FAQ Commands (Page {page_count}/<page-count>)')})

            embed_pages[page_count].add_field(name=f'{self.bot.command_prefix}{faq[0]}', value=faq[1], inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages[i].title.replace('<page-count>', str(page_count))
            embed_pages[i].title = new_title

        message = await ctx.send(embed=embed_pages[1])
        await message.edit(view=PageButtons(embed_pages, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' <command-type> <shortcut> <duration> *<reason>',
        description='Set up a custom moderation command. A custom command can be a `warn`, `mute`, `kick` or `ban`. '
                    'A specified duration is still required while creating a `warn` or `kick` command for command '
                    'parsing reasons, but will be disregarded. Requires <required-role> or higher. The custom command '
                    'itself corresponds to the built-in commands in terms of the required role.',
        extras=7)
    @commands.guild_only()
    async def addcustomcommand(self, ctx: commands.Context, logtype: str, shortcut: str, duration: str, *, reason: str):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        elif shortcut.lower() in await self.bot.get_commands():
            await self.bot.embed_error(ctx, 'Shortcut clashes with an existing command/alias.')
            return

        if logtype.lower() in 'warn':
            await self.bot.add_custom_command(shortcut.lower(), 'Warn', reason, 0)
            await self.bot.embed_success(
                ctx, f'Custom command created! Use `{self.bot.command_prefix}{shortcut.lower()}` to try it out.')

        elif logtype.lower() in 'mute':
            resolved_duration = DurationConverter(duration).get_resolved_duration()
            if not resolved_duration or not 60 <= resolved_duration <= 2419200:
                await self.bot.embed_error(ctx, 'Time-outs must be between 1 minute and 28 days.')
            else:
                await self.bot.add_custom_command(shortcut.lower(), 'Mute', reason, resolved_duration)
                await self.bot.embed_success(
                    ctx, f'Custom command created! Use `{self.bot.command_prefix}{shortcut.lower()}` to try it out.')

        elif logtype.lower() in 'kick':
            await self.bot.add_custom_command(shortcut.lower(), 'Kick', reason, 0)
            await self.bot.embed_success(
                ctx, f'Custom command created! Use `{self.bot.command_prefix}{shortcut.lower()}` to try it out.')

        elif logtype.lower() in 'ban':
            resolved_duration = DurationConverter(duration).get_resolved_duration()
            if not resolved_duration:
                await self.bot.embed_error(ctx, 'Please specify a valid duration.')
            else:
                await self.bot.add_custom_command(shortcut.lower(), 'Ban', reason, resolved_duration)
                await self.bot.embed_success(
                    ctx, f'Custom command created! Use `{self.bot.command_prefix}{shortcut.lower()}` to try it out.')
        else:
            await self.bot.embed_error(ctx, 'Custom command type not recognised.')

    @commands.command(
        brief=' <shortcut>',
        description='Removes an existing custom command. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def delcustomcommand(self, ctx: commands.Context, shortcut: str):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        elif shortcut.lower() not in [entry[0] for entry in await self.bot.custom_commands()]:
            await self.bot.embed_error(ctx, 'Custom command not found.')
            return

        await self.bot.del_custom_command(shortcut.lower())
        await self.bot.embed_success(ctx, 'Custom command deleted.')

    @commands.command(
        brief='',
        description='View a list of all custom commands. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def customcommandlist(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        current_custom_cmds = await self.bot.custom_commands()
        if not current_custom_cmds:
            await self.bot.embed_error(
                ctx, f'No custom commands found. Use `{self.bot.command_prefix}addcustomcommand` to create one!')
            return

        page_count = 1
        embed_pages = {1: Embed(colour=0x337fd5, title='Custom Commands (Page 1/<page-count>)')}

        field_count = 0
        for command in current_custom_cmds:
            duration_str = f'\n**Duration:** `{timedelta(seconds=command[3])}`' if command[3] else ''

            if len(embed_pages[page_count]) + len(command[2]) < 5000 and field_count < 7:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages.update({page_count: Embed(
                    colour=0x337fd5, title=f'Custom Commands (Page {page_count}/<page-count>)')})

            embed_pages[page_count].add_field(name=f'{self.bot.command_prefix}{command[0]}',
                                              value=f'**Type:** `{command[1]}`{duration_str}\n**Reason:** {command[2]}',
                                              inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages[i].title.replace('<page-count>', str(page_count))
            embed_pages[i].title = new_title

        message = await ctx.send(embed=embed_pages[1])
        await message.edit(view=PageButtons(embed_pages, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' <blacklist> <user>',
        description='Add a user to one of the bot\'s blacklists. These can be `suggest`, `appeal` or `trivia` and will '
                    'prevent the user from using the respective feature. Requires <required-role> or higher.',
        extras=5)
    @commands.guild_only()
    async def blacklist(self, ctx: commands.Context, blacklist: str, user: User):
        if self.bot.member_clearance(ctx.author) < 5 or \
                self.bot.member_clearance(await self.bot.get_or_fetch_member(user.id)):
            return
        elif blacklist.lower() not in ['suggest', 'appeal', 'trivia']:
            await self.bot.embed_error(ctx, 'Unrecognised blacklist.')
            return
        elif user.id in await self.bot.blacklist(blacklist.lower()):
            await self.bot.embed_error(ctx, f'{user.mention} is already blacklisted.')
            return
        await self.bot.edit_blacklist(blacklist.lower(), 1, user.id)
        await self.bot.embed_success(ctx, f'{user.mention} has been blacklisted.')

    @commands.command(
        brief=' <blacklist> <user>',
        description='Remove a user to one of the bot\'s blacklists. These can be `suggest`, `appeal` or `trivia` and '
                    'will allow the user to use the respective feature again. Requires <required-role> or higher.',
        extras=5)
    @commands.guild_only()
    async def unblacklist(self, ctx: commands.Context, blacklist: str, user: User):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        elif blacklist.lower() not in ['suggest', 'appeal', 'trivia']:
            await self.bot.embed_error(ctx, 'Unrecognised blacklist.')
            return
        elif user.id not in await self.bot.blacklist(blacklist.lower()):
            await self.bot.embed_error(ctx, f'{user.mention} is not blacklisted.')
            return
        await self.bot.edit_blacklist(blacklist.lower(), 0, user.id)
        await self.bot.embed_success(ctx, f'{user.mention} has been unblacklisted.')

    @commands.command(
        brief=' *<message>',
        description='Set a custom welcome message that will be sent when a new member joins the guild. Type `<member>` '
                    'where you want the new member to be mentioned. Requires <required-role> or higher.',
        extras=6)
    @commands.guild_only()
    async def setwelcome(self, ctx: commands.Context, *, message):
        if self.bot.member_clearance(ctx.author) < 6:
            return
        self.bot.welcome_message = message
        await self.bot.embed_success(
            ctx, 'Changed welcome message. (This will have the be re-applied if the bot restarts)')

    @commands.command(
        brief=' opt<text-channel>',
        description='Posts an embedded message in the specified text channel. You can customise an embedded message '
                    '**[here](https://discohook.org/)**, copy the JSON data and save it as a `.json` file. This file '
                    'should be attached to your message whilst invoking the command. Message content and attachments '
                    'are not supported. Requires <required-role> or higher.',
        extras=7)
    async def embed(self, ctx: commands.Context, channel: TextChannel = None):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        elif not channel:
            channel = ctx.channel

        embeds = await self.parse_embed_json(ctx)
        if embeds:
            await channel.send(embeds=embeds)
            await self.bot.embed_success(ctx, 'Embed posted!')

    @commands.command(
        brief=' opt<text-channel>',
        description='Posts an embedded message in the specified text channel with built-in informational buttons '
                    'attached. You can customise an embedded message **[here](https://discohook.org/)**, copy the '
                    'JSON data and save it as a `.json` file. This file should be attached to your message whilst '
                    'invoking the command. Message content and attachments are not currently supported. Requires '
                    '<required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def rulesetup(self, ctx: commands.Context, channel: TextChannel = None):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        elif not channel:
            channel = ctx.channel

        embeds = await self.parse_embed_json(ctx)
        if embeds:
            await channel.send(embeds=embeds, view=RulesButtons(self.bot))
            await self.bot.embed_success(ctx, 'Embed posted!')

    @commands.command(
        brief=' <text-channel> *<role-ids>',
        description='Posts an embedded message in the specified text channel with dynamically-produced role buttons '
                    'attached. These buttons can be pressed by any user to add/remove their respective role. You can '
                    'customise an embedded message **[here](https://discohook.org/)**, copy the JSON data and save it '
                    'as a `.json` file. This file should be attached to your message whilst invoking the command. '
                    'Message content and attachments are not currently supported. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def rolesetup(self, ctx: commands.Context, channel: TextChannel, *, roles: str):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        try:
            role_list = [self.bot.guild.get_role(int(role_id)) for role_id in roles.split(' ')]
        except ValueError:
            await self.bot.embed_error(ctx, 'Invalid/unknown role ID(s) passed.')
            return
        else:
            if None in role_list:
                await self.bot.embed_error(ctx, 'Invalid/unknown role ID(s) passed.')
                return

        embeds = await self.parse_embed_json(ctx)
        if embeds:
            await channel.send(embeds=[emb for emb in embeds], view=RolesView(self.bot, role_list))
            await self.bot.add_pers_role_view(role_list)
            await self.bot.embed_success(ctx, 'Embed posted!')

    @commands.command(
        brief=' <text-channel> <message-id>',
        description='Edits an embedded message sent my the bot, and replaces it with the new embed(s) provided. '
                    'Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def edit(self, ctx: commands.Context, channel: TextChannel, message_id: int):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        try:
            message = await channel.fetch_message(message_id)
        except (NotFound, Forbidden, HTTPException):
            await self.bot.embed_error(ctx, 'Message not found.')
            return

        embeds = await self.parse_embed_json(ctx)
        if embeds:
            try:
                await message.edit(embeds=embeds)
                await self.bot.embed_success(ctx, 'Message edited.')
            except Forbidden:
                await self.bot.embed_error(ctx, 'Could not edit message.')

    @commands.command(
        brief=' <text-channel> <message-id> *<role-ids>',
        description='Edits an embedded message sent by the bot, and replaces the view component  with '
                    'dynamically-produced role buttons. These buttons can be pressed by any user to add/remove their '
                    'respective role. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def editview(self, ctx: commands.Context, channel: TextChannel, message_id: int, *, roles: str):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        try:
            message = await channel.fetch_message(message_id)
        except (NotFound, Forbidden, HTTPException):
            await self.bot.embed_error(ctx, 'Message not found.')
            return

        try:
            role_list = [self.bot.guild.get_role(int(role_id)) for role_id in roles.split(' ')]
        except ValueError:
            await self.bot.embed_error(ctx, 'Invalid/unknown role ID(s) passed.')
            return
        else:
            if None in role_list:
                await self.bot.embed_error(ctx, 'Invalid/unknown role ID(s) passed.')
                return

        try:
            await message.edit(view=RolesView(self.bot, role_list))
            await self.bot.add_pers_role_view(role_list)
            await self.bot.embed_success(ctx, 'Message edited.')
        except Forbidden:
            await self.bot.embed_error(ctx, 'Could not edit message.')

    @commands.command(
        brief='',
        description='View the bot\'s blacklisted and whitelisted URL domains. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def domains(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        urls_embed = Embed(colour=0x337fd5)
        urls_embed.set_author(name='All Domains', icon_url=self.bot.user.avatar)
        urls_embed.add_field(name='Whitelisted Domains:',
                             value=', '.join([f'`{domain}`' for domain in (await self.bot.domain_data())[0]]),
                             inline=False)
        urls_embed.add_field(name='Blacklisted Domains:',
                             value=', '.join([f'`{domain}`' for domain in (await self.bot.domain_data())[1]]),
                             inline=False)
        await ctx.send(embed=urls_embed)

    @commands.command(
        brief=' *<domain>',
        description='Toggles the whitelisting of a URL domain. Requires <required-role> or higher.',
        extras=5)
    @commands.guild_only()
    async def wldomain(self, ctx: commands.Context, *, domain: str):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        await self.bot.domain_wl(domain)
        await self.bot.embed_success(ctx, 'Domain whitelist updated.')

    @commands.command(
        brief=' *<domain>',
        description='Toggles the blacklisting of a URL domain. Requires <required-role> or higher.',
        extras=5)
    @commands.guild_only()
    async def bldomain(self, ctx: commands.Context, *, domain: str):
        if self.bot.member_clearance(ctx.author) < 5:
            return
        await self.bot.domain_bl(domain)
        await self.bot.embed_success(ctx, 'Domain blacklist updated.')

    @commands.command(
        brief=' *<guild-name>',
        description='Resets the guild\'s current data. Useful as a failsafe if a deleted object ID somehow gets '
                    'trapped inside the database. Requires <required-role> or higher. Modlogs, suggestions and '
                    'blacklists are unaffected.',
        extras=9)
    @commands.guild_only()
    async def wipe(self, ctx: commands.Context, *, guild_name: str):
        if self.bot.member_clearance(ctx.author) < 9:
            return
        elif guild_name != self.bot.guild.name:
            await self.bot.embed_error(ctx, 'Please invoke the command followed by the exact guild name to confirm.')
            return
        await self.bot.wipe()
        await self.bot.embed_success(
            ctx, 'Data successfully wiped. (Modlogs, suggestions and blacklists are unaffected.)')

    @commands.command(
        brief='',
        description='Closes the bot\'s connection to Discord. Requires command author to be a guild/bot owner.',
        extras=10)
    @commands.guild_only()
    async def terminate(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) >= 10:
            await self.bot.embed_success(ctx, 'Closing bot...')
            logging.info('Received signal to terminate bot and event loop.')
            await self.bot.close()


async def setup(bot):
    await bot.add_cog(ConfigCommands(bot))
