import os
import aiosqlite
from typing import Union
from discord import (
    User,
    Member,
    utils, Embed,
    TextStyle,
    ui, Interaction,
    Message,
    ButtonStyle,
    Forbidden)
from discord.ext import commands
from dotenv import load_dotenv
from math import floor

load_dotenv()
DATABASE = os.getenv('DATABASE')


class ModLogsByUser:
    def __init__(self, user: Union[User, Member]):
        self.user = user

    async def get_logs(self):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        cursor = await db.execute(f'SELECT case_id, mod_id, log_type, reason, recorded_at, lasts_until, channel_id '
                                  f'FROM user_logs WHERE user_id = {self.user.id}')
        user_logs_data = await cursor.fetchall()

        await db.close()

        return user_logs_data

    async def add_log(self, mod_id: int, log_type: str, log_reason: str, duration: int, channel_id: int):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        cursor = await db.execute('SELECT count FROM case_count')
        count = (await cursor.fetchone())[0] + 1
        await db.execute('UPDATE case_count SET count = ?', (count,))

        await db.execute(f'INSERT INTO user_logs (user_id, case_id, mod_id, log_type, reason, recorded_at, '
                         f'lasts_until, channel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (self.user.id, count, mod_id, log_type, log_reason,
                          floor(utils.utcnow().timestamp()), floor(utils.utcnow().timestamp() + duration), channel_id))

        if log_type in ['Ban', 'Mute', 'Channel Ban']:
            await db.execute(f'INSERT INTO ongoing_logs (user_id, case_id, log_type, lasts_until, '
                             f'channel_id) VALUES (?, ?, ?, ?, ?)',
                             (self.user.id, count, log_type, floor(utils.utcnow().timestamp() + duration), channel_id))

        await db.commit()
        await db.close()

    async def remove_ongoing_logs(self, log_type: str, channel_id: int):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        await db.execute(f'DELETE FROM ongoing_logs WHERE user_id = ? AND log_type = ? AND channel_id = ?',
                         (self.user.id, log_type, channel_id))

        await db.commit()
        await db.close()

    async def get_deleted_logs(self):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        cursor = await db.execute(f'SELECT case_id, mod_id, log_type,reason, recorded_at, lasts_until, channel_id '
                                  f'FROM deleted_logs WHERE user_id = {self.user.id}')
        user_logs_data = await cursor.fetchall()

        await db.close()

        return user_logs_data


class ModLogsByCaseID:
    def __init__(self, case_id: int):
        self.case_id = case_id

    async def find_case(self):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        cursor = await db.execute(f'SELECT user_id, mod_id, log_type, reason, recorded_at, lasts_until, channel_id '
                                  f'FROM user_logs WHERE case_id = {self.case_id}')
        case_data = await cursor.fetchone()

        ongoing = False

        if case_data:
            cursor = await db.execute(f'SELECT user_id FROM ongoing_logs WHERE case_id = {self.case_id}')
            ongoing = await cursor.fetchone()

            ongoing = True if ongoing else False

        await db.commit()
        await db.close()

        return case_data, ongoing

    async def edit_reason(self, new_reason: str):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        await db.execute(f'UPDATE user_logs SET reason = ? WHERE case_id = ?', (new_reason, self.case_id))

        await db.commit()
        await db.close()

    async def edit_duration(self, new_duration: int):
        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        cursor = await db.execute(f'SELECT recorded_at FROM user_logs WHERE case_id = {self.case_id}')
        recorded_at = await cursor.fetchone()

        new_lasts_until = recorded_at[0] + new_duration

        await db.execute(f'UPDATE user_logs SET lasts_until = ? WHERE case_id = ?',
                         (new_lasts_until, self.case_id))

        await db.execute(f'UPDATE ongoing_logs SET lasts_until = ? WHERE case_id = ?',
                         (new_lasts_until, self.case_id))

        await db.commit()
        await db.close()

    async def delete_case(self):
        existing_case = await self.find_case()

        deleted_case_data = list(existing_case[0])
        deleted_case_data.insert(1, self.case_id)

        db = await aiosqlite.connect(DATABASE)
        await db.execute('PRAGMA journal_mode=wal')

        await db.execute(f'DELETE FROM user_logs WHERE case_id = {self.case_id}')

        await db.execute(f'INSERT INTO deleted_logs (user_id, case_id, mod_id, log_type, reason, recorded_at, '
                         f'lasts_until, channel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', tuple(deleted_case_data))

        await db.commit()
        await db.close()


# Ban Appeal Modals are deprecated
class BanAppealModal(ui.Modal):
    def __init__(self, bot):
        super().__init__(title='Ban Appeal', timeout=None)
        self.bot = bot
    field_1 = ui.TextInput(label='Why, in your opinion, were you banned?', placeholder='Reason', required=True,
                           style=TextStyle.paragraph)
    field_2 = ui.TextInput(label='Why should you be unbanned?', placeholder='Reason', required=True,
                           style=TextStyle.paragraph)

    async def on_submit(self, interaction: Interaction):
        if interaction.user.id in await self.bot.blacklist('appeal'):
            await self.bot.send_ephemeral_response(interaction, '❌ You\'ve been blacklisted from appealing your ban.',
                                                   0xf04a47)

        guild_appeal_embed = Embed(colour=0x337fd5,
                                   title='Ban Appeal Submitted',
                                   description=f'{interaction.user.mention} (ID: {interaction.user.id})')

        url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
        guild_appeal_embed.set_thumbnail(url=url)

        user_data = ModLogsByUser(interaction.user)
        user_logs = await user_data.get_logs()

        ban_reason = 'Case not found.'
        case_id = 'Not Found'
        for entry in user_logs:
            if entry[2] == 'Ban':
                ban_reason = entry[3]
                case_id = entry[0]

        guild_appeal_embed.add_field(name='Why, in your opinion, were you banned?',
                                     value=self.field_1.value,
                                     inline=False)
        guild_appeal_embed.add_field(name='Why should you be unbanned?',
                                     value=self.field_2.value,
                                     inline=False)
        guild_appeal_embed.add_field(name=f'Ban Reason (Case {case_id}):',
                                     value=ban_reason,
                                     inline=False)

        try:
            await self.bot.appeal_channel.send(embed=guild_appeal_embed)
            await self.bot.send_ephemeral_response(interaction, '*Ban appeal submitted!*', 0x43b582)
        except (Forbidden, AttributeError):
            await self.bot.send_ephemeral_response(interaction, '❌ Something went wrong. The guild may not be '
                                                                'accepting ban appeals currently. Try again later.',
                                                   0xf04a47)  # #


class BanAppealButton(ui.View):
    def __init__(self, bot: commands.Bot, message: Message):
        super().__init__(timeout=604800)
        self.bot = bot
        self.message = message
        self.add_item(ui.Button(label='Appeal Ban', style=ButtonStyle.grey, url='https://dyno.gg/form/8edeab12/'))

    async def on_timeout(self):
        await self.message.edit(view=None)
