import logging
from pytrivia import Trivia, Type
from discord.ext import commands, tasks
from discord import (
    Embed,
    utils,
    Forbidden,
    HTTPException,
    Message)
from asyncio import sleep, TimeoutError
from math import floor


class TriviaModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = Trivia(True)

        self.game_is_ongoing = False

        self.current_question = None
        self.current_answer = None
        self.current_difficulty = None
        self.current_category = None
        self.current_correct = []

        self.recent_scores = {}
        self.weekly_lb = {}

        self.difficulty_to_points = {
            'easy': 1,
            'medium': 2,
            'hard': 3}

    def cog_unload(self):
        self.weekly_reset.cancel()
        self.trivia_loop_main.cancel()
        self.trivia_game.cancel()

    def generate_question(self) -> None:
        question_data = self.api.request(1, type_=Type.Multiple_Choice)['results'][0]
        while 'which' in question_data['question'].lower() or 'following' in question_data['question'].lower():
            question_data = self.api.request(1, type_=Type.Multiple_Choice)
        self.current_question = question_data['question']
        self.current_answer = question_data['correct_answer']
        self.current_difficulty = question_data['difficulty']
        self.current_category = question_data['category']

    @commands.command(
        brief='',
        description='Starts the trivia event loop. Requires Senior Staff or higher.')
    @commands.guild_only()
    async def start(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        self.weekly_reset.start()
        await self.bot.embed_success(ctx, 'Starting trivia...')

    @commands.command(
        brief='',
        description='Stops the trivia event loop. Requires Senior Staff or higher.')
    @commands.guild_only()
    async def stop(self, ctx: commands.Context):
        if self.bot.member_clearance(ctx.author) < 7:
            return
        self.weekly_reset.cancel()
        self.trivia_loop_main.cancel()
        self.trivia_game.cancel()
        await self.bot.embed_success(ctx, 'Stopping trivia...')

    @tasks.loop(hours=168)
    async def weekly_reset(self):
        self.weekly_lb = {}
        self.trivia_loop_main.start()

    @tasks.loop(hours=8, count=21)
    async def trivia_loop_main(self):
        await self.bot.wait_until_ready()

        if not self.bot.trivia_channel:
            logging.warning('Cancelling upcoming trivia game - Channel not found')
            return

        try:
            embed_soon = Embed(
                colour=0x337fd5, description=f'**Starting <t:{floor(utils.utcnow().timestamp() + 600)}:R>!**')
            embed_soon.set_author(name='Trivia', icon_url=self.bot.user.avatar)
            await self.bot.trivia_channel.send(
                content=self.bot.trivia_role.mention if self.bot.trivia_role else None,
                embed=embed_soon)
            await sleep(600)
            self.trivia_game.start()
            self.game_is_ongoing = True
            self.recent_scores = {}
        except Forbidden:
            logging.warning('Cancelling upcoming trivia game - Missing permissions')
            return
        except HTTPException:
            logging.warning('Cancelling upcoming trivia game - HTTPException')
            return

    @tasks.loop(seconds=50, count=30)
    async def trivia_game(self):
        embed_start = Embed(colour=0x337fd5, description=f'**Next question in 15 seconds!**')
        embed_start.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await self.bot.trivia_channel.send(embed=embed_start)
        await sleep(14)

        self.generate_question()
        question_embed = Embed(colour=0x337fd5, description=f'**{self.current_question}**')
        question_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        question_embed.add_field(name='Category:', value=f'`{self.current_category}`', inline=True)
        question_embed.add_field(name='Difficulty:', value=f'`{self.current_difficulty}`', inline=True)
        await self.bot.trivia_channel.send(embed=question_embed)
        await sleep(7)

        async def end_question():
            for m in self.current_correct:
                try:
                    self.recent_scores[m] += self.difficulty_to_points[self.current_difficulty]
                except KeyError:
                    self.recent_scores[m] = self.difficulty_to_points[self.current_difficulty]

            description = '\n'.join(
                [f"> `{m} - +{self.difficulty_to_points[self.current_difficulty]} Points "
                 f"({self.recent_scores[m]} Total)`" for m in self.current_correct]) if self.current_correct else \
                '`😢 No winners!`'

            winners_embed = Embed(
                colour=0x337fd5,
                description=f'**Answer: {self.current_answer}**\n\n**Winners**\n' + description)
            winners_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
            await self.bot.trivia_channel.send(embed=winners_embed)

        if self.current_correct:
            await end_question()
        else:
            bl = await self.bot.blacklist('trivia')

            def check(msg: Message):
                return msg.content.lower() == self.current_answer.lower() and msg.channel == self.bot.trivia_channel \
                       and msg.author.id not in bl
            try:
                message = await self.bot.wait_for('message', check=check, timeout=23)
                self.current_correct.append(message.author)
            except TimeoutError:
                pass
            finally:
                await end_question()

        self.current_question = None
        self.current_answer = None
        self.current_category = None
        self.current_difficulty = None
        self.current_correct = []

    @trivia_game.after_loop
    async def end_game(self):
        self.game_is_ongoing = False
        for member in self.recent_scores:
            if member in self.weekly_lb:
                self.weekly_lb[member] += self.recent_scores[member]
            else:
                self.weekly_lb[member] = self.recent_scores[member]

        prev_count = 10
        weekly_count = 10
        if len(self.recent_scores) < 10:
            prev_count = len(self.recent_scores)
        if len(self.weekly_lb) < 10:
            weekly_count = len(self.weekly_lb)

        prev_description = '\n'.join(
            [f'`#{list(self.recent_scores).index(member) + 1} | {member}  ({self.recent_scores[member]} Points)`'
             for member in list(self.recent_scores)[:prev_count]])if self.recent_scores else '`No data to display`'
        prev_game_embed = Embed(colour=0x337fd5, title='Previous Game Leaderboard', description=prev_description)
        prev_game_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await self.bot.trivia_channel.send(embed=prev_game_embed)

        weekly_description = '\n'.join(
            [f'`#{list(self.weekly_lb).index(member) + 1} | {member}  ({self.weekly_lb[member]} Points)`'
             for member in list(self.weekly_lb)[:weekly_count]]) if self.weekly_lb else '`No data to display`'
        weekly_embed = Embed(colour=0x337fd5, title='Weekly Leaderboard', description=weekly_description)
        weekly_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await self.bot.trivia_channel.send(embed=weekly_embed)

        self.recent_scores = {}

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not self.game_is_ongoing or not self.current_question or message.channel != self.bot.trivia_channel or \
                message.author.bot or message.content.lower() != self.current_answer.lower() or \
                message.author in self.current_correct or message.author.id in await self.bot.blacklist('trivia'):
            return
        self.current_correct.append(message.author)


async def setup(bot):
    await bot.add_cog(TriviaModule(bot))
