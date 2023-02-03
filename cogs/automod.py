from discord.ext import commands, tasks
from discord import Message, NotFound, Forbidden, Embed, utils
from re import findall
from datetime import timedelta
from asyncio import sleep
from core.modlogs import ModLogsByUser
from math import floor


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^" \
                     r"\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        self.member_recent_infractions = {}

    def cog_load(self):
        self.infraction_cooldown.start()

    def cog_unload(self):
        self.infraction_cooldown.stop()

    @tasks.loop(seconds=60)
    async def infraction_cooldown(self):
        await self.bot.wait_until_ready()
        await sleep(40)

        for user_id in self.member_recent_infractions:
            self.member_recent_infractions[user_id] -= 1

        delete = [key for key in self.member_recent_infractions if self.member_recent_infractions[key] <= 0]
        for key in delete:
            del self.member_recent_infractions[key]

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        urls = findall(self.regex, message.content)

        if not urls or not message.guild or self.bot.member_clearance(message.author) > 2 or \
                [role for role in message.author.roles if role in self.bot.immune_roles] or \
                message.channel in self.bot.immune_channels:
            return

        try:
            await message.delete()
            await message.channel.send(f'{message.author.mention}, that link is not allowed.', delete_after=5)
        except (Forbidden, NotFound):
            return

        if message.author.id in self.member_recent_infractions:
            self.member_recent_infractions[message.author.id] += 1
        else:
            self.member_recent_infractions[message.author.id] = 1

        if self.member_recent_infractions[message.author.id] % 5:
            return
        self.member_recent_infractions.pop(message.author.id)

        user_logs = ModLogsByUser(message.author)
        reason = '[AUTO] 5 Auto-Mod infractions.'

        try:
            await message.author.timeout(timedelta(seconds=120))
            await user_logs.add_log(self.bot.user.id, 'Mute', reason, 120, 0)
            await message.author.send(embed=Embed(
                colour=0xf04a47, description=f'***You were muted in {self.bot.guild} until '
                                             f'<t:{floor(utils.utcnow().timestamp() + 120)}:F> for:*** {reason}'))
        except Forbidden:
            return


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
