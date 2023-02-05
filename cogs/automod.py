import logging
from discord.ext import commands, tasks
from discord import Message, NotFound, Forbidden, Embed, utils
from datetime import timedelta
from asyncio import sleep
from core.modlogs import ModLogsByUser
from math import floor
from re import findall
from urllib.parse import urlparse


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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
        urls = findall(r'(https?://\S+)', message.content)
        domains = [urlparse(url).netloc for url in urls]

        if not domains or message.guild != self.bot.guild or self.bot.member_clearance(message.author) > 1:
            return
        elif [domain for domain in domains if domain in self.bot.blacklisted_domains]:
            pass
        elif [role for role in message.author.roles if role in self.bot.immune_roles]:
            return
        elif not [domain for domain in domains if domain not in self.bot.whitelisted_domains] and \
                message.channel in self.bot.immune_channels:
            return

        try:
            await message.delete()
            await message.channel.send(f'{message.author.mention}, that link is not allowed.', delete_after=5)
        except (Forbidden, NotFound):
            logging.warning('Failed to delete message')
            return

        try:
            self.member_recent_infractions[message.author.id] += 1
        except KeyError:
            self.member_recent_infractions[message.author.id] = 1

        if self.member_recent_infractions[message.author.id] % 5:
            return
        self.member_recent_infractions.pop(message.author.id)

        try:
            await message.author.timeout(timedelta(seconds=120))
        except Forbidden:
            logging.warning('Failed to time member out for auto-mod violations')
            return

        user_logs = ModLogsByUser(message.author)
        await user_logs.add_log(self.bot.user.id, 'Mute', '[AUTO] 5 Auto-Mod infractions.', 120, 0)

        try:
            await message.author.send(embed=Embed(
                colour=0xf04a47,
                description=f'***You were muted in {self.bot.guild} until '
                            f'<t:{floor(utils.utcnow().timestamp() + 120)}:F> for:*** [AUTO] 5 Auto-Mod infractions.'))
        except Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
