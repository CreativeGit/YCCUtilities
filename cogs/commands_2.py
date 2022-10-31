import discord
from discord.utils import get
from discord.ui import View, Button
from discord.ext import commands
from discord.ext.commands import has_permissions, has_role
from discord.ext.commands import MemberConverter, RoleConverter
from config import PERSIST, VALID_COLOR, INVALID_COLOR
from config import SUGGESTIONS_CHANNEL, SUGGESTIONS_BL, NAMES
from config import COLOR_ROLE, MODLOGS, DATABASE, SUB_ROLES
from main import Duration, Punishment, PunishmentFromMessage
from main import fetch_user_data as fud, punish
from main import FlagReason
import json
import random
from datetime import timedelta, datetime, timezone
import re
import string
import normalize
import os
import typing

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
	async def agreed(self, _, interaction):
		if interaction.user.id in self.interacted_users:
			await interaction.response.send_message('You have already voted!', ephemeral=True)
			return
		self.data[0] += 1
		await interaction.response.edit_message(embed=self.em.edit(self.data))

	@discord.ui.button(label='I disagree!', emoji='👎', style=discord.ButtonStyle.red)
	async def disagreed(self, _, interaction):
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
		self.modlog_channel = None

	@commands.Cog.listener()
	async def on_ready(self):
		self.modlog_channel = await self.client.fetch_channel(MODLOGS)

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
		msg_id = link.split('/')[-1]
		msg = await ctx.fetch_message(int(msg_id))
		embed = discord.Embed(title=f'Message by {msg.author}', description=f'Message: {msg.content}', color=VALID_COLOR)

		await ctx.send(embed=embed)

	@commands.command()
	async def remindme(self, ctx, duration: Duration):
		embed = discord.Embed(title='Reminder set.', description=f'I\'ll remind you on <t:{round(time.time()) + duration[-1]}:', color=VALID_COLOR)
		await ctx.send(embed=embed)
		await asyncio.sleep(duration[-1])
		await ctx.send(f"{ctx.author.mention}! Your alarm is ringing! :alarm_clock:")

	@commands.command(aliases=['ui'])
	async def userinfo(self, ctx, target: typing.Optional[MemberConverter]):
		target = target or ctx.author

		print(target.public_flags.all())

		embed = discord.Embed(description=f"{target.mention}\nName: `{target.name}`\n<:person:1019962716724670494> Username: **{target.name}**\n   Tag: {target}\n:identification_card: ID: {target.id}\n<:personadd:1019962814946869279> Creation: <t:{target.created_at.timestamp():.0f}:R>\n<:IconCalendar:1019962838988632104> Joined on: <t:{target.joined_at.timestamp():.0f}:R>", color=VALID_COLOR)
		embed.set_author(name=target, icon_url=target.avatar.url)
		embed.set_thumbnail(url=target.avatar.url)

		await ctx.send(embed=embed)

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot or message.author.guild_permissions.manage_messages:
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

			link = re.search(r'https?://.*(.*)', content).group(1)
			if link in restrictions:
				return
			await message.delete()

		if len(message.mentions) >= 5:
			punish(message.author.id, PunishmentFromMessage(message, 'Mass mention', message.author, message.jump_url, 'ban'))
			await message.delete()

	@commands.command()
	@has_permissions(manage_channels=True)
	async def warn(self, ctx, member: MemberConverter, *, flg_reason: FlagReason):
		flags, reason = flg_reason
		log_data = Punishment(ctx, reason, member, ctx.message.jump_url, 'warn')
		case = punish(member.id, log_data)

		embed = discord.Embed(title='User has been warned.', description=f'Reason: **{reason}**', color=VALID_COLOR)
		await ctx.send(embed=embed)

		if 's' not in flags:
			embed = discord.Embed(title='You have been warned!', description=f'You have been warned!', color=VALID_COLOR)
			embed.add_field(name='Reason', value=reason)
			await member.send(embed=embed)

		modlog_embed = discord.Embed(title='Warn Command Issued', description=f'Moderator {ctx.author} warned {member}.', color=VALID_COLOR)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)
		modlog_embed.add_field(name='Case number', value=case)

		await self.modlog_channel.send(embed=modlog_embed)

	@commands.group(invoke_without_command=True)
	@has_permissions(manage_messages=True)
	async def purge(self, ctx, limit: typing.Optional[int] = 100, mem_roles: commands.Greedy[typing.Union[MemberConverter, RoleConverter]] = (), *, reason='Reason not provided'):
		ids = [mem_role.id for mem_role in mem_roles]
		history = (await ctx.channel.history().flatten())[1:]
		count = 0
		file_name = f'purge_{"".join(random.choices(string.ascii_letters, k=8))}.txt'
		with open(file_name, 'a') as file:
			for message in history:
				roles = [role.id for role in message.author.roles]
				if mem_roles == () or message.author.id in ids or any(rid in roles for rid in ids):
					try:
						file.write(f'[{message.author}] ({message.author.id}) >>> {message.content}' + '\n')
					except UnicodeEncodeError:
						file.write(f'[{message.author}] ({message.author.id}) >>> (invalid characters)')

					await message.delete()
					count += 1
					if count == limit:
						break
		await ctx.message.delete()
		file = discord.File(fp=file_name)

		modlog_embed = discord.Embed(title='Purge Command Issued', description=f'Moderator {ctx.author} purged messages', color=VALID_COLOR)
		modlog_embed.add_field(name='Purged from channel', value=ctx.channel.mention, inline=False)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Messages purged of', value=', '.join([member.mention for member in mem_roles]) if mem_roles != () else 'All', inline=False)
		modlog_embed.add_field(name='Number of messages purged:', value=limit)

		await self.modlog_channel.send(embed=modlog_embed, file=file)

		os.remove(f'./{file_name}')

	@purge.command()
	async def match(self, ctx, limit: int, *, text: str):
		del_all = text.endswith('-o')
		text = text if not del_all else text[:-3]
		to_delete = []
		for message in (await ctx.channel.history().flatten())[1:]:
			if len(to_delete) == limit:
				break

			if ((not del_all) and text.lower() in message.content.lower()) or (del_all and text.lower() == message.content.lower()):
				to_delete.append(message)

		file_name = f'purge_{"".join(random.choices(string.ascii_letters, k=8))}.txt'
		with open(file_name, 'w') as f:
			f.write('\n'.join(f'[{msg.author}] ({msg.author.id}) >>> {msg.content}' for msg in to_delete))

		await ctx.channel.delete_messages(to_delete)
		modlogs = discord.Embed(title=f'Messages deleted', description=f'Messages deleted in {ctx.channel.mention}', color=VALID_COLOR)
		modlogs.add_field(name='Messages deleted', value=str(len(to_delete)), inline=False)
		modlogs.add_field(name='Text matching', value=text, inline=False)
		modlogs.add_field(name='Delete containing?', value=['Yes', 'No'][del_all], inline=False)
		modlogs.add_field(name='Issued by', value=ctx.message.author)

		await self.modlog_channel.send(embed=modlogs, file=discord.File(file_name))
		await ctx.message.delete()
		os.remove(f'./{file_name}')

	@commands.command()
	@has_permissions(manage_channels=True)
	async def reason(self, ctx, case_number: int, *, reason):
		with open(DATABASE, 'r') as f:
			text = json.load(f)
		text['cases'][case_number-1]['reason'] = reason
		with open(DATABASE, 'w') as f:
			json.dump(text, f, indent=4)

		embed = discord.Embed(title='Warn Reason Changed', color=VALID_COLOR)
		embed.add_field(name='New Reason', value=reason)
		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def kick(self, ctx, target: MemberConverter, *, flg_reason: FlagReason):
		flags, reason = flg_reason
		if target.guild_permissions.manage_messages:
			embed = discord.Embed(title='Invalid!', description='You can\'t your fellow mod!', color=INVALID_COLOR)
			await ctx.send(embed=embed)
			return

		punish(target.id, Punishment(ctx, reason, target, ctx.message.jump_url, 'kick'))
		embed = discord.Embed(title='User has been kicked!', description=f'User {target} has been kicked!', color=VALID_COLOR)
		await ctx.send(embed=embed)

		if 's' not in flags:
			embed = discord.Embed(title='You have been kicked!', description=f'You have been kicked from {ctx.guild.name}!', color=VALID_COLOR)
			embed.add_field(name='Reason', value=reason)
			await target.send(embed=embed)
		await target.kick()

		modlog_embed = discord.Embed(title='Kick Command Issued', description=f'Moderator {ctx.author} kicked {target}', color=VALID_COLOR)
		modlog_embed.add_field(name="Reason", value=reason)

		await self.modlog_channel.send(embed=modlog_embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def decancer(self, ctx, target: MemberConverter):
		old, new = target.display_name, normalize(target.display_name)
		await target.edit(nick=new)
		embed = discord.Embed(title='Successfully decancered', description=f'User {target.mention}\'s name has been decancered.', color=VALID_COLOR)
		embed.add_field(name='Old', value=old)
		embed.add_field(name='New', value=new)

		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(manage_messages=True)
	async def softban(self, ctx, member: MemberConverter, *, reason: str = 'Reason not provided'):
		contents = []
		for channel in ctx.guild.text_channels:
			async for message in channel.history():
				if message.author.id == member.id:
					contents.append(f'[in {message.channel}]: {message.content}')
					await message.delete()

		file_name = f'softban_{"".join(random.choices(string.ascii_letters, k=8))}.txt'
		with open(file_name, 'w') as f:
			f.write('\n'.join(contents))

		punish(member.id, Punishment(ctx, reason, member, ctx.message.jump_url, 'softban'))

		modlogs = discord.Embed(title='Softban command invoked', description=f'User {member.mention} has been softbanned', color=VALID_COLOR)
		modlogs.add_field(name='Reason', value=reason, inline=False)

		await self.modlog_channel.send(embed=modlogs, file=discord.File(file_name))
		await member.kick()
		os.remove(file_name)

	@commands.Cog.listener()
	async def on_member_update(self, old, new):
		o_roles, n_roles = old.roles, new.roles
		n_rids = [r.id for r in n_roles if r.id in SUB_ROLES]
		if n_rids:
			if len(n_roles) > len(o_roles):
				for item in n_roles:
					if item not in o_roles:
						break
				to_remove = sorted(n_rids, key=lambda i: SUB_ROLES.index(i))[1:]
				await new.remove_roles(*[r for r in n_roles if r.id in to_remove])


def setup(client):
	client.add_cog(CommandSet2(client))

