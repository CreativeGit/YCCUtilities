from discord.ext import commands
from discord import (
    Embed,
    ui,
    Message,
    Button,
    ButtonStyle,
    Interaction,
    User, utils)
from core.modlogs import ModLogsByCaseID, ModLogsByUser
from core.pageviewer import PageButtons
from core.duration import DurationConverter
from datetime import timedelta
from math import floor


class MyLogsButton(ui.View):
    def __init__(self, message: Message):
        super().__init__(timeout=90)
        self.message = message

    @ui.button(label='My Logs', emoji='📖', style=ButtonStyle.blurple)
    async def my_logs_button(self, interaction: Interaction, button: Button):
        user_data = ModLogsByUser(interaction.user)
        user_logs = await user_data.get_logs()
        user_logs.reverse()

        if not user_logs:
            await interaction.response.send_message(embed=Embed(
                colour=0xf04a47, description=f'❌ No logs found for {interaction.user.mention}.'), ephemeral=True)
            return

        count = 0
        while count < len(user_logs):
            if user_logs[count][2] == 'Note':
                user_logs.pop(count)
            else:
                count += 1

        page_count = 1
        embed_pages_dict = {1: Embed(
            colour=0x337fd5, title=f'Mod logs for {interaction.user} (Page 1/<page-count>)')}

        field_count = 0
        for entry in user_logs:
            channel_mute_str = '' if not entry[6] else f' (<#{entry[6]}>)'

            duration = '' if not entry[5] - entry[4] else f'**Duration:** `{timedelta(seconds=entry[5] - entry[4])}`'

            if len(embed_pages_dict[page_count]) + len(entry[3]) < 5000 and field_count < 7:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages_dict.update({page_count: Embed(
                    colour=0x337fd5, title=f'Mod logs for {interaction.user} (Page {page_count}/<page-count>)')})

            embed_pages_dict[page_count].insert_field_at(index=0,
                                                         name=f'Case {entry[0]}',
                                                         value=f'**Type:** {entry[2]}{channel_mute_str}\n'
                                                               f'**Reason:** {entry[3]} - <t:{entry[4]}:f>\n'
                                                               f'{duration}',
                                                         inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages_dict[i].title.replace('<page-count>', str(page_count))
            embed_pages_dict[i].title = new_title

        await interaction.response.send_message(embed=embed_pages_dict[1],
                                                view=PageButtons(embed_pages_dict, interaction=interaction),
                                                ephemeral=True)

    async def on_timeout(self):
        self.my_logs_button.disabled = True
        await self.message.edit(view=self)


class ModLogsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief='',
        description='View your own modlogs history in the guild. Responsible moderators and notes are omitted.')
    @commands.guild_only()
    async def mylogs(self, ctx: commands.Context):
        response = await ctx.send(embed=Embed(
            colour=0x337fd5, description='Click below to view your past modlogs for this guild.'))
        await response.edit(view=MyLogsButton(response))

    @commands.command(
        brief=' opt<flag>',
        aliases=['mds'],
        description='View all ongoing moderations in the guild. `<flag>` can be used to filter specific actions. '
                    'Requires Community Helper or higher.')
    @commands.guild_only()
    async def moderations(self, ctx: commands.Context, flag: str = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        active_logs = await self.bot.ongoing_cases()

        flag_filter_dict = {'-m': 'Mute', '-b': 'Ban', '-cb': 'Channel Ban'}

        if flag in list(flag_filter_dict):
            count = 0
            while count < len(active_logs):
                if active_logs[count][2] != flag_filter_dict[flag]:
                    active_logs.pop(count)
                else:
                    count += 1

        if not active_logs:
            await self.bot.embed_error(ctx, f'No ongoing logs found.')
            return

        page_count = 1
        embed_pages_dict = {1: Embed(colour=0x337fd5, title=f'Active Moderations (Page 1/<page-count>)')}

        field_count = 0
        for entry in active_logs:
            channel_mute_str = '' if not entry[4] else f' (<#{entry[4]}>)'

            if field_count < 7:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages_dict.update({page_count: Embed(
                    colour=0x337fd5, title=f'Active Moderations (Page {page_count}/<page-count>)')})

            embed_pages_dict[page_count].insert_field_at(
                index=0, name=f'Case {entry[1]}',
                value=f'**User:** <@{entry[0]}>\n**Type:** {entry[2]}{channel_mute_str}\n**Expires:** '
                      f'<t:{floor(entry[3])}:f>', inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages_dict[i].title.replace('<page-count>', str(page_count))
            embed_pages_dict[i].title = new_title

        message = await ctx.send(embed=embed_pages_dict[1])
        await message.edit(view=PageButtons(embed_pages_dict, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' opt<user> opt<flag>',
        aliases=['logs'],
        description='View the modlogs history of a specific user. `<flag>` can be used to filter specific actions. '
                    'Requires Community Helper or higher.')
    @commands.guild_only()
    async def modlogs(self, ctx: commands.Context, user: User = None, flag: str = None):
        if self.bot.member_clearance(ctx.author) < 1:
            return
        elif not user:
            user = ctx.author

        user_data = ModLogsByUser(user)
        user_logs = await user_data.get_logs()
        user_logs.reverse()

        if not user_logs:
            await self.bot.embed_error(ctx, f'No logs found for {user.mention}.')
            return

        flag_filter_dict = {'-n': 'Note', '-dm': 'Direct Message', '-w': 'Warn', '-k': 'Kick', '-m': 'Mute',
                            '-b': 'Ban', '-cb': 'Channel Ban', '-um': 'Unmute', '-ub': 'Unban', '-ucb': 'Channel Unban'}

        if flag in list(flag_filter_dict):
            count = 0
            while count < len(user_logs):
                if user_logs[count][2] != flag_filter_dict[flag]:
                    user_logs.pop(count)
                else:
                    count += 1

        page_count = 1
        embed_pages_dict = {1: Embed(colour=0x337fd5, title=f'Mod logs for {user} (Page 1/<page-count>)')}

        field_count = 0
        for entry in user_logs:
            channel_mute_str = '' if not entry[6] else f' (<#{entry[6]}>)'

            duration_str = '' if not entry[5] - entry[4] else f'**Duration:** ' \
                                                              f'`{timedelta(seconds=entry[5] - entry[4])}`'

            if len(embed_pages_dict[page_count]) + len(entry[3]) < 5000 and field_count < 7:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages_dict.update({page_count: Embed(
                    colour=0x337fd5, title=f'Mod logs for {user} (Page {page_count}/<page-count>)')})

            embed_pages_dict[page_count].insert_field_at(index=0,
                                                         name=f'Case {entry[0]}',
                                                         value=f'**Type:** {entry[2]}{channel_mute_str}\n'
                                                               f'**Moderator:** <@{entry[1]}>\n'
                                                               f'**Reason:** {entry[3]} - <t:{entry[4]}:f>\n'
                                                               f'{duration_str}',
                                                         inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages_dict[i].title.replace('<page-count>', str(page_count))
            embed_pages_dict[i].title = new_title

        message = await ctx.send(embed=embed_pages_dict[1])
        await message.edit(view=PageButtons(embed_pages_dict, message=message, author_id=ctx.author.id))

    @commands.command(
        brief=' <case-id>',
        description='View information about a specific modlogs case. Requires Community Helper or higher.')
    @commands.guild_only()
    async def case(self, ctx: commands.Context, case_id: int):
        if self.bot.member_clearance(ctx.author) < 1:
            return

        case = ModLogsByCaseID(case_id)
        case_data = await case.find_case()

        if not case_data[0]:
            await self.bot.embed_error(ctx, 'Case not found.')
            return

        channel_mute_str = '' if not case_data[0][6] else f' (<#{case_data[0][6]}>)'

        duration = '' if not case_data[0][5] - case_data[0][4] else \
            f'\n**Duration:** `{timedelta(seconds=case_data[0][5] - case_data[0][4])}`'

        ongoing = '' if not duration else f'\n**Ongoing:** `{case_data[1]}`'

        case_embed = Embed(
            colour=0x337fd5, title=f'Case {case_id}',
            description=f'**User:** <@{case_data[0][0]}>\n**Type:** {case_data[0][2]}{channel_mute_str}\n'
                        f'**Moderator:** <@{case_data[0][1]}>\n**Reason:** {case_data[0][3]} - <t:{case_data[0][4]}:f>'
                        f'{duration}{ongoing}')

        await ctx.send(embed=case_embed)

    @commands.command(
        brief=' <case-id> *opt<reason>',
        description='Edit the reason for a specified modlogs case. Requires Moderator or higher.')
    @commands.guild_only()
    async def reason(self, ctx: commands.Context, case_id: int, *, new_reason: str = 'No reason given.'):
        if self.bot.member_clearance(ctx.author) < 4:
            return

        case = ModLogsByCaseID(case_id)
        if not (await case.find_case())[0]:
            await self.bot.embed_error(ctx, 'Case not found.')
            return
        await case.edit_reason(new_reason)
        await self.bot.embed_success(ctx, f'Reason for case {case_id} updated.')

    @commands.command(
        brief=' <case-id> <duration>',
        description='Edit the duration of an ongoing case. The new duration is measured from the time the modlogs '
                    'entry was initially created. Requires Moderator or higher.')
    @commands.guild_only()
    async def duration(self, ctx: commands.Context, case_id: int, new_duration: str):
        if self.bot.member_clearance(ctx.author) < 4:
            return

        case = ModLogsByCaseID(case_id)
        ongoing_case = await case.find_case()

        if not ongoing_case[0]:
            await self.bot.embed_error(ctx, 'Case not found.')
            return
        elif not ongoing_case[1]:
            await self.bot.embed_error(ctx, 'This case is not ongoing so it\'s duration can not be edited.')
            return

        resolved_duration = DurationConverter(new_duration).get_resolved_duration()
        if not resolved_duration or resolved_duration < 60:
            await self.bot.embed_error(ctx, 'Please specify a valid duration greater than 1 minute.')
            return
        elif ongoing_case[0][2] == 'Mute' and resolved_duration > 2419200:
            await self.bot.embed_error(ctx, 'Mutes cannot last longer than 28 days.')
            return

        member = ctx.guild.get_member(ongoing_case[0][0])
        if member and ongoing_case[0][2] == 'Mute':
            new_lasts_for = floor((ongoing_case[0][4] + resolved_duration) - utils.utcnow().timestamp())
            if new_lasts_for <= 0:
                await member.timeout(None)
            else:
                await member.timeout(timedelta(seconds=new_lasts_for))

        await case.edit_duration(resolved_duration)
        await self.bot.embed_success(ctx, f'Duration for case {case_id} updated.')

    @commands.command(
        brief=' <case-id>',
        description='Delete a specified modlogs case. The case will no longer show up in the user\'s modlogs history '
                    'but can be seen using `deletedlogs`. Requires Senior Staff or higher.')
    @commands.guild_only()
    async def delcase(self, ctx: commands.Context, case_id: int):
        if self.bot.member_clearance(ctx.author) < 7:
            return

        case = ModLogsByCaseID(case_id)

        if not (await case.find_case())[0]:
            await self.bot.embed_error(ctx, 'Case not found.')
            return
        if (await case.find_case())[1]:
            await self.bot.embed_error(ctx, 'Case is currently ongoing and cannot be deleted.')
            return

        await case.delete_case()

        await self.bot.embed_success(ctx, 'Case successfully deleted.')

    @commands.command(
        brief=' opt<user> opt<flag>',
        aliases=['dellogs'],
        description='View the deleted modlogs cases for a specified user. Requires Senior Staff or higher.')
    @commands.guild_only()
    async def deletedlogs(self, ctx: commands.Context, user: User = None, flag: str = None):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        elif not user:
            user = ctx.author

        user_data = ModLogsByUser(user)
        deleted_logs = await user_data.get_deleted_logs()
        deleted_logs.reverse()

        if not deleted_logs:
            await self.bot.embed_error(ctx, f'No deleted logs found for {user.mention}.')
            return

        flag_filter_dict = {'-n': 'Note', '-dm': 'Direct Message', '-w': 'Warn', '-k': 'Kick', '-m': 'Mute',
                            '-b': 'Ban', '-cb': 'Channel Ban', '-um': 'Unmute', '-ub': 'Unban', '-ucb': 'Channel Unban'}

        if flag in list(flag_filter_dict):
            count = 0
            while count < len(deleted_logs):
                if deleted_logs[count][2] != flag_filter_dict[flag]:
                    deleted_logs.pop(count)
                else:
                    count += 1

        page_count = 1
        embed_pages_dict = {1: Embed(colour=0x337fd5, title=f'Deleted logs for {user} (Page 1/<page-count>)')}

        field_count = 0
        for entry in deleted_logs:
            channel_mute_str = '' if not entry[6] else f' (<#{entry[6]}>)'

            duration = '' if not entry[5] - entry[4] else f'**Duration:** `{timedelta(seconds=entry[5] - entry[4])}`'

            if len(embed_pages_dict[page_count]) + len(entry[3]) < 5000 and field_count < 2:
                field_count += 1

            else:
                page_count += 1
                field_count = 1

                embed_pages_dict.update({page_count: Embed(
                    colour=0x337fd5, title=f'Mod logs for {user} (Page {page_count}/<page-count>)')})

            embed_pages_dict[page_count].insert_field_at(
                index=0, name=f'Case {entry[0]}',
                value=f'**Type:** {entry[2]}{channel_mute_str}\n**Moderator:** <@{entry[1]}>\n'
                      f'**Reason:** {entry[3]} - <t:{entry[4]}:f>\n{duration}', inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages_dict[i].title.replace('<page-count>', str(page_count))
            embed_pages_dict[i].title = new_title

        message = await ctx.send(embed=embed_pages_dict[1])
        await message.edit(view=PageButtons(embed_pages_dict, message=message, author_id=ctx.author.id))


async def setup(bot):
    await bot.add_cog(ModLogsCommands(bot))
