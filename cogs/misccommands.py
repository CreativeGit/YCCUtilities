from discord.ext import commands
from discord import (
    Role,
    User,
    Embed,
    HTTPException,
    Forbidden,
    Button,
    ButtonStyle,
    Message,
    Interaction,
    ui,
    utils,
    TextChannel)
from core.pageviewer import PageButtons
from core.duration import DurationConverter
from ast import literal_eval as l_e
from math import floor
from asyncio import sleep
from random import sample


class SuggestionButtons(ui.View):
    def __init__(self, bot, message: Message, suggestion_id: int):
        super().__init__(timeout=604800)
        self.bot = bot
        self.message = message
        self.suggestion_id = suggestion_id

    @staticmethod
    async def update_suggestion_embed(interaction: Interaction, approvals: int, declines: int):
        suggestion_embed = interaction.message.embeds[0]

        for i in range(2):
            suggestion_embed.remove_field(-1)

        suggestion_embed.add_field(name='Upvotes:', value=f'> {approvals}', inline=True)
        suggestion_embed.add_field(name='Downvotes:', value=f'> {declines}', inline=True)

        await interaction.message.edit(embed=suggestion_embed)

    @ui.button(label='I Agree', emoji='<:tick:1051065037659312209>', style=ButtonStyle.green)
    async def agree(self, interaction: Interaction, button: Button):
        suggestion_data = await self.bot.get_suggestion(self.suggestion_id)

        approvals = l_e(suggestion_data[4])
        declines = l_e(suggestion_data[5])

        total_approvals = len(approvals)
        total_declines = len(declines)

        if interaction.user.id in approvals:
            await self.bot.send_ephemeral_response(
                interaction, '❌ You\'ve already upvoted this suggestion.', 0xf04a47)
            return

        await self.bot.suggestion_vote(self.suggestion_id, 'approvals', 1, interaction.user.id)
        total_approvals += 1

        if interaction.user.id in declines:
            await self.bot.suggestion_vote(self.suggestion_id, 'declines', 0, interaction.user.id)
            total_declines -= 1

        await self.bot.send_ephemeral_response(interaction, '*Suggestion upvoted.*', 0x43b582)
        await self.update_suggestion_embed(interaction, total_approvals, total_declines)

    @ui.button(label='I Disagree', emoji='<:no:1051064861565657108>', style=ButtonStyle.red)
    async def disagree(self, interaction: Interaction, button: Button):
        suggestion_data = await self.bot.get_suggestion(self.suggestion_id)

        approvals = l_e(suggestion_data[4])
        declines = l_e(suggestion_data[5])

        total_approvals = len(approvals)
        total_declines = len(declines)

        if interaction.user.id in declines:
            await self.bot.send_ephemeral_response(
                interaction, '❌ You\'ve already downvoted this suggestion.', 0xf04a47)
            return

        await self.bot.suggestion_vote(self.suggestion_id, 'declines', 1, interaction.user.id)
        total_declines += 1

        if interaction.user.id in approvals:
            await self.bot.suggestion_vote(self.suggestion_id, 'approvals', 0, interaction.user.id)
            total_approvals -= 1

        await self.bot.send_ephemeral_response(interaction, '*Suggestion downvoted.*', 0x43b582)
        await self.update_suggestion_embed(interaction, total_approvals, total_declines)

    async def on_timeout(self):
        self.agree.disabled = True
        self.disagree.disabled = True
        await self.message.edit(view=self)


class GiveawayButton(ui.View):
    def __init__(self, bot, message: Message, winners: int, duration: int, description: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.winners = winners
        self.duration = duration
        self.description = description
        self.entries = []

    @ui.button(label='Enter!', emoji='<:partypopper:733421037168885840>', style=ButtonStyle.green)
    async def enter(self, interaction: Interaction, button: Button):
        if interaction.user in self.entries:
            await self.bot.send_ephemeral_response(interaction, '❌ You already entered this giveaway.', 0xf04a47)
            return
        self.entries.append(interaction.user)
        await self.bot.send_ephemeral_response(interaction, 'Giveaway entered!', 0x43b582)

    async def expire(self):
        await sleep(self.duration)

        self.stop()
        self.enter.disabled = True
        await self.message.edit(view=self)

        winners = sample(self.entries, self.winners)
        await self.message.reply(
            f'Congratulations {", ".join([u.mention for u in winners])}, you won a giveaway: {self.description}!')


class MiscCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief=' <user> <role>',
        description='Add a persistent role to a user. This role is then automatically re-added if they leave and '
                    're-join the guild. Note: role is not added when the command is initially used. Requires '
                    '<required-role> or higher.',
        extras=4)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def addpersrole(self, ctx: commands.Context, user: User, role: Role):
        if self.bot.member_clearance(ctx.author) < 4:
            return
        elif role > (await self.bot.bot_member()).top_role or role == self.bot.guild.premium_subscriber_role or \
                role == self.bot.guild.default_role:
            await self.bot.embed_error(ctx, 'Pick another role.')
            return

        existing_pers_roles = await self.bot.role_assignments('persistent_roles')
        for entry in existing_pers_roles:
            if entry == (role.id, user.id):
                await self.bot.embed_error(
                    ctx, f'{user.mention} already has {role.mention} assigned as a persistent role.')
                return

        await self.bot.add_role_assignment('persistent_roles', role.id, user.id)
        await self.bot.embed_success(ctx, f'Persistent role added for {user.mention}.')

    @commands.command(
        brief=' <user> <role>',
        description='Remove a persistent role assignment from a user. Requires <required-role> or higher.',
        extras=4)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def delpersrole(self, ctx: commands.Context, user: User, role: Role):
        if self.bot.member_clearance(ctx.author) < 4:
            return

        existing_pers_roles = await self.bot.role_assignments('persistent_roles')
        if (role.id, user.id) not in existing_pers_roles:
            await self.bot.embed_error(ctx, 'This persistent role assignment does not exist.')
            return
        await self.bot.del_role_assignment('persistent_roles', role.id, user.id)
        await self.bot.embed_success(ctx, f'Persistent role assignment deleted.')

    @commands.command(
        brief='',
        description='View a list of all persistent role assignments. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def listpersroles(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        persistent_role_data = await self.bot.role_assignments('persistent_roles')
        if not persistent_role_data:
            await self.bot.embed_error(
                ctx, f'No persistent roles found. Use `{self.bot.command_prefix}addpersrole` to add one!')
            return

        page_count = 1
        embed_pages = {1: Embed(colour=0x337fd5, title='Persistent Roles (Page 1/<page-count>)')}

        field_count = 0
        for entry in persistent_role_data:

            if field_count < 7:
                field_count += 1
            else:
                page_count += 1
                field_count = 1

                embed_pages.update({page_count: Embed(
                    colour=0x337fd5, title=f'Persistent Roles (Page {page_count}/<page-count>)')})

            embed_pages[page_count].add_field(
                name='Persistent Role', value=f'**User:** <@{entry[1]}> (ID: {entry[1]})\n'
                                              f'**Role:** <@&{entry[0]}> (ID: {entry[0]})', inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages[i].title.replace('<page-count>', str(page_count))
            embed_pages[i].title = new_title

        message = await ctx.send(embed=embed_pages[1])
        await message.edit(view=PageButtons(embed_pages, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' <user> <role>',
        description='Add a custom role to a user. The user can then use the `editcustomrole` command to edit the colour'
                    ' and name of this role without requiring the `manage roles` permission. Each user can only have '
                    'a single custom role, and each custom role only one user. Note: role is not added when the '
                    'command is initially used. Requires <required-role> or higher.',
        extras=4)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def addcustomrole(self, ctx: commands.Context, user: User, role: Role):
        if self.bot.member_clearance(ctx.author) < 4:
            return
        elif role > (await self.bot.bot_member()).top_role or role == self.bot.guild.premium_subscriber_role or \
                role == self.bot.guild.default_role:
            await self.bot.embed_error(ctx, 'Pick another role.')
            return

        existing_custom_roles = await self.bot.role_assignments('custom_roles')
        for entry in existing_custom_roles:
            if user.id in entry:
                await self.bot.embed_error(ctx, f'{user.mention} already has an assigned custom role.')
                return
            elif role.id in entry:
                await self.bot.embed_error(ctx, f'{role.mention} is already assigned as <@{entry[1]}>\'s custom role.')
                return

        await self.bot.add_role_assignment('custom_roles', role.id, user.id)
        await self.bot.embed_success(ctx, f'Custom role added for {user.mention}.')

    @commands.command(
        brief=' <user> <role>',
        description='Remove a custom role assignment from a user. Requires <required-role> or higher.',
        extras=4)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def delcustomrole(self, ctx: commands.Context, user: User, role: Role):
        if self.bot.member_clearance(ctx.author) < 4:
            return

        existing_custom_roles = await self.bot.role_assignments('custom_roles')
        if (role.id, user.id) not in existing_custom_roles:
            await self.bot.embed_error(ctx, 'This custom role assignment does not exist.')
            return

        await self.bot.del_role_assignment('custom_roles', role.id, user.id)
        await self.bot.embed_success(ctx, f'Custom role assignment deleted.')

    @commands.command(
        brief='',
        description='View a list of all custom role assignments. Requires <required-role> or higher.',
        extras=1)
    @commands.guild_only()
    async def listcustomroles(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        custom_role_data = await self.bot.role_assignments('custom_roles')
        if not custom_role_data:
            await self.bot.embed_error(
                ctx, f'No custom roles found. Use `{self.bot.command_prefix}addcustomrole` to add one!')
            return

        page_count = 1
        embed_pages = {1: Embed(colour=0x337fd5, title='Custom Roles (Page 1/<page-count>)')}

        field_count = 0
        for entry in custom_role_data:

            if field_count < 7:
                field_count += 1
            else:
                page_count += 1
                field_count = 1

                embed_pages.update({page_count: Embed(
                    colour=0x337fd5, title=f'Custom Roles (Page {page_count}/<page-count>)')})

            embed_pages[page_count].add_field(
                name='Custom Role', value=f'**User:** <@{entry[1]}> (ID: {entry[1]})\n'
                                          f'**Role:** <@&{entry[0]}> (ID: {entry[0]})', inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages[i].title.replace('<page-count>', str(page_count))
            embed_pages[i].title = new_title

        message = await ctx.send(embed=embed_pages[1])
        await message.edit(view=PageButtons(embed_pages, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' <hex> *<name>',
        description='Edit a custom role assigned by a staff member. `<hex>` should be a 6-digit hexadecimal number, '
                    'with or without the leading `#`.',
        extras=0)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def editcustomrole(self, ctx: commands.Context, new_hex: str, *, new_name: str):
        custom_roles = await self.bot.role_assignments('custom_roles')
        user_custom_role = None

        for entry in custom_roles:
            if entry[1] == ctx.author.id:
                user_custom_role = ctx.guild.get_role(entry[0])

        if not user_custom_role:
            await self.bot.embed_error(ctx, 'Custom role not found/does not exist')
            return

        try:
            new_colour_int = int(new_hex.strip('#'), 16)
        except ValueError:
            await self.bot.embed_error(ctx, 'Please specify a valid 6-digit hex code.')
            return

        try:
            await user_custom_role.edit(name=new_name, colour=new_colour_int)
            await self.bot.embed_success(ctx, f'Successfully edited {user_custom_role.mention}.')
        except HTTPException:
            await self.bot.embed_error(ctx, 'Something went wrong. (Name was too long or colour was out of range)')

    @commands.command(
        brief=' *<suggestion>',
        description='Submit a suggestion to the guild. This is then posted as an embed in the guild\'s suggestions '
                    'channel where members can vote, and staff members can approve or decline the suggestion.',
        extras=0)
    @commands.cooldown(1, 21600, commands.BucketType.member)
    @commands.guild_only()
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        if ctx.author.id in await self.bot.blacklist('suggest'):
            await self.bot.embed_error(ctx, 'You\'ve been blacklisted from posting suggestions in this guild.')
            return

        try:
            suggestion_message = await self.bot.suggest_channel.send(embed=Embed(colour=0x337fd5, description='\u200b'))
        except (HTTPException, Forbidden, AttributeError):
            await self.bot.embed_error(ctx, 'Something went wrong. Please contact a server staff member.')
            return

        suggestion_id = await self.bot.add_suggestion(suggestion_message.id, ctx.author.id, suggestion)

        suggestion_embed = Embed(colour=0x337fd5)
        suggestion_embed.set_author(name=f'Suggestion #{suggestion_id}: Pending', icon_url=self.bot.user.avatar.url)
        suggestion_embed.set_thumbnail(url=ctx.author.avatar if ctx.author.avatar else ctx.author.default_avatar)
        suggestion_embed.set_footer(text='Click "I Agree" to upvote this suggestion, or "I Disagree" to downvote it.')

        suggestion_embed.add_field(name='Author:', value=f'{ctx.author.mention} (ID: {ctx.author.id})', inline=False)
        suggestion_embed.add_field(name='Suggestion:', value=suggestion, inline=False)
        suggestion_embed.add_field(name='Upvotes:', value='> 0', inline=True)
        suggestion_embed.add_field(name='Downvotes:', value='> 0', inline=True)

        await suggestion_message.edit(embed=suggestion_embed,
                                      view=SuggestionButtons(self.bot, suggestion_message, suggestion_id))
        await self.bot.embed_success(ctx, 'Suggestion submitted!')

    @commands.command(
        brief=' <suggestion-id> *opt<reason>',
        description='Approve a pending suggestion. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def approve(self, ctx: commands.Context, suggestion_id: int, *, response: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        try:
            found_suggestion = await self.bot.get_suggestion(suggestion_id)
            suggestion_message = await ctx.guild.get_channel(found_suggestion[0]).fetch_message(found_suggestion[1])
        except (TypeError, HTTPException):
            await self.bot.embed_error(ctx, 'Suggestion not found/could not be retrieved.')
            return
        else:
            if found_suggestion[6] != 'Pending':
                await self.bot.embed_error(ctx, 'This suggestion has already been approved/declined.')
                return

        suggestion_embed = suggestion_message.embeds[0]
        suggestion_embed.colour = 0x43b582
        suggestion_embed.set_author(name=suggestion_embed.author.name.replace('Pending', 'Approved'),
                                    icon_url=self.bot.user.avatar)
        suggestion_embed.set_footer(text=None)
        suggestion_embed.add_field(name='Response:', value=response, inline=False)

        await self.bot.end_suggestion(suggestion_id, 'Approved')
        await suggestion_message.edit(embed=suggestion_embed, view=None)
        await self.bot.embed_success(ctx, 'Suggestion approved!')

    @commands.command(
        brief=' <suggestion-id> *opt<reason>',
        description='Decline a pending suggestion. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def decline(self, ctx: commands.Context, suggestion_id: int, *, response: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        try:
            found_suggestion = await self.bot.get_suggestion(suggestion_id)
            suggestion_message = await ctx.guild.get_channel(found_suggestion[0]).fetch_message(found_suggestion[1])
        except (TypeError, HTTPException):
            await self.bot.embed_error(ctx, 'Suggestion not found/could not be retrieved.')
            return
        else:
            if found_suggestion[6] != 'Pending':
                await self.bot.embed_error(ctx, 'This suggestion has already been approved/declined.')
                return

        suggestion_embed = suggestion_message.embeds[0]
        suggestion_embed.colour = 0xf04a47
        suggestion_embed.set_author(name=suggestion_embed.author.name.replace('Pending', 'Declined'),
                                    icon_url=self.bot.user.avatar)
        suggestion_embed.set_footer(text=None)
        suggestion_embed.add_field(name='Response:', value=response, inline=False)

        await self.bot.end_suggestion(suggestion_id, 'Declined')
        await suggestion_message.edit(embed=suggestion_embed, view=None)
        await self.bot.embed_success(ctx, 'Suggestion declined.')

    @commands.command(
        brief=' <text-channel> <winners> <duration> *<description>',
        description='Hosts a giveaway in the specified channel. Requires <required-role> or higher.',
        extras=7)
    @commands.guild_only()
    async def giveaway(self, ctx: commands.Context, channel: TextChannel, winners: int, duration: str, *, desc: str):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        resolved_duration = DurationConverter(duration).get_resolved_duration()
        if not resolved_duration or not 3600 <= resolved_duration <= 2419200:
            await self.bot.embed_error(ctx, 'Specify a valid duration between 1 hour and 28 days.')
            return

        ga_embed = Embed(colour=0x337fd5, title=desc)
        ga_embed.set_thumbnail(url=self.bot.guild.icon if self.bot.guild.icon else self.bot.user.avatar)
        ga_embed.set_footer(text=f'{winners} Winner(s) • Started at {utils.utcnow().strftime("%m/%d/%Y, %H:%M:%S")}')
        ga_embed.add_field(name='Ends:', value=f'<t:{floor(utils.utcnow().timestamp() + resolved_duration)}:F>')
        ga_embed.add_field(name='Hosted By:', value=ctx.author.mention)

        message = await channel.send(embed=ga_embed)
        view = GiveawayButton(self.bot, message, winners, resolved_duration, desc)
        await message.edit(view=view)
        await view.expire()


async def setup(bot):
    await bot.add_cog(MiscCommands(bot))
