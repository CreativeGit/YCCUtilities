import json
import time
from collections import defaultdict
import os
import random
import discord
from discord.ext import commands
from discord.ext import tasks
from config import INVALID_COLOR, KILLS, SUMMON_CHANNEL

creatures = ['zombie', 'ghost', 'mummy', 'witch', 'vampire']
descriptions = ['zombie lorem ipsum', 'ghost lorem ipsum', 'mummy lorem ipsum', 'witch lorem ipsum', 'vampire lorem ipsum']
emojis = [':zombie:', ':ghost:', ':m:', ':regional_indicator_w:', ':vampire:']
multipliers = [1, 1, 1.5, 1.5, 2]

cr_mt = dict(zip(creatures, multipliers))
cr_dc = dict(zip(creatures, descriptions))
cr_ej = dict(zip(creatures, emojis))

items = ['sword', 'staff', 'penknife']

user_data = defaultdict(lambda: dict(zip(items, [2, 4, 8])))

def used_check(item_type):
    def pred(ctx):
        return user_data[ctx.author.id][items[item_type]] != 0
    return commands.check(pred)


class CommandSet3(commands.Cog):
    def __init__(self, client):
        self.color = 0xd17015
        self.client = client
        self.summon_data = {}
        self.damage_dealt = defaultdict(lambda: 0)
        self.summon_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.summon_channel = await self.client.fetch_channel(SUMMON_CHANNEL)
        await self.reset.start()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def start_common(self, ctx):
        self.summon_common.start()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def start_mid(self, ctx):
        self.summon_mid.start()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def start_rare(self, ctx):
        self.summon_rare.start()

    @tasks.loop(minutes=20)
    async def summon_common(self):
        await self.summon_creature(['zombie', 'ghost'][random.randint(0, 1)])

    @tasks.loop(minutes=50)
    async def summon_mid(self):
        await self.summon_creature(['mummy', 'witch'][random.randint(0, 1)])

    @tasks.loop(minutes=120)
    async def summon_rare(self):
        await self.summon_creature('vampire')

    @tasks.loop(hours=24)
    async def reset(self):
        global user_data
        user_data.clear()

    def deduct_hp(self, ctx, amt):
        curr = self.summon_data[ctx.channel.id]
        new = (curr[0] - amt, *curr[1:])
        self.summon_data[ctx.channel.id] = new

        self.damage_dealt[ctx.author.id] += amt

        if new[0] <= 0:
            embed = discord.Embed(title='Vanquish me!', description='I have been vanquished!', color=self.color)
            embed.add_field(name='HP', value='Dead :dizzy_face:')
            data = self.summon_data.pop(ctx.channel.id)

            with open(KILLS, 'r') as f:
                text = json.load(f)

            if str((max_dmg := max(self.damage_dealt, key=lambda uid: self.damage_dealt[uid]))) in text:
                text[str(max_dmg)] += (2 * cr_mt[data[1]])
            else:
                text[str(max_dmg)] = 2 * cr_mt[data[1]]

            if str(ctx.author.id) in text:
                text[str(ctx.author.id)] += cr_mt[data[1]]
            else:
                text[str(ctx.author.id)] = cr_mt[data[1]]

            with open(KILLS, 'w') as f:
                json.dump(text, f, indent=4)

            self.damage_dealt.clear()
            return embed
        else:
            embed = discord.Embed(title='Vanquish me!', description='Boo! :ghost:', color=self.color)
            embed.add_field(name='HP', value=str(new[0]))

            return embed

    async def summon_creature(self, creature: str):
        embed = discord.Embed(title='Vanquish me!', description='Boo! :ghost:', color=self.color)
        embed.add_field(name='HP', value=cr_mt[creature] * 100)

        msg = await self.summon_channel.send(embed=embed)
        self.summon_data[self.summon_channel.id] = (cr_mt[creature] * 100, creature, msg)

    @commands.command()
    async def summon(self, ctx, creature):
        await self.summon_creature(creature)
        await ctx.send('This command is just for debugging and testing purposes, it will be removed later.')

    @commands.command()
    @used_check(0)
    async def sword(self, ctx):
        if ctx.channel.id in self.summon_data:
            data = self.summon_data[ctx.channel.id]

            em = self.deduct_hp(ctx, 100)
            await data[2].edit(embed=em)
            user_data[ctx.author.id]['sword'] -= 1
        else:
            embed = discord.Embed(title='Couldn\'t use sword!',
                                  description='There\'s no monsters nearby to attack with your sword! Try again later!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)

    @sword.error
    async def sword_error(self, ctx, err):
        if isinstance(err, commands.CheckFailure):
            embed = discord.Embed(title='Sword usage failed',
                                  description='You couldn\'t use the sword! You\'ve already used it in the past 24 hours!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)
        else:
            print(type(err), err)

    @commands.command()
    @used_check(1)
    async def staff(self, ctx):
        if ctx.channel.id in self.summon_data:
            data = self.summon_data[ctx.channel.id]

            em = self.deduct_hp(ctx, 50)
            await data[2].edit(embed=em)
            user_data[ctx.author.id]['staff'] -= 1
        else:
            embed = discord.Embed(title='Couldn\'t use staff!',
                                  description='There\'s no monsters nearby to attack with your staff! Try again later!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)

    @staff.error
    async def staff_error(self, ctx, err):
        if isinstance(err, commands.CheckFailure):
            embed = discord.Embed(title='Staff usage failed',
                                  description='You couldn\'t use the staff! You\'ve already used it in the past 24 hours!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)

    @commands.command()
    @used_check(2)
    async def penknife(self, ctx):
        if ctx.channel.id in self.summon_data:
            data = self.summon_data[ctx.channel.id]

            em = self.deduct_hp(ctx, 25)
            await data[2].edit(embed=em)
            user_data[ctx.author.id]['penknife'] -= 1
        else:
            embed = discord.Embed(title='Couldn\'t use penknife!!',
                                  description='There\'s no monsters nearby to attack with your penknife! Try again later!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)

    @penknife.error
    async def penknife_error(self, ctx, err):
        if isinstance(err, commands.CheckFailure):
            embed = discord.Embed(title='Penknife usage failed',
                                  description='You couldn\'t use the penknife! You\'ve already used it in the past 24 hours!',
                                  color=INVALID_COLOR)
            await ctx.send(embed=embed)

    @commands.command(aliases=['hs'])
    async def halloweenscore(self, ctx):
        with open(KILLS, 'r') as f:
            text = json.load(f)

        embed = discord.Embed(title='Your halloween kill score', color=self.color)
        embed.add_field(name='Your score: ', value=str(text[str(ctx.author.id)]))
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['hlb'])
    async def halloweenleaderboard(self, ctx):
        with open(KILLS, 'r') as f:
            kills = json.load(f)
        data = [(f'**#{idx}**: {(await self.client.fetch_user(int(i))).mention}: **{v}**', v) for idx, (i, v) in enumerate(kills.items(), 1)]
        sort = sorted(data, key=lambda i: i[1], reverse=True)
        r = sort[:(min(len(sort), 10))]

        jnt = [i[0] for i in r]

        embed = discord.Embed(title='Kills leaderboard!', description='\n'.join(jnt), color=self.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def listcreatures(self, ctx):
        embed = discord.Embed(title='All creatures', color=self.color)
        for cr, dc, ej in zip(creatures, descriptions, emojis):
            embed.add_field(name=f'{ej} {cr.capitalize()}', value=dc, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def halloweenhelp(self, ctx):
        embed = discord.Embed(title='Welcome to Halloween!', description='Here are the halloween commands:', color=self.color)
        embed.add_field(name=':sword: Sword', value='`>sword` Use your sword to kill monsters, deals 100 damage. Can be used once every 24 hours.', inline=False)
        embed.add_field(name=':chopsticks: Staff', value='`>staff` Use your staff to kill monsters, deals 50 damage. Can be used twice every 24 hours.', inline=False)
        embed.add_field(name=':dagger: Penknife', value='`>penknife` Use your penknife to kill monsters, deals 25 damage. Can be used 4 times every 24 hours.', inline=False)
        embed.add_field(name='Leaderboard', value='`>lb` or `>leaderboard` Shows the players with the most points, obtained from killing monsters.', inline=False)
        embed.add_field(name='Monsters', value='There are 5 monsters that can spawn:\n:vampire: Vampires\n:zombie: Zombies\n:ghost: Ghosts\n:m: Mummies\n:regional_indicator_w: Witches', inline=False)

        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(CommandSet3(client))

