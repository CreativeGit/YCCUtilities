import discord
from main import punish, Punishment
from discord.ext import commands
from discord.ext.commands import MemberConverter
from config import VALID_COLOR, INVALID_COLOR, MODLOGS, DATABASE
import json

class CommandSet5(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.MODLOGS_CHANNEl = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.MODLOGS_CHANNEl = await self.client.fetch_channel(MODLOGS)

    @commands.command(aliases=['fs'])
    @commands.has_permissions(manage_guild=True)
    async def filestrike(self, ctx, user: MemberConverter, reason='Reason not provided'):
        punish(user.id, Punishment(ctx, reason, user, ctx.message.jump_url, 'filestrike'))

        embed = discord.Embed(title='User has been filestriked', description='This user has been filestriked.', color=VALID_COLOR)
        await ctx.send(embed=embed)

        modlogs = discord.Embed(title='Filestrike command issued.', description=f'User {user.id} ({user.mention}) has been filestriked.', color=VALID_COLOR)
        modlogs.add_field(name='Reason', value=reason)
        modlogs.add_field(name='Responsible mod', value=ctx.author.mention)

        await self.MODLOGS_CHANNEl.send(embed=modlogs)

    @commands.command(aliases=['fsh'])
    @commands.has_permissions(manage_guild=True)
    async def filestrikehistory(self, ctx, user: MemberConverter):  # DO NOT USE THIS! IT WILL CAUSE AN ERROR!
        with open(DATABASE, 'r') as f:
            text = json.load(f)
        cases = text['cases']
        user_cases = [case for case in cases if case[1]]

        embed = discord.Embed(title=f'{user.mention}\'s filestrikes.', color=VALID_COLOR)

        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(CommandSet5(client))
