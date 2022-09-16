import discord
from discord.utils import get
from discord.ui import View, Button
from discord.ext import commands
from discord.ext.commands import has_permissions, has_role
from discord.ext.commands import MemberConverter, RoleConverter
from config import PERSIST, VALID_COLOR, INVALID_COLOR
from config import SUGGESTIONS_CHANNEL, SUGGESTIONS_BL, NAMES
from config import COLOR_ROLE
from main import Duration, Punishment
from main import fetch_user_data as fud, dump_user_data as dud
import json
import random
from datetime import timedelta, datetime, timezone
import re

class LinkMod:
	def __init__(self, restrictions):
		self.restrictions = restrictions


suggestions = []
id_link = {1019933300653035540: 1, 1019571036875931709: LinkMod(['youtube'])}

class HexConverter(commands.Converter):
	async def convert(self, ctx, arg):
		return int(arg, 16)

class SuggestionView(View):
	def __init__(self, em):
		super().__init__()
		self.data = [0, 0]
		self.interacted_users = []
		self.em = em
		suggestions.append([self])
		self.case_number = len(suggestions)

	@discord.ui.button(label='I agree!', emoji='👍', style=discord.ButtonStyle.green)
	async def agreed(self, button, interaction):
		if interaction.user.id in self.interacted_users:
			await interaction.response.send_message('You have already voted!', ephemeral=True)
			return
		self.data[0] += 1
		await interaction.response.edit_message(embed=self.em.edit(self.data))

	@discord.ui.button(label='I disagree!', emoji='👎', style=discord.ButtonStyle.red)
	async def disagreed(self, button, interaction):
		if interaction.user.id in self.interacted_users:
			await interaction.response.send_message('You have already voted!', ephemeral=True)
			return
		self.data[1] += 1
		await interaction.response.edit_message(embed=self.em.edit(self.data))

class SuggestionEmbed(discord.Embed):
	def __init__(self, user, suggestion, case_id):
		self.user = user
		title = f'Suggestion by {user}: Suggestion {case_id}'
		description = suggestion

		super().__init__(title=title, description=description, color=VALID_COLOR)
		self.add_field(name='Up votes', value='0')
		self.add_field(name='Down votes', value='0')

	def edit(self, data):
		self.set_field_at(0, name='Up votes', value=data[0])
		self.set_field_at(1, name='Down votes', value=data[1])
		return self

	def accepted(self):
		self.title += '\n**__suggestion has been accepted__**'
		self.color = 0x32a852
		return self

	def declined(self):
		self.title += '\n**__suggestion has been declined__**'
		self.color = INVALID_COLOR
		return self

class CommandSet2(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_member_join(self, member):
		with open(PERSIST, 'r') as f:
			text = json.load(f)

		if str(member.id) in text:
			for role in text[str(member.id)]:
				await member.add_roles(member.guild.get_role(role), reason='Role Persist')

	@commands.command(aliases=['rp', 'rolep'])
	@has_permissions(manage_roles=True)
	async def rolepersist(self, ctx, target: MemberConverter, role: RoleConverter):
		with open(PERSIST, 'r') as f:
			text = json.load(f)

		if str(target.id) in text:
			text[str(target.id)].append(role.id)
		else:
			text[str(target.id)] = [role.id]

		with open(PERSIST, 'w') as f:
			json.dump(text, f, indent=4)

		embed = discord.Embed(title=f'User has been permanently given a role.', description=f'User {target.mention} has been permanently the {role.name!r} role.', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command()
	@commands.cooldown(1, 86400, commands.BucketType.member)
	async def suggest(self, ctx, *, suggestion):
		if SUGGESTIONS_BL in list(map(lambda role: role.id, ctx.author.roles)):
			embed = discord.Embed(title='You can\'t run this command!', description='You are blacklisted from making any suggestions!', color=INVALID_COLOR)
			await ctx.send(embed=embed)
			return

		channel = await self.client.fetch_channel(SUGGESTIONS_CHANNEL)
		em = SuggestionEmbed(ctx.author, suggestion, len(suggestions)+1)
		message = await channel.send(embed=em, view=SuggestionView(em))
		suggestions[-1].append(message.id)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def accept(self, ctx, case_no: int):
		if case_no > len(suggestions):
			await ctx.send('There isn\'t a case with that number!')
			return

		case = suggestions[case_no-1]

		for item in case[0].children:
			item.disabled = True

		message = await ctx.fetch_message(case[1])
		await message.edit(embed=case[0].em.accepted(), view=case[0])

	@commands.command()
	@has_permissions(manage_channels=True)
	async def decline(self, ctx, case_no: int):
		if case_no > len(suggestions):
			await ctx.send('There isn\'t a case with that number!')
			return

		case = suggestions[case_no-1]

		for item in case[0].children:
			item.disabled = True

		message = await ctx.fetch_message(case[1])
		await message.edit(embed=case[0].em.declined(), view=case[0])

	@commands.command()
	@has_permissions(manage_channels=True)
	async def modnick(self, ctx, target: MemberConverter):
		name = random.choice(NAMES)
		await target.edit(nick=name)
		embed = discord.Embed(title='Name changed!', description=f'User {target.mention}\'s name has been changed.', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command(aliases=['cc'])
	@has_role(COLOR_ROLE)
	async def change_color(self, ctx, *, color: HexConverter):
		role = get(ctx.guild.roles, id=COLOR_ROLE)
		await role.edit(color=color)
		embed = discord.Embed(title='Role color changed.', description=f'The role color has been changed to hex {color}', color=color)
		await ctx.send(embed=embed)

	@commands.command()
	async def quote(self, ctx, link):
		id = link.split('/')[-1]
		msg = await ctx.fetch_message(int(id))
		embed = discord.Embed(title=f'Message by {msg.author}', description=f'Message: {msg.content}', color=VALID_COLOR)

		await ctx.send(embed=embed)

	@commands.command()
	async def remindme(self, ctx, duration: Duration):
		embed = discord.Embed(title='Reminder set.', description=f'I\'ll remind you on <t:{round(time.time()) + duration[-1]}:', color=VALID_COLOR)
		await ctx.send(embed=embed)
		await asyncio.sleep(duration[-1])
		await ctx.send(f"{ctx.author.mention}! Your alarm is ringing! :alarm_clock:")

	@commands.command(aliases=['ui'])
	async def userinfo(self, ctx, target: MemberConverter = None):
		target = target or ctx.author

		print(target.public_flags.all())

		embed = discord.Embed(description=f"{target.mention}\nName: `{target.name}`\n<:person:1019962716724670494> Username: **{target.name}**\n   Tag: {target}\n:identification_card: ID: {target.id}\n<:personadd:1019962814946869279> Creation: <t:{target.created_at.timestamp():.0f}:R>\n<:IconCalendar:1019962838988632104> Joined on: <t:{target.joined_at.timestamp():.0f}:R>", color=VALID_COLOR)
		embed.set_author(name=target, icon_url=target.avatar.url)
		embed.set_thumbnail(url=target.avatar.url)

		await ctx.send(embed=embed)

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot:
			return
		content = message.content
		if 'https://' in content or 'http://' in content:
			for role in message.author.roles:
				if role.id in id_link:
					restrictions = id_link[role.id].restrictions
					break
			else:
				restrictions = LinkMod(2).restrictions

			if restrictions == 1:
				return
			if restrictions == 2:
				await message.delete()

			link = re.search(r'http[s]?://.*(.*)', content).group(1)
			if link in restrictions:
				return
			await message.delete()

	@commands.command()
	@has_permissions(manage_channels=True)
	async def warn(self, ctx, member: MemberConverter, *, reason='Reason not provided'):
		log_data = Punishment(ctx, reason, member, ctx.message.jump_url)

		user_data = fud(member.id)
		user_data['violations']['warns'].append(log_data)
		dud(member.id, user_data)

		embed = discord.Embed(title='User has been warned.', description=f'Reason: **{reason}**', color=VALID_COLOR)
		await ctx.send(embed=embed)

def setup(client):
	client.add_cog(CommandSet2(client))

