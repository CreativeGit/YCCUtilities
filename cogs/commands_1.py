import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from discord.errors import HTTPException
from discord.ext.commands import MemberConverter
from config import VALID_COLOR, INVALID_COLOR, FAQ, MODLOGS, LOCK_BYPASS
from main import Duration, Punishment, is_convertible
from main import fetch_user_data as fud, dump_user_data as dud
import time
import asyncio
import datetime
import json

class CommandSet1(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		self.start_time = time.time()

	@commands.command(aliases=['cb', 'channelban'])
	@has_permissions(ban_members=True) # the user must have ban member permissions to run this command
	async def channel_ban(self, ctx, member: MemberConverter, channel: discord.TextChannel, duration: Duration = ('1h', 3600), *, reason='Reason not provided'):
		log_data = Punishment(ctx, reason, member, ctx.message.jump_url, duration)

		user_data = fud(member.id)
		user_data['violations']['cbans'].append(log_data)
		dud(member.id, user_data)

		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=False, view_channel=False), reason=reason) # updates the user's permissions such that they can't view the channel.
		embed = discord.Embed(description=f'User has been banned from this channel for {duration[1]} seconds ({duration[0]}).', color=VALID_COLOR)
		embed.set_author(icon_url=member.avatar.url, name=f'User {member} Channel-Banned.')
		embed.set_footer(icon_url=ctx.author.avatar.url, text=f'Channel-Banned by {ctx.author} on {round(time.time())}')
		embed.add_field(name='Unban on:', value=f'<t:{round(time.time() + duration[1])}:R>')

		await ctx.send(embed=embed) # sends a confirmation embed

		await asyncio.sleep(duration[1])
		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=True, view_channel=True)) # updates the user's permissions such that they can view the channel.

	"""
	@channel_ban.error # an error occured in the channel_ban command
	async def channel_ban_error(self, ctx, err):
		if isinstance(err, MissingPermissions): # the error occured due to the user running the command not having the required permissiosn
			embed = discord.Embed(title='Missing Permissions', description='You don\'t have the permissions required to run this command! (ban members)', color=INVALID_COLOR)
			await ctx.send(embed=embed)
		else: # an unkown error occured. If the code has no bugs, the following line should not be executed.
			print(err)
	"""

	@commands.command(aliases=['cub', 'channelunban'])
	@has_permissions(ban_members=True) # the user must be able to ban users to be able to unban users.
	async def channel_unban(self, ctx, member: MemberConverter, channel: discord.TextChannel, *, reason=None):
		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=True, view_channel=True), reason=reason) # updates the user's permissions such that they can view the channel.
		embed = discord.Embed(description='User has been unbanned from this channel.', color=VALID_COLOR)
		embed.set_author(icon_url=member.avatar.url, name=f'User {member} Channel-Unbanned.')
		embed.set_footer(icon_url=ctx.author.avatar.url, text=f'Channel-Unbanned by {ctx.author} on {round(time.time())}')

		await ctx.send(embed=embed) # sends a confirmation embed

	@channel_unban.error # an error occured in the channel_unban command
	async def channel_ban_error(self, ctx, err):
		if isinstance(err, MissingPermissions): # the error occured due to the user running the command not having the required permissiosn
			embed = discord.Embed(title='Missing Permissions', description='You don\'t have the permissions required to run this command! (ban members)', color=INVALID_COLOR)
			await ctx.send(embed=embed)
		else: # an unkown error occured. If the code has no bugs, the following line should not be executed.
			print(err)

	@commands.command()
	async def modlogs(self, ctx, target: MemberConverter, *, filters=''):
		filters = [filter[1:] for filter in filters.split() if filter.startswith('-')]
		show_mod = False if 'ms' in filters else ctx.author.guild_permissions.manage_messages

		base_user_data = fud(target.id)
		user_data = base_user_data['violations']

		warn_description = [f'**Case: {i}**\nReason: {warn.reason}\nIssued on: <t:{warn.issued_on}:d> (<t:{warn.issued_on}:F>)\nLink: [Jump]({warn.link})' + (f'\nResponsible Moderator: {warn.responsible_mod} ({await self.client.fetch_user(warn.responsible_mod)})' if show_mod else '') for i, warn in enumerate(user_data['warns'], 1)]
		ban_description = [f'**Case: {i}**\nReason: {ban.reason}\nIssued on: <t:{ban.issued_on}:d> (<t:{ban.issued_on}:F>)\nLink: [Jump]({ban.link})' + (f'\nResponsible Moderator: {ban.responsible_mod} ({await self.client.fetch_user(ban.responsible_mod)})' if show_mod else '') for i, ban in enumerate(user_data['bans'], 1)]
		kick_description = [f'**Case: {i}**\nReason: {kick.reason}\nIssued on: <t:{kick.issued_on}:d> (<t:{kick.issued_on}:F>)\nLink: [Jump]({kick.link})' + (f'\nResponsible Moderator: {kick.responsible_mod} ({await self.client.fetch_user(kick.responsible_mod)})' if show_mod else '') for i, kick in enumerate(user_data['kicks'], 1)]
		cban_description = [f'**Case: {i}**\nReason: {cban.reason}\nIssued on: <t:{cban.issued_on}:d> (<t:{cban.issued_on}:F>)\nLink: [Jump]({cban.link})' + (f'\nResponsible Moderator: {cban.responsible_mod} ({await self.client.fetch_user(cban.responsible_mod)})' if show_mod else '') for i, cban in enumerate(user_data['cbans'], 1)]
		mute_description = [f'**Case: {i}**\nReason: {mute.reason}\nIssued on: <t:{mute.issued_on}:d> (<t:{mute.issued_on}:F>)\nLink: [Jump]({mute.link})' + (f'\nResponsible Moderator: {mute.responsible_mod} ({await self.client.fetch_user(mute.responsible_mod)})' if show_mod else '') for i, mute in enumerate(user_data['mutes'], 1)]


		embed = discord.Embed(description='Moderation History', color=VALID_COLOR)
		if 'w' in filters:
			embed.add_field(name='Warns', value='\n\n'.join(warn_description) or 'No data.', inline=False)
		if 'b' in filters:
			embed.add_field(name='Bans', value='\n\n'.join(ban_description) or 'No data.', inline=False)
		if 'k' in filters:
			embed.add_field(name='Kicks', value='\n\n'.join(kick_description) or 'No data.', inline=False)
		if 'cb' in filters:
			embed.add_field(name='Channel bans', value='\n\n'.join(cban_description) or 'No data.', inline=False)
		if 'm' in filters:
			embed.add_field(name='Mutes', value='\n\n'.join(mute_description) or 'No data.', inline=False)

		if filters in [['ms'], []]:
			embed.add_field(name='Warns', value='\n\n'.join(warn_description) or 'No data.', inline=False)
			embed.add_field(name='Bans', value='\n\n'.join(ban_description) or 'No data.', inline=False)
			embed.add_field(name='Kicks', value='\n\n'.join(kick_description) or 'No data.', inline=False)
			embed.add_field(name='Channel bans', value='\n\n'.join(cban_description) or 'No data.', inline=False)
			embed.add_field(name='Mutes', value='\n\n'.join(mute_description) or 'No data.', inline=False)

		if show_mod:
			embed.add_field(name='Notes', value=base_user_data['note'])

		embed.set_author(icon_url=target.avatar.url, name=str(target))

		try:
			await ctx.send(embed=embed)
		except HTTPException:
			await ctx.send('Too much data to send.')

	@commands.command()
	@has_permissions(ban_members=True)
	async def ban(self, ctx, target: MemberConverter, *, rest=None):
		if rest:
			items = rest.split(' ')
			if is_convertible(items[0]):
				duration = is_convertible(items[0])
			if len(items) >= 1:
				reason = ' '.join(items[1:])
		else:
			duration = 'Indefinitely'
			reason = 'Reason not provided'

		user_data = fud(target.id)
		user_data['violations']['bans'].append(Punishment(ctx, reason, target, ctx.message.jump_url, duration))
		dud(target.id, user_data)
		uid = target.id

		await target.send('Here\'s your appeal link: https://discord.gg/Hp5jwY9Vxd')
		await ctx.guild.ban(target, reason=reason)
		embed = discord.Embed(title='User has been banned.', description=f'User {target.id} has been banned ({f"Until <t:{round(time.time()) + duration}:F> (<t:{round(time.time() + duration)}:R>)"})', color=VALID_COLOR)
		await ctx.send(embed=embed)

		if isinstance(duration, int):
			await asyncio.sleep(duration)
			await ctx.guild.unban(await self.client.fetch_user(uid))

	@commands.command()
	@has_permissions(ban_members=True)
	async def unban(self, ctx, target_id: int):
		bans = [u.user.id async for u in ctx.guild.bans()]
		if target_id in bans:
			user = await self.client.fetch_user(target_id)
			await ctx.guild.unban(user)
			embed = discord.Embed(title='User has been unbanned.', description=f'User {user.mention} has been unbanned.', color=VALID_COLOR)
		else:
			embed = discord.Embed(title='User isn\'t banned.', description='The given user id is invalid (has not been banned)', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@ban.error
	async def ban_error(self, ctx, err):
		if isinstance(err, MissingPermissions):
			await ctx.send('You don\'t have the required priviliges to perform this action.')
		else:
			print(err)


	@unban.error
	async def unban_error(self, ctx, err):
		if isinstance(err, MissingPermissions):
			await ctx.send('You don\'t have the required priviliges to perform this action.')
		else:
			print(err)

	@commands.command()
	@has_permissions(manage_messages=True)
	async def note(self, ctx, user: MemberConverter, *, _note):
		data = fud(user.id)
		data['note'] = _note
		dud(user.id, data)

		embed = discord.Embed(title='Note successfully changed.', description=f'The note for user {user.mention} has been changed {_note!r}', color=VALID_COLOR)
		await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

	@commands.command()
	@has_permissions(moderate_members=True)
	async def mute(self, ctx, user: MemberConverter, duration: Duration, *, reason='Reason not provided'):
		data = fud(user.id)
		data['violations']['mutes'].append(Punishment(ctx, reason, user, ctx.message.jump_url, duration[1]))
		dud(user.id, data)

		await user.timeout_for(datetime.timedelta(seconds=duration[1]))
		embed = discord.Embed(title='User has been timed out.', description=f'User {user.mention} has been timed out by {ctx.author.mention}.', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@mute.error
	async def mute_error(self, ctx, err):
		if isinstance(err, MissingPermissions):
			await ctx.send('You don\'t have the required priviliges to perform this action.')
		else:
			print(err)

	@commands.group(invoke_without_command=True)
	async def faq(self, ctx, *, message):
		with open(FAQ, 'r') as f:
			text = json.load(f)

		if message in text:
			embed = discord.Embed(title='FAQ command invoked.', color=VALID_COLOR)
			embed.add_field(name='Question', value=message.capitalize())
			embed.add_field(name='Answer', value=text[message].capitalize())
			await ctx.send(embed=embed)
		else:
			embed = discord.Embed(title='Tag doesn\'t exist', description='That tag doesn\'t exist.', color=INVALID_COLOR)
			await ctx.send(embed=embed)

	@faq.command()
	@has_permissions(administrator=True)
	async def add(self, ctx, *, name):
		embed = discord.Embed(title='FAQ Tag creation', description=f'What should I reply with when a user uses `>faq {name}`', color=VALID_COLOR)
		await ctx.send(embed=embed)
		try:
			message = await self.client.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.message.channel, timeout=30)
		except asyncio.TimeoutError:
			abort_embed = discord.Embed(title='Timed out.', description='You didn\'t respond in time. Tag creation has been aborted.', color=INVALID_COLOR)
			await ctx.send(embed=abort_embed)
			return
		with open(FAQ, 'r') as f:
			text = json.load(f)

		text[name] = message.content
		with open(FAQ, 'w') as f:
			json.dump(text, f, indent=4)

		embed = discord.Embed(title='Tag added', description=f'Reply for tag {name!r} has been added.', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(administrator=True)
	async def dm(self, ctx, target: MemberConverter, *, message):
		embed = discord.Embed(title='You\'ve got mail!', description=f'{ctx.author} says: {message}', color=VALID_COLOR)
		embed.set_thumbnail(url=ctx.author.avatar.url)
		await target.send(embed=embed)

		modlog_embed = discord.Embed(title='DM Command Issued', color=VALID_COLOR)
		modlog_embed.add_field(name='Issued By', value=f'{ctx.author} {ctx.author.mention}')
		modlog_embed.add_field(name='Sent to', value=f'{target} {target.mention}')
		modlog_embed.add_field(name='Message', value=message, inline=False)
		await (await self.client.fetch_channel(MODLOGS)).send(embed=modlog_embed)

	@commands.command(aliases=['avatar'])
	async def av(self, ctx, target: MemberConverter = None):
		target = target or ctx.author
		embed = discord.Embed(title=f'{target}\'s avatar.', color=VALID_COLOR)
		embed.set_image(url=target.avatar.url)
		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def lock(self, ctx):
		channel = ctx.message.channel
		role = ctx.guild.get_role(LOCK_BYPASS)
		await channel.set_permissions(ctx.guild.default_role, send_messages=False)
		await channel.set_permissions(role, send_messages=True)
		embed = discord.Embed(title=':lock: Channel Locked.', description='This channel has been locked by the staff team.\n**__YOU ARE NOT MUTED__**', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def unlock(self, ctx):
		channel = ctx.message.channel
		await channel.set_permissions(ctx.guild.default_role, send_messages=True)
		embed = discord.Embed(title=':unlock: Channel Unlocked.', description='This channel has been unlocked by the staff team.', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command()
	async def uptime(self, ctx):
		embed = discord.Embed(title='Uptime', description=f'I have been online since: <t:{round(self.start_time)}:R>', color=VALID_COLOR)
		await ctx.send(embed=embed)

	@commands.command()
	async def ping(self, ctx):
		embed = discord.Embed(title='Ping', description=f'My ping is: {round(self.client.latency * 1000)}ms', color=VALID_COLOR)
		await ctx.send(embed=embed)



def setup(client):
	client.add_cog(CommandSet1(client))
