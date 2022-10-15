import asyncio
import json
import time
import random
import discord
from discord.ext import commands
from discord.ext import tasks
from config import SUMMON_CHANNEL, TRIVIA, QNA

def fetch_qna():
    with open(QNA, 'r') as f: return json.load(f)

def append_qna(q, a):
    data = fetch_qna()
    data['questions'].append(q)
    data['answers'].append(a)
    with open(QNA, 'w') as f:
        json.dump(data, f, indent=4)

class QNAView(discord.ui.View):
    @discord.ui.button(label='Create QNA!', style=discord.ButtonStyle.green)
    async def callback(self, button, interaction):
        await interaction.response.send_modal(QNAModal())

class QNAModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='Enter new Question and it\'s Answer.')

        self.add_item(discord.ui.InputText(style=discord.InputTextStyle.short, label='Question', placeholder='Question goes here'))
        self.add_item(discord.ui.InputText(style=discord.InputTextStyle.short, label='Answer', placeholder='Answer goes here'))

    async def callback(self, interaction):
        embed = discord.Embed(title='New QNA', color=0xd17015)
        embed.add_field(name='Question', value=self.children[0].value)
        embed.add_field(name='Answer', value=self.children[1].value)
        await interaction.response.send_message(embed=embed)

        append_qna(self.children[0].value, self.children[1].value)

class CommandSet4(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = 0xd17015

        self.fetch_data = fetch_qna()
        self.questions, self.answers = self.fetch_data['questions'], self.fetch_data['answers']

        self.qna = dict(zip(self.questions, self.answers))

    def refresh(self):
        self.fetch_data = fetch_qna()
        self.questions, self.answers = self.fetch_data['questions'], self.fetch_data['answers']

    @commands.Cog.listener()
    async def on_ready(self):
        self.summon_channel = await self.client.fetch_channel(SUMMON_CHANNEL)

    @commands.command(aliases=['st'])
    @commands.has_permissions(manage_channels=True)
    async def start_trivia(self, ctx):
        await ctx.send('Starting trivia games, they will be conducted once every 8 hours.')
        await self.start_game.start()

    @tasks.loop(hours=8)
    async def start_game(self):
        embed = discord.Embed(title='Trivia time!', description='There\'s a trivia game starting soon!', color=self.color)
        embed.add_field(name='Starting in', value=f'<t:{round(time.time() + 30)}:R>')
        await self.summon_channel.send(embed=embed)
        time.sleep(30)

        nums = list(range(len(self.questions)))
        random.shuffle(nums)
        for index, i in enumerate(nums, 1):
            embed = discord.Embed(title=f'Question #{index}', description=self.questions[i], color=self.color)
            await self.summon_channel.send(embed=embed)
            try:
                msg = await self.client.wait_for('message', check=lambda m: m.channel.id == SUMMON_CHANNEL and m.content.lower() == self.answers[i], timeout=10)
                with open(TRIVIA, 'r') as f:
                    text = json.load(f)
                if text.get(str(msg.author.id)):
                    text[str(msg.author.id)] += 2
                else:
                    text[str(msg.author.id)] = 2

                with open(TRIVIA, 'w') as f:
                    json.dump(text, f, indent=4)

                await self.summon_channel.send(f'{msg.author.mention} got the answer first! They have been awarded 2 points.')
            except asyncio.TimeoutError:
                await self.summon_channel.send('No one got a right answer!')

            time.sleep(5)

        embed = discord.Embed(title='The game has ended!', description='GG to everyone who participated!', color=self.color)
        await self.summon_channel.send(embed=embed)

    @commands.command(aliases=['tlb'])
    async def trivialeaderboard(self, ctx):
        with open(TRIVIA, 'r') as f:
            trivia = json.load(f)
        data = [(f'**#{idx}**: {(await self.client.fetch_user(int(i))).mention}: **{v}**', v) for idx, (i, v) in enumerate(trivia.items(), 1)]
        sort = sorted(data, key=lambda i: i[1], reverse=True)
        r = sort[:(min(len(sort), 10))]

        jnt = [i[0] for i in r]

        embed = discord.Embed(title='Trivia leaderboard!', description='\n'.join(jnt), color=self.color)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def new_question(self, ctx):
        await ctx.send(view=QNAView())

    @commands.command(aliases=['ts'])
    async def triviascore(self, ctx):
        with open(TRIVIA, 'r') as f:
            text = json.load(f)

        embed = discord.Embed(title='Your trivia score', color=self.color)
        embed.add_field(name='Your score: ', value=str(text[str(ctx.author.id)]))
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(CommandSet4(client))


