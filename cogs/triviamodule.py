import logging
from pytrivia import Trivia, Type
from discord.ext import commands, tasks
from discord import (
    Interaction,
    ui,
    ButtonStyle,
    utils,
    Embed,
    Forbidden,
    HTTPException
)
from random import shuffle
from time import strftime
from math import floor
from asyncio import sleep


class TriviaModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = Trivia(True)

        self.channel = None

        self.question = None
        self.category = None
        self.difficulty = None
        self.answers = {}
        self.correct_answer = None

        self.correct_users = []
        self.incorrect_users = []

        self.blacklisted_user_ids = []

        self.current_game_lb = {}
        self.weekly_lb = {}

        self.difficulty_mapping = {'easy': 1, 'medium': 2, 'hard': 3}

        self.wait_for_time.start()

    def cog_unload(self):
        self.wait_for_time.cancel()
        self.weekly_reset.cancel()
        self.trivia_cycle.cancel()
        self.trivia_game.cancel()

    def new_question(self) -> None:
        question_data = self.api.request(1, type_=Type.Multiple_Choice)['results'][0]
        self.question = question_data['question']
        self.category = question_data['category']
        self.difficulty = question_data['difficulty']
        answer_list = [question_data['correct_answer']] + question_data['incorrect_answers']
        shuffle(answer_list)
        self.answers = {'A': answer_list[0], 'B': answer_list[1], 'C': answer_list[2], 'D': answer_list[3]}
        self.correct_answer = question_data['correct_answer']

    @tasks.loop(seconds=5)
    async def wait_for_time(self):
        await self.bot.wait_until_ready()
        if strftime('%H:%M') in ['07:50', '15:50', '23:50']:
            self.weekly_reset.start()
            self.wait_for_time.stop()

    @tasks.loop(hours=168)
    async def weekly_reset(self):
        self.weekly_lb = {}
        self.trivia_cycle.start()

    @tasks.loop(hours=8, count=21)
    async def trivia_cycle(self):
        self.channel = self.bot.trivia_channel
        self.blacklisted_user_ids = await self.bot.blacklist('trivia')

        if not self.channel:
            logging.warning('Cancelling upcoming trivia game - Channel not found')
            return

        embed_soon = Embed(
            colour=0x337fd5,
            description=f'**Starting <t:{floor(utils.utcnow().timestamp() + 600)}:R>!**')
        embed_soon.set_author(name='Trivia', icon_url=self.bot.user.avatar)

        try:
            await self.bot.trivia_channel.send(
                content=self.bot.trivia_role.mention if self.bot.trivia_role else None,
                embed=embed_soon)
        except Forbidden:
            logging.warning('Cancelling upcoming trivia game - Missing permissions')
            return
        except HTTPException:
            logging.warning('Cancelling upcoming trivia game - HTTPException')
            return

        await sleep(600)
        self.current_game_lb = {}
        self.trivia_game.start()

    @tasks.loop(seconds=45, count=30)
    async def trivia_game(self):
        embed_soon = Embed(
            colour=0x337fd5,
            description=f'**Next question in 15 seconds!**')
        embed_soon.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await self.bot.trivia_channel.send(embed=embed_soon)

        await sleep(14)
        self.new_question()

        question_embed = Embed(
            colour=0x337fd5,
            description=f'**{self.question}**\n'
                        f'\n> **A) `{self.answers["A"]}`**\n> **B) `{self.answers["B"]}`**'
                        f'\n> **C) `{self.answers["C"]}`**\n> **D) `{self.answers["D"]}`**')
        question_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        question_embed.add_field(name='Category:', value=f'`{self.category}`', inline=True)
        question_embed.add_field(name='Difficulty:', value=f'`{self.difficulty}`', inline=True)

        view = ui.View(timeout=None)
        for label in ['A', 'B', 'C', 'D']:
            view.add_item(TriviaButton(self, label))

        question = await self.channel.send(embed=question_embed, view=view)

        await sleep(15)

        await question.edit(view=None)

        for correct_user in self.correct_users:
            try:
                self.current_game_lb[correct_user] += self.difficulty_mapping[self.difficulty]
            except KeyError:
                self.current_game_lb[correct_user] = self.difficulty_mapping[self.difficulty]

        embed_done = Embed(
            colour=0x337fd5,
            description=f'**Answer: {self.correct_answer}**')
        embed_done.add_field(
            name='Winners',
            value='\n'.join([f"`{user} - +{self.difficulty_mapping[self.difficulty]} Points "
                             f"({self.current_game_lb[user]} Total)`" for user in self.correct_users]) if
            self.correct_users else '`😢 No winners!`',
            inline=False)
        embed_done.add_field(
            name='Losers',
            value='\n'.join([f"`{user}`" for user in self.incorrect_users]) if
            self.incorrect_users else '`😀 No losers!`',
            inline=False)
        embed_done.set_author(name='Trivia', icon_url=self.bot.user.avatar)

        await self.channel.send(embed=embed_done)

        self.correct_users = []
        self.incorrect_users = []

    @trivia_game.after_loop
    async def end_game(self):
        for user in self.current_game_lb:
            try:
                self.weekly_lb[user] += self.current_game_lb[user]
            except KeyError:
                self.weekly_lb[user] = self.current_game_lb[user]

        self.current_game_lb = {u: p for u, p in sorted(
            self.current_game_lb.items(), key=lambda item: item[1], reverse=True)}
        self.weekly_lb = {u: p for u, p in sorted(
            self.weekly_lb.items(), key=lambda item: item[1], reverse=True)}

        prev_count = 10
        weekly_count = 10
        if len(self.current_game_lb) < 10:
            prev_count = len(self.current_game_lb)
        if len(self.weekly_lb) < 10:
            weekly_count = len(self.weekly_lb)

        thanks_embed = Embed(colour=0x337fd5, title='Thanks For Playing!')

        prev_description = '\n'.join(
            [f'`#{list(self.current_game_lb).index(member) + 1} | {member}  ({self.current_game_lb[member]} Points)`'
             for member in list(self.current_game_lb)[:prev_count]]) if self.current_game_lb else '`No data to display`'
        prev_game_embed = Embed(colour=0x337fd5, title='Previous Game Leaderboard', description=prev_description)
        prev_game_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)

        weekly_description = '\n'.join(
            [f'`#{list(self.weekly_lb).index(member) + 1} | {member}  ({self.weekly_lb[member]} Points)`'
             for member in list(self.weekly_lb)[:weekly_count]]) if self.weekly_lb else '`No data to display`'
        weekly_embed = Embed(colour=0x337fd5, title='Weekly Leaderboard', description=weekly_description)
        weekly_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)

        await self.channel.send(embeds=[thanks_embed, prev_game_embed, weekly_embed])

    @commands.command(
        brief='',
        description='View the previous trivia game leaderboard.',
        aliases=['lb'],
        extras=0)
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        prev_count = 10
        if len(self.current_game_lb) < 10:
            prev_count = len(self.current_game_lb)
        prev_description = '\n'.join(
            [f'`#{list(self.current_game_lb).index(member) + 1} | {member}  ({self.current_game_lb[member]} Points)`'
             for member in list(self.current_game_lb)[:prev_count]]) if self.current_game_lb else '`No data to display`'
        prev_game_embed = Embed(colour=0x337fd5, title='Previous Game Leaderboard', description=prev_description)
        prev_game_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await ctx.send(embed=prev_game_embed)

    @commands.command(
        brief='',
        description='View the weekly trivia leaderboard.',
        extras=0)
    @commands.guild_only()
    async def weekly(self, ctx: commands.Context):
        weekly_count = 10
        if len(self.weekly_lb) < 10:
            weekly_count = len(self.weekly_lb)
        weekly_description = '\n'.join(
            [f'`#{list(self.weekly_lb).index(member) + 1} | {member}  ({self.weekly_lb[member]} Points)`'
             for member in list(self.weekly_lb)[:weekly_count]]) if self.weekly_lb else '`No data to display`'
        weekly_embed = Embed(colour=0x337fd5, title='Weekly Leaderboard', description=weekly_description)
        weekly_embed.set_author(name='Trivia', icon_url=self.bot.user.avatar)
        await ctx.send(embed=weekly_embed)


class TriviaButton(ui.Button):
    def __init__(self, trivia: TriviaModule, label: str):
        super().__init__(label=label, style=ButtonStyle.grey)
        self.trivia = trivia

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id in self.trivia.blacklisted_user_ids:
            await self.trivia.bot.send_ephemeral_response(
                interaction, '❌ You\'ve been blacklisted from competing in trivia games.', 0xf04a47)
            return

        if interaction.user in self.trivia.correct_users:
            self.trivia.correct_users.remove(interaction.user)
        if interaction.user in self.trivia.incorrect_users:
            self.trivia.incorrect_users.remove(interaction.user)

        if self.trivia.answers[self.label] == self.trivia.correct_answer:
            self.trivia.correct_users.append(interaction.user)
        else:
            self.trivia.incorrect_users.append(interaction.user)

        await self.trivia.bot.send_ephemeral_response(
            interaction, f'*Answer selected: `{self.trivia.answers[self.label]}`*', 0x43b582)


async def setup(bot):
    await bot.add_cog(TriviaModule(bot))
