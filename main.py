import os
import aiosqlite
import asyncio
import logging
from discord import (
    Intents,
    Activity,
    ActivityType,
    LoginFailure,
    PrivilegedIntentsRequired,
    NotFound, HTTPException,
    abc, Member,
    Interaction,
    Embed, utils,
    Forbidden)
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import Mapping
from math import floor
from ast import literal_eval as l_e
from json import dumps
from typing import Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()


class YCCUtilities(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=os.getenv('PREFIX'),
                         owner_ids=set(os.getenv('OWNERS').split(',')),
                         activity=Activity(type=ActivityType.listening, name=os.getenv('ACTIVITY')),
                         case_insensitive=True,
                         intents=Intents.all(),
                         help_command=HelpCommand(),
                         max_messages=5000)

        self.guild = None
        self.general = None
        self.log_channel = None
        self.appeal_channel = None
        self.suggest_channel = None
        self.trivia_channel = None

        self.welcome_message = 'Welcome to the server <member>!'

        self.immune_channels = []

        self.admin = None
        self.bot_admin = None
        self.senior_staff = None
        self.head_mod = None
        self.senior_mod = None
        self.moderator = None
        self.trainee = None
        self.staff = None
        self.helper = None

        self.trivia_role = None
        self.active_role = None

        self.immune_roles = []

        self.db = None

    @property
    def token(self):
        return os.getenv('TOKEN')

    def member_clearance(self, member: Union[Member, None]):
        if not member:
            return 0
        if member == self.guild.owner or f'{member.id}' in self.owner_ids:
            return 10
        if self.admin in member.roles:
            return 9
        if self.bot_admin in member.roles:
            return 8
        if self.senior_staff in member.roles:
            return 7
        if self.head_mod in member.roles:
            return 6
        if self.senior_mod in member.roles:
            return 5
        if self.moderator in member.roles:
            return 4
        if self.trainee in member.roles:
            return 3
        if self.staff in member.roles:
            return 2
        if self.helper in member.roles:
            return 1
        return 0

    @staticmethod
    async def embed_error(ctx: commands.Context, message: str):
        embed = Embed(colour=0xf04a47, description=f'❌ {message}')
        await ctx.send(embed=embed)

    @staticmethod
    async def embed_success(ctx: commands.Context, message: str):
        embed = Embed(colour=0x43b582, description=f'*{message}*')
        await ctx.send(embed=embed)

    @staticmethod
    async def send_ephemeral_response(interaction: Interaction, reply: str, colour: int):
        await interaction.response.send_message(embed=Embed(colour=colour, description=reply), ephemeral=True)

    async def format_db(self):
        await self.db.execute('create table if not exists user_logs (user_id integer, case_id integer, mod_id integer, '
                              'log_type text, reason text, recorded_at integer, lasts_until integer, '
                              'channel_id integer)')
        await self.db.execute('create table if not exists case_count (count integer)')
        await self.db.execute('create table if not exists ongoing_logs (user_id integer, case_id integer, '
                              'log_type text, lasts_until integer, channel_id integer)')
        await self.db.execute('create table if not exists deleted_logs (user_id integer, case_id integer, '
                              'mod_id integer, log_type text, reason text, recorded_at integer, lasts_until integer, '
                              'channel_id integer)')

        cursor = await self.db.execute('SELECT count FROM case_count')
        count = await cursor.fetchone()
        if not count:
            await self.db.execute('INSERT INTO case_count (count) VALUES (?)', (0,))

        await self.db.execute('create table if not exists custom_roles (role_id integer, user_id integer)')
        await self.db.execute('create table if not exists persistent_roles (role_id integer, user_id integer)')

        await self.db.execute('create table if not exists faqs (shortcut text, response text)')
        await self.db.execute('create table if not exists custom_commands (shortcut text, log_type text, reason text, '
                              'duration integer)')

        await self.db.execute('create table if not exists suggest_count (count integer)')
        await self.db.execute('create table if not exists suggestion_data (channel_id integer, message_id integer, '
                              'suggestion_id integer, author_id integer, suggestion text, approvals text, '
                              'declines text, state text, created_at integer)')

        cursor = await self.db.execute('SELECT count FROM suggest_count')
        suggest_count = await cursor.fetchone()
        if not suggest_count:
            await self.db.execute('INSERT INTO suggest_count (count) VALUES (?)', (0,))

        await self.db.execute('create table if not exists blacklists (suggest text, appeal text, trivia text)')

        cursor = await self.db.execute('SELECT * FROM blacklists')
        rows = await cursor.fetchone()
        if not rows:
            await self.db.execute('INSERT INTO blacklists (suggest, appeal, trivia) VALUES (?, ?, ?)', ('[]',) * 3)

        await self.db.execute(f'create table if not exists message_stats (user_id integer, channel_id integer, '
                              f'message_time integer)')
        await self.db.execute(f'create table if not exists voice_stats (user_id integer, channel_id integer, '
                              f'joined integer, left integer)')

        await self.db.commit()

    async def blacklist(self, blacklist: str):
        cursor = await self.db.execute(f'SELECT {blacklist} FROM blacklists')
        blacklist = await cursor.fetchone()
        return l_e(blacklist[0])

    async def edit_blacklist(self, blacklist: str, operation: int, user_id: int):
        current_blacklist = await self.blacklist(blacklist)

        if operation and user_id not in current_blacklist:
            current_blacklist.append(user_id)
        elif not operation and user_id in current_blacklist:
            current_blacklist.remove(user_id)

        await self.db.execute(f'UPDATE blacklists SET {blacklist} = ?', (dumps(current_blacklist),))
        await self.db.commit()

    async def ongoing_cases(self):
        cursor = await self.db.execute('SELECT * FROM ongoing_logs')
        logs_data = await cursor.fetchall()
        return logs_data

    async def pull_expired_cases(self):
        cursor = await self.db.execute(f'SELECT user_id, log_type, channel_id FROM ongoing_logs WHERE lasts_until < '
                                       f'{utils.utcnow().timestamp()}')
        expired_logs = await cursor.fetchall()

        await self.db.execute(f'DELETE FROM ongoing_logs WHERE lasts_until < {utils.utcnow().timestamp()}')
        await self.db.commit()

        return expired_logs

    async def get_suggestion(self, suggestion_id: int):
        cursor = await self.db.execute(f'SELECT channel_id, message_id, author_id, suggestion, approvals, declines, '
                                       f'state, created_at FROM suggestion_data WHERE suggestion_id = ?',
                                       (suggestion_id,))
        suggestion_data = await cursor.fetchone()
        return suggestion_data

    async def add_suggestion(self, message_id: int, author_id: int, suggestion: str):
        cursor = await self.db.execute(f'SELECT count FROM suggest_count')
        count = (await cursor.fetchone())[0] + 1
        await self.db.execute('UPDATE suggest_count SET count = ?', (count,))

        await self.db.execute(f'INSERT INTO suggestion_data(channel_id, message_id, suggestion_id, author_id, '
                              f'suggestion, approvals, declines, state, created_at) VALUES '
                              f'(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                              (self.suggest_channel.id, message_id, count, author_id, suggestion, '[]', '[]', 'Pending',
                               floor(utils.utcnow().timestamp())))

        await self.db.commit()
        return count

    async def suggestion_vote(self, suggestion_id: int, vote_type: str, edit_type: int, user_id: int):
        cursor = await self.db.execute(f'SELECT {vote_type} FROM suggestion_data WHERE suggestion_id = ?',
                                       (suggestion_id,))
        votes_list = l_e((await cursor.fetchone())[0])

        if not edit_type and user_id in votes_list:
            votes_list.remove(user_id)
        elif edit_type and user_id not in votes_list:
            votes_list.append(user_id)

        await self.db.execute(f'UPDATE suggestion_data SET {vote_type} = ? WHERE suggestion_id = ?',
                              (dumps(votes_list), suggestion_id))
        await self.db.commit()

    async def end_suggestion(self, suggestion_id: int, result: str):
        await self.db.execute(f'UPDATE suggestion_data SET state = ? WHERE suggestion_id = ?', (result, suggestion_id))
        await self.db.commit()

    async def role_assignments(self, assignment_type: str):
        cursor = await self.db.execute(f'SELECT role_id, user_id FROM {assignment_type}')
        data = await cursor.fetchall()
        return data

    async def add_role_assignment(self, assignment_type: str, role_id: int, user_id: int):
        await self.db.execute(f'INSERT INTO {assignment_type} (role_id, user_id) VALUES (?, ?)', (role_id, user_id))
        await self.db.commit()

    async def del_role_assignment(self, assignment_type: str, role_id: int, user_id: int):
        await self.db.execute(f'DELETE FROM {assignment_type} WHERE role_id = ? AND user_id = ?', (role_id, user_id))
        await self.db.commit()

    async def auto_del_assignment(self, role_id: int):
        await self.db.execute('DELETE FROM custom_roles WHERE role_id = ?', (role_id,))
        await self.db.execute('DELETE FROM persistent_roles WHERE role_id = ?', (role_id,))
        await self.db.commit()

    async def wipe(self):
        for item in ['custom_commands', 'faqs', 'custom_roles', 'persistent_roles']:
            await self.db.execute(f'DELETE FROM {item}')
        await self.db.commit()

    async def faq_commands(self):
        cursor = await self.db.execute(f'SELECT shortcut, response FROM faqs')
        guild_faq_data = await cursor.fetchall()
        return guild_faq_data

    async def add_faq(self, shortcut: str, response: str):
        await self.db.execute(f'INSERT INTO faqs (shortcut, response) VALUES (?, ?)', (shortcut, response))
        await self.db.commit()

    async def del_faq(self, shortcut: str):
        await self.db.execute(f'DELETE FROM faqs WHERE shortcut = ?', (shortcut,))
        await self.db.commit()

    async def custom_commands(self):
        cursor = await self.db.execute(f'SELECT shortcut, log_type, reason, duration FROM custom_commands')
        guild_custom_data = await cursor.fetchall()
        return guild_custom_data

    async def add_custom_command(self, shortcut: str, log_type: str, reason: str, duration: int):
        await self.db.execute(f'INSERT INTO custom_commands (shortcut, log_type, reason, duration) VALUES (?, ?, ?, ?)',
                              (shortcut, log_type, reason, duration))
        await self.db.commit()

    async def del_custom_command(self, shortcut: str):
        await self.db.execute(f'DELETE FROM custom_commands WHERE shortcut = ?', (shortcut,))
        await self.db.commit()

    async def activity_stats(self, duration: int):
        cursor = await self.db.execute(f'SELECT user_id, channel_id, message_time FROM message_stats WHERE'
                                       f' message_time > {floor(utils.utcnow().timestamp() - duration)}')
        all_text_stats = await cursor.fetchall()
        cursor = await self.db.execute(f'SELECT user_id, channel_id, joined, left FROM voice_stats WHERE '
                                       f'left > {floor(utils.utcnow().timestamp() - duration)}')
        all_voice_stats = await cursor.fetchall()
        return all_text_stats, all_voice_stats

    async def add_message_stat(self, member_id: int, channel_id: int, sent_at: int):
        await self.db.execute(f'INSERT INTO message_stats (user_id, channel_id, message_time) VALUES (?, ?, ?)',
                              (member_id, channel_id, sent_at))
        await self.db.commit()

    async def add_vc_stat(self, member_id: int, channel_id: int, joined_at: int, left_at: int):
        await self.db.execute(f'INSERT INTO voice_stats (user_id, channel_id, joined, left) VALUES (?, ?, ?, ?)',
                              (member_id, channel_id, joined_at, left_at))
        await self.db.commit()

    async def get_owners(self):
        return [await self.fetch_user(user_id) for user_id in self.owner_ids]

    async def get_or_fetch_member(self, user_id: int):
        member = self.guild.get_member(user_id)
        if not member:
            try:
                member = await self.guild.fetch_member(user_id)
            except NotFound:
                member = None
        return member

    async def get_or_fetch_channel(self, channel_id: int) -> abc.GuildChannel:
        channel = self.guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.guild.fetch_channel(channel_id)
            except NotFound:
                channel = None
        return channel

    async def bot_member(self) -> Member:
        return await self.get_or_fetch_member(self.user.id)

    async def get_commands(self):
        command_list = []
        for command in self.commands:
            command_list.append(command.name)
            for alias in command.aliases:
                command_list.append(alias)
        for entry in await self.faq_commands():
            command_list.append(entry[0])
        for entry in await self.custom_commands():
            command_list.append(entry[0])
        return command_list

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await self.embed_error(ctx, f'Whoa there! Wait `{floor(error.retry_after)}s` before trying that again.')

        elif isinstance(error, commands.NotOwner):
            await self.embed_error(ctx, f'User is not a bot owner.')

        elif isinstance(error, commands.MissingPermissions):
            await self.embed_error(ctx, f'User missing required permissions: '
                                        f'`{"".join(error.missing_permissions).replace("_", " ")}`.')
        elif isinstance(error, commands.BotMissingPermissions):
            await self.embed_error(ctx, f'Bot missing required permissions: '
                                        f'`{"".join(error.missing_permissions).replace("_", " ")}`.')

        elif isinstance(error, commands.MissingRequiredArgument):
            await self.embed_error(ctx, f'Missing required arguments.')

        elif isinstance(error, commands.UserNotFound):
            await self.embed_error(ctx, 'User not found.')
        elif isinstance(error, commands.MemberNotFound):
            await self.embed_error(ctx, 'Member not found.')
        elif isinstance(error, commands.RoleNotFound):
            await self.embed_error(ctx, 'Role not found.')
        elif isinstance(error, commands.ChannelNotFound):
            await self.embed_error(ctx, 'Channel not found.')

        elif isinstance(error, commands.BadArgument):
            await self.embed_error(ctx, 'Incorrect argument type(s).')

        elif isinstance(error, commands.CommandNotFound):
            return

        else:
            await self.embed_error(ctx, f'An unexpected error occurred: {error}')
            logging.warning(error)

    @tasks.loop(seconds=60)
    async def process_expired_logs(self):
        await self.wait_until_ready()
        self.guild = self.get_guild(int(os.getenv('GUILD_ID')))

        expired_logs = await self.pull_expired_cases()

        for log in expired_logs:
            try:
                user = await bot.fetch_user(log[0])
            except (HTTPException, NotFound):
                continue

            if log[1] == 'Ban':
                try:
                    await self.guild.unban(user)
                except Forbidden:
                    logging.warning(f'Could not unban {user.name} (ID: {user.id}) - Missing permissions')
                    continue
                except (HTTPException, NotFound):
                    continue
            elif log[1] == 'Mute':
                member = self.guild.get_member(user.id)
                try:
                    await member.timeout(None)
                except Forbidden:
                    logging.warning(f'Could not unmute {user.name} (ID: {user.id}) - Missing permissions')
                    continue
                except AttributeError:
                    continue
            elif log[1] == 'Channel Ban':
                member = self.guild.get_member(user.id)
                channel = self.guild.get_channel(log[2])
                try:
                    await channel.set_permissions(member, overwrite=None)
                except Forbidden:
                    logging.warning(f'Could not channel unban {user.name} (ID: {user.id}) - Missing permissions')
                    continue
                except (AttributeError, TypeError):
                    continue

    async def setup_hook(self) -> None:
        logging.info('Setting up database...')

        self.db = await aiosqlite.connect('data.db')
        await self.db.execute('PRAGMA journal_mode=wal')
        await self.format_db()

        logging.info('Fetching Discord objects...')

        try:
            self.guild = await self.fetch_guild(int(os.getenv('GUILD_ID')))
        except (NotFound, HTTPException, ValueError):
            logging.fatal('Unknown Guild ID.')
            exit()

        try:
            self.general = await self.get_or_fetch_channel(int(os.getenv('GENERAL')))
            self.log_channel = await self.get_or_fetch_channel(int(os.getenv('LOGGING')))
            self.appeal_channel = await self.get_or_fetch_channel(int(os.getenv('BAN_APPEALS')))
            self.suggest_channel = await self.get_or_fetch_channel(int(os.getenv('SUGGESTIONS')))
            self.trivia_channel = await self.get_or_fetch_channel(int(os.getenv('TRIVIA')))

            self.immune_channels = [await self.get_or_fetch_channel(int(c_id)) for c_id in
                                    os.getenv('IMMUNE_CHANNELS').split(',')]
        except (NotFound, HTTPException, ValueError):
            logging.fatal('Unknown/invalid channel ID(s).')
            exit()

        try:
            self.admin = self.guild.get_role(int(os.getenv('ADMINISTRATOR')))
            self.bot_admin = self.guild.get_role(int(os.getenv('BOT_ADMIN')))
            self.senior_staff = self.guild.get_role(int(os.getenv('SENIOR_STAFF')))
            self.head_mod = self.guild.get_role(int(os.getenv('HEAD_MOD')))
            self.senior_mod = self.guild.get_role(int(os.getenv('SENIOR_MOD')))
            self.moderator = self.guild.get_role(int(os.getenv('MODERATOR')))
            self.trainee = self.guild.get_role(int(os.getenv('TRAINEE_MOD')))
            self.staff = self.guild.get_role(int(os.getenv('STAFF_TEAM')))
            self.helper = self.guild.get_role(int(os.getenv('COMMUNITY_HELPER')))

            self.trivia_role = self.guild.get_role(int(os.getenv('TRIVIA_ROLE')))
            self.active_role = self.guild.get_role(int(os.getenv('ACTIVE_ROLE')))

            self.immune_roles = [self.guild.get_role(int(role_id)) for role_id in os.getenv('IMMUNE_ROLES').split(',')]
        except ValueError:
            logging.fatal('Invalid role ID(s) found.')
            exit()

        logging.info(f'Logging in as {self.user} (ID: {self.user.id})...')

        try:
            owners = await self.get_owners()
            logging.info(f'Bot owner(s): {", ".join([user.name for user in owners])}')
        except (NotFound, HTTPException):
            logging.fatal('Unknown/invalid owner ID(s) found.')
            exit()
        logging.info(f'Guild: {self.guild}')

    def run_bot(self):
        async def runner():
            async with self:
                logging.info(f'Loading extensions...')
                for filename in os.listdir(os.getenv('COGS')):
                    if filename.endswith('.py'):
                        try:
                            await self.load_extension(f'cogs.{filename[:-3]}')
                        except (commands.ExtensionFailed, commands.NoEntryPointError):
                            logging.warning(f'Extension {filename} could not be loaded...')
                logging.info('Starting tasks...')
                self.process_expired_logs.start()
                try:
                    await self.start(self.token)
                except LoginFailure:
                    logging.error('Invalid token passed.')
                except PrivilegedIntentsRequired:
                    logging.error('Privileged intents have not been explicitly enabled in the developer portal..')

        async def cancel_tasks():
            await self.db.commit()
            await self.db.close()
            self.process_expired_logs.stop()

        try:
            asyncio.run(runner())
        except (KeyboardInterrupt, SystemExit):
            logging.info("Received signal to terminate bot and event loop.")
        finally:
            logging.info('Cleaning up tasks and connections...')
            asyncio.run(cancel_tasks())
            logging.info('Done. Have a nice day!')


class HelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping: Mapping):
        help_menu_embed = Embed(colour=0x337fd5, title='All Commands')

        help_menu_embed.set_author(name='Help Menu', icon_url=bot.user.avatar.url)
        help_menu_embed.set_footer(text=f'Use {bot.command_prefix}help <command> for more info on a single command.')

        cog_name_dict = {'ConfigCommands': 'Server Configuration Commands',
                         'MiscCommands': 'Miscellaneous Commands',
                         'ModLogsCommands': 'Modlogs Commands',
                         'PunishmentCommands': 'Moderation Commands',
                         'InfoCommands': 'Info Commands',
                         'UserStatistics': 'Activity Statistics Commands',
                         'TriviaModule': 'Trivia Commands'}

        for cog_name in bot.cogs:
            if cog_name in cog_name_dict:
                cog = bot.get_cog(cog_name)

                cog_commands = f'`{"` `".join([command.qualified_name for command in cog.get_commands()])}`'

                help_menu_embed.add_field(name=cog_name_dict[cog.qualified_name],
                                          value=cog_commands,
                                          inline=False)

        await self.context.send(embed=help_menu_embed)

    async def send_command_help(self, command: commands.Command):
        command_help_embed = Embed(colour=0x337fd5,
                                   title=f'{bot.command_prefix}{command.qualified_name} Command',
                                   description=command.description)

        command_help_embed.set_author(name='Help Menu', icon_url=bot.user.avatar.url)
        command_help_embed.set_footer(text=f'Use {bot.command_prefix}help to view all commands.')

        command_help_embed.add_field(name='Usage:',
                                     value=f'`{bot.command_prefix}{command.qualified_name}{command.brief}`'
                                     if command.qualified_name != 'help'
                                     else f'`{bot.command_prefix}help opt<command-name>`',
                                     inline=False)

        command_help_embed.add_field(name='Aliases:',
                                     value=f'`{", ".join([alias for alias in command.aliases])}`' if command.aliases
                                     else '`None`',
                                     inline=False)

        await self.context.send(embed=command_help_embed)

    async def send_error_message(self, error: commands.CommandError):
        await self.context.send(embed=Embed(colour=0xf04a47, description='❌ Something went wrong.'))


bot = YCCUtilities()

bot.run_bot()
