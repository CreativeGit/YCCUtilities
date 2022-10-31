import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from discord.errors import HTTPException
from discord.ext.commands import MemberConverter
from config import VALID_COLOR, INVALID_COLOR, FAQ, MODLOGS, LOCK_BYPASS, DATABASE
from main import Duration, Punishment, is_convertible
from main import punish, fetch_user_data as fud, set_note
from main import FlagReason
import time
import asyncio
import datetime
import json
import typing

class CommandSet1(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		self.start_time = time.time()
		self.modlog_channel = await self.client.fetch_channel(MODLOGS)

	@commands.command(aliases=['cb', 'channelban'])
	@has_permissions(ban_members=True) # the user must have ban member permissions to run this command
	async def channel_ban(self, ctx, member: MemberConverter, channel: discord.TextChannel, duration: typing.Optional[Duration], *, reason='Reason not provided'):
		if member.guild_permissions.manage_messages:
			embed = discord.Embed(title='Invalid!', description='You can\'t channel-ban a fellow mod!', color=INVALID_COLOR)
			await ctx.send(embed=embed)
			return

		log_data = Punishment(ctx, reason, member, ctx.message.jump_url, 'cban', duration)
		case = punish(member.id, log_data)

		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=False, view_channel=False), reason=reason) # updates the user's permissions such that they can't view the channel.
		embed = discord.Embed(description=f'User has been banned from this channel for {duration[1]} seconds ({duration[0]}).', color=VALID_COLOR)
		embed.set_author(icon_url=member.avatar.url, name=f'User {member} Channel-Banned.')
		embed.set_footer(icon_url=ctx.author.avatar.url, text=f'Channel-Banned by {ctx.author} on {round(time.time())}')
		embed.add_field(name='Unban on:', value=f'<t:{round(time.time() + duration[1])}:R>')

		await ctx.send(embed=embed) # sends a confirmation embed

		modlog_embed = discord.Embed(title='Channel Ban Command Issued', description=f'Moderator {ctx.author} channel-banned {member}.', color=VALID_COLOR)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Duration', value=duration[0], inline=False)
		modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)
		modlog_embed.add_field(name='Channel Banned from', value=channel.mention, inline=False)
		modlog_embed.add_field(name='Case number', value=case)

		await self.modlog_channel.send(embed=modlog_embed)

		await asyncio.sleep(duration[1])
		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=True, view_channel=True)) # updates the user's permissions such that they can view the channel.


	@channel_ban.error # an error occured in the channel_ban command
	async def channel_ban_error(self, ctx, err):
		if isinstance(err, MissingPermissions): # the error occured due to the user running the command not having the required permissiosn
			embed = discord.Embed(title='Missing Permissions', description='You don\'t have the permissions required to run this command! (ban members)', color=INVALID_COLOR)
			await ctx.send(embed=embed)
		else: # an unkown error occured. If the code has no bugs, the following line should not be executed.
			print(err)

	@commands.command(aliases=['cub', 'channelunban'])
	@has_permissions(ban_members=True) # the user must be able to ban users to be able to unban users.
	async def channel_unban(self, ctx, member: MemberConverter, channel: discord.TextChannel, *, reason='Reason not provided'):
		await channel.set_permissions(member, overwrite=discord.PermissionOverwrite(send_messages=True, view_channel=True), reason=reason) # updates the user's permissions such that they can view the channel.
		embed = discord.Embed(description='User has been unbanned from this channel.', color=VALID_COLOR)
		embed.set_author(icon_url=member.avatar.url, name=f'User {member} Channel-Unbanned.')
		embed.set_footer(icon_url=ctx.author.avatar.url, text=f'Channel-Unbanned by {ctx.author} on {round(time.time())}')

		modlog_embed = discord.Embed(title='Channel Unban Command Issued', description=f'Moderator {ctx.author} channel-unbanned {member}.', color=VALID_COLOR)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)
		modlog_embed.add_field(name='Channel Unbanned from', value=channel.mention, inline=False)

		await self.modlog_channel.send(embed=modlog_embed)

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
		if not ctx.author.guild_permissions.manage_messages and target != ctx.author:
			embed = discord.Embed(title='Invalid', description='You can\'t access this users modlogs! You need to be a mod to perform this action. You can only check your own modlogs.', color=INVALID_COLOR)
			await ctx.send(embed=embed)
			return

		filters = [filter[1:] for filter in filters.split() if filter.startswith('-')]
		show_mod = False if 'ms' in filters else ctx.author.guild_permissions.manage_messages

		base_user_data = fud(target.id)

		with open(DATABASE, 'r') as f:
			text = json.load(f)
		cases = text['cases']
		user_data = [Punishment.python(data) for data in cases if data['inflicted_on'] == target.id]

		user_cases = [(case.infraction, f'**Case: {case.case_number}**\nReason: {case.reason}\nIssued on: <t:{case.issued_on}:d> (<t:{case.issued_on}:F>)\nLink: [Jump]({case.link})' + (f'\nResponsible Moderator: {case.responsible_mod} ({await self.client.fetch_user(case.responsible_mod)})' if show_mod else '')) for case in user_data]

		embed = discord.Embed(description='Moderation History', color=VALID_COLOR)
		if 'w' in filters:
			warns = [case[1] for case in user_cases if case[0] == 'warn']
			embed.add_field(name='Warns', value='\n\n'.join(warns) or 'No data.', inline=False)
		if 'b' in filters:
			bans = [case[1] for case in user_cases if case[0] == 'ban']
			embed.add_field(name='Bans', value='\n\n'.join(bans) or 'No data.', inline=False)
		if 'k' in filters:
			kicks = [case[1] for case in user_cases if case[0] == 'kick']
			embed.add_field(name='Kicks', value='\n\n'.join(kicks) or 'No data.', inline=False)
		if 'cb' in filters:
			cbans = [case[1] for case in user_cases if case[0] == 'cban']
			embed.add_field(name='Channel bans', value='\n\n'.join(cbans) or 'No data.', inline=False)
		if 'm' in filters:
			mutes = [case[1] for case in user_cases if case[0] == 'mute']
			embed.add_field(name='Mutes', value='\n\n'.join(mutes) or 'No data.', inline=False)
		if 'sb' in filters:
			softbans = [case[1] for case in user_cases if case[0] == 'softban']
			embed.add_field(name='Softbans', value='\n\n'.join(softbans) or 'No data.', inline=False)

		if filters in [['ms'], []]:
			warns = [case[1] for case in user_cases if case[0] == 'warn']
			bans = [case[1] for case in user_cases if case[0] == 'ban']
			kicks = [case[1] for case in user_cases if case[0] == 'kick']
			cbans = [case[1] for case in user_cases if case[0] == 'cban']
			mutes = [case[1] for case in user_cases if case[0] == 'mute']
			softbans = [case[1] for case in user_cases if case[0] == 'mute']
			embed.add_field(name='Warns', value='\n\n'.join(warns) or 'No data.', inline=False)
			embed.add_field(name='Bans', value='\n\n'.join(bans) or 'No data.', inline=False)
			embed.add_field(name='Kicks', value='\n\n'.join(kicks) or 'No data.', inline=False)
			embed.add_field(name='Channel bans', value='\n\n'.join(cbans) or 'No data.', inline=False)
			embed.add_field(name='Mutes', value='\n\n'.join(mutes) or 'No data.', inline=False)
			embed.add_field(name='Softbans', value='\n\n'.join(softbans) or 'No data.', inline=False)

		if show_mod:
			embed.add_field(name='Notes', value=base_user_data['note'])

		embed.set_author(icon_url=target.avatar.url, name=str(target))

		try:
			await ctx.send(embed=embed)
		except HTTPException:
			await ctx.send('Too much data to send.')

	@commands.command()
	@has_permissions(ban_members=True)
	async def ban(self, ctx, target: MemberConverter, duration: typing.Optional[Duration] = 'Indefinitely', *, flag_reason: FlagReason):
		flags, reason = flag_reason
		print(flags, reason)

		case = punish(target.id, Punishment(ctx, reason, target, ctx.message.jump_url, 'ban', duration))
		uid = target.id

		modlog_embed = discord.Embed(title='Ban Command Issued', description=f'Moderator {ctx.author} banned {target}.', color=VALID_COLOR)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Duration', value=duration, inline=False)
		modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)
		modlog_embed.add_field(name='Case number', value=case)

		message = await self.modlog_channel.send(embed=modlog_embed)

		if 's' not in flags:
			embed = discord.Embed(title='You have been banned!', description=f'You have been banned from {ctx.guild.name}!', color=VALID_COLOR)
			embed.add_field(name='Reason', value=reason)
			await target.send(embed=embed)
		await target.send('Here\'s your appeal link: https://discord.gg/Hp5jwY9Vxd')
		await ctx.guild.ban(target, reason=reason)
		embed = discord.Embed(title='User has been banned.', description=f'User {uid} has been banned ' + (f'({f"Until <t:{round(time.time()) + duration}:F> (<t:{round(time.time() + duration)}:R>)"})' if isinstance(duration, (int, float)) else 'Indefinitely') , color=VALID_COLOR)
		await ctx.send(embed=embed)

		if isinstance(duration, int):
			await asyncio.sleep(duration)
			await ctx.guild.unban(await self.client.fetch_user(uid))

			modlog_embed = discord.Embed(title='User Unbanned', description=f'User {uid} has been unbanned.', color=VALID_COLOR)
			modlog_embed.add_field(name='Reason', value='Automatic unban due to ban duration expiring.', inline=False)
			modlog_embed.add_field(name='Ban Logs', value=f'[Jump]({message.jump_url})', inline=False)

			await self.modlog_channel.send(embed=modlog_embed)			

	@commands.command()
	@has_permissions(ban_members=True)
	async def unban(self, ctx, target_id: int):
		bans = [u.user.id async for u in ctx.guild.bans()]
		if target_id in bans:
			user = await self.client.fetch_user(target_id)
			await ctx.guild.unban(user)
			embed = discord.Embed(title='User has been unbanned.', description=f'User {user.mention} has been unbanned.', color=VALID_COLOR)

			modlog_embed = discord.Embed(title='Unban Command Issued', description=f'Moderator {ctx.author} unbanned {user.mention}.', color=VALID_COLOR)
			modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)

			await self.modlog_channel.send(embed=modlog_embed)			
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
		set_note(user.id, _note)

		modlog_embed = discord.Embed(title='Note Command Issued', description=f'Moderator {ctx.author} changed note of {member}.', color=VALID_COLOR)
		modlog_embed.add_field(name='New Note', value=_note, inline=False)

		await self.modlog_channel.send(embed=modlog_embed)

		embed = discord.Embed(title='Note successfully changed.', description=f'The note for user {user.mention} has been changed {_note!r}', color=VALID_COLOR)
		await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

	@commands.command()
	@has_permissions(moderate_members=True)
	async def mute(self, ctx, user: MemberConverter, duration: typing.Optional[Duration] = 'Indefinitely', *, flg_reasons: FlagReason):
		flags, reason = flg_reasons
		case = punish(user.id, Punishment(ctx, reason, user, ctx.message.jump_url, 'mute', duration[1]))

		modlog_embed = discord.Embed(title='Mute Command Issued', description=f'Moderator {ctx.author} muted {member}.', color=VALID_COLOR)
		modlog_embed.add_field(name='Reason', value=reason, inline=False)
		modlog_embed.add_field(name='Duration', value=duration[0] if isinstance(duration, tuple) else duration, inline=False)
		modlog_embed.add_field(name='Link', value=f'[Jump]({ctx.message.jump_url})', inline=False)
		modlog_embed.add_field(name='Case number', value=case)

		await self.modlog_channel.send(embed=modlog_embed)

		await user.timeout_for(datetime.timedelta(seconds=duration[1]))
		if 's' not in flags:
			embed = discord.Embed(title='You have been muted!', description=f'You have been muted in {ctx.guild.name}!', color=VALID_COLOR)
			embed.add_field(name='Reason', value=reason)
			await user.send(embed=embed)

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
		modlog_embed.add_field(name='Issued By', value=f'{ctx.author} {ctx.author.mention}', inline=False)
		modlog_embed.add_field(name='Sent to', value=f'{target} {target.mention}', inline=False)
		modlog_embed.add_field(name='Message', value=message, inline=False)
		await self.modlog_channel.send(embed=modlog_embed)

	@commands.command(aliases=['avatar'])
	async def av(self, ctx, target: MemberConverter = None):
		target = target or ctx.author
		embed = discord.Embed(title=f'{target}\'s avatar.', color=VALID_COLOR)
		embed.set_image(url=target.avatar.url)
		await ctx.send(embed=embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def lock(self, ctx, channel: discord.TextChannel = None, *, reason='Reason not provided'):
		channel = channel or ctx.channel
		role = ctx.guild.get_role(LOCK_BYPASS)
		await channel.set_permissions(ctx.guild.default_role, send_messages=False)
		await channel.set_permissions(role, send_messages=True)
		embed = discord.Embed(title=':lock: Channel Locked.', description='This channel has been locked by the staff team.\n**__YOU ARE NOT MUTED__**', color=VALID_COLOR)
		embed.add_field(name='Reason', value=reason)
		await channel.send(embed=embed)

		if channel != ctx.channel:
			secondary = discord.Embed(title='Channel Locked.', description=f'Channel {channel.mention} has been locked.', color=VALID_COLOR)
			await ctx.send(embed=secondary)

		modlog_embed = discord.Embed(title='Channel Lock Command Issued', color=VALID_COLOR)
		modlog_embed.add_field(name='Issued By', value=f'{ctx.author} {ctx.author.mention}', inline=False)
		await self.modlog_channel.send(embed=modlog_embed)

	@commands.command()
	@has_permissions(manage_channels=True)
	async def unlock(self, ctx):
		channel = ctx.message.channel
		await channel.set_permissions(ctx.guild.default_role, send_messages=True)
		embed = discord.Embed(title=':unlock: Channel Unlocked.', description='This channel has been unlocked by the staff team.', color=VALID_COLOR)
		await ctx.send(embed=embed)

		modlog_embed = discord.Embed(title='Channel Unlock Command Issued', color=VALID_COLOR)
		modlog_embed.add_field(name='Issued By', value=f'{ctx.author} {ctx.author.mention}', inline=False)
		await self.modlog_channel.send(embed=modlog_embed)

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
