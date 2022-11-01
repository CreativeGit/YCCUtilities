import config
import discord
import os
import json
import time
from discord.ext import commands
from discord.ui import View, Button

class FlagReason(commands.Converter):
	async def convert(self, ctx, arg):
		split = arg.split()
		flags, reason = [], []
		for index, item in enumerate(split):
			if not item.startswith('-'):
				reason = split[index:]
				return flags, ' '.join(reason)
			flags.append(item[1:])
		return flags, 'Reason not provided'

help_items = {
	1: [
		{
			'name': 'Avatar', 
			'value': 'Gives the specified member\'s avatar.'
		}, 
		{
			'name': 'Ban',
			'value': 'Ban\'s the specified member for the specified duration.'
		},
		{
			'name': 'Channel Ban',
			'value': 'Channel bans the specified member from the specified channel (they are unable to send messages or view the channel).'
		},
		{
			'name': 'Channel Unban',
			'value': 'Channel unbans the specified member from the specified channel (they can send message and view the channel again).'
		},
		{
			'name': 'DM',
			'value': 'DMs the specified member the specified text.'
		},
		{
			'name': 'FAQ',
			'value': 'Provides the answer to the FAQ question. Has 1 subcommand.'
		}
	],
	2: [
		{
			'name': 'Lock',
			'value': 'Locks the specified channel (members can\'t send messages).'
		},
		{
			'name': 'Unlock',
			'value': 'Unlocks the specified channel (members can send messages again).'

		},
		{
			'name': 'Modlogs',
			'value': 'This allows you to view the past moderation logs of a user by running `?modlogs [UserID]`'
		}
	]
}

class HelpView(View):
	def __init__(self):
		self.page = 1
		super().__init__()

	@discord.ui.button(label='Previous', emoji='⬅', style=discord.ButtonStyle.blurple)
	async def previous(self, _, interaction):
		self.page -= 1
		await interaction.response.edit_message(embed=HelpEmbed(self.page), view=self.update_buttons())

	@discord.ui.button(label='Next', emoji='➡', style=discord.ButtonStyle.blurple)
	async def next(self, _, interaction):
		self.page += 1
		await interaction.response.edit_message(embed=HelpEmbed(self.page), view=self.update_buttons())

	def update_buttons(self):
		buttons = self.children
		_prev, _next = buttons

		_prev.disabled = self.page == 1
		_next.disabled = self.page == len(help_items)
		return self

class HelpEmbed(discord.Embed):
	def __init__(self, page: int):
		title = f'Help - Page number {page}'
		super().__init__(title=title, color=config.VALID_COLOR)
		for command in help_items[page]:
			self.add_field(name=command['name'], value='⮩ ' + command['value'], inline=False)


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or('?'), intents=intents)
bot.remove_command('help')

"""
@bot.group(invoke_without_command=True, name='help')
async def help_cmd(ctx):
	await ctx.send(embed=HelpEmbed(1), view=HelpView().update_buttons())
""" # ^^^ Removes the incomplete help method

def is_convertible(arg):
	return int(arg[:-1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'y': 31557600}[arg[-1]] if arg[-1] in 'smhdy' and not arg.startswith('-') else False

class Duration(commands.Converter):
	async def convert(self, ctx, arg):
		if is_convertible(arg):
			time_converter = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
			return arg, int(arg[:-1]) * time_converter[arg[-1]]  # returns the exact text passed (eg: 1m, 2h) and that time in seconds
		return None

def load_cogs():
	for file in os.listdir('cogs'):  # runs through every file in the cogs directory
		if file.endswith('.py'):
			bot.load_extension(f'cogs.{file[:-3]}')  # loads every python file
			print(f'Loaded {file}')

def fetch_user_data(user_id):
	with open(config.DATABASE, 'r') as f:
		text = json.load(f)

	if text['users'].get(str(user_id)) is None:
		text['users'][str(user_id)] = {
			'violations': [],
			'note': 'Nothing special.'
		}

		with open(config.DATABASE, 'w') as f:
			json.dump(text, f, indent=4)

	return text['users'][str(user_id)]

def punish(user_id, punishment):
	with open(config.DATABASE, 'r') as f:
		text = json.load(f)
	if text['users'].get(str(user_id)) is None:  # if the user doesn't have any past data.
		text['users'][str(user_id)] = {
			'violations': [],
			'note': 'Nothing special.'
		}

	text['case_count'] += 1
	case = text['case_count']
	text['cases'].append(punishment.json())
	text['users'][str(user_id)]['violations'].append(case)

	with open(config.DATABASE, 'w') as f:
		json.dump(text, f, indent=4)

	return case

def set_note(user_id, note):
	with open(config.DATABASE, 'r') as f:
		text = json.load(f)
	if text['users'].get(str(user_id)) is None:  # if the user doesn't have any past data.
		text['users'][str(user_id)] = {
			'violations': [],
			'note': 'Nothing special.'
		}

	text['users'][str(user_id)]['note'] = note

	with open(config.DATABASE, 'w') as f:
		json.dump(text, f, indent=4)

class PunishmentMaster:
	def __init__(self, ctx=0, reason=0, user=0, link=0, infraction=0, duration=0):
		self.issued_on = round(time.time())
		self.responsible_mod = ctx.author.id if ctx != 0 else ctx
		self.reason = reason
		self.inflicted_on = user.id if user != 0 else user
		self.link = link
		self.infraction = infraction
		with open(config.DATABASE, 'r') as f:
			text = json.load(f)

		self.case_number = text['case_count']

		if duration:
			self.duration = duration

	def json(self):
		return vars(self)

class Punishment(PunishmentMaster):
	def __init__(self, ctx, reason, user, link, infraction, duration=None):
		super().__init__(ctx, reason, user, link, infraction, duration)

	def json(self):
		return vars(self)

	@classmethod
	def empty(cls):
		return PunishmentMaster()

	@classmethod
	def python(cls, data):
		base = Punishment.empty()
		base.issued_on = data['issued_on']
		base.responsible_mod = data['responsible_mod']
		base.reason = data['reason']
		base.inflicted_on = data['inflicted_on']
		base.link = data['link']
		base.case_number = data['case_number']
		base.infraction = data['infraction']
		if data.get('duration') is not None:
			base.duration = data['duration']
		return base

class PunishmentFromMessage(Punishment):
	def from_message(self, message, reason, inflicted_on, link, infraction):
		self.issued_on = round(time.time())
		self.responsible_mod = message.author.id
		self.reason = reason
		self.inflicted_on = inflicted_on.id
		self.link = link
		self.infraction = infraction
		with open(config.DATABASE, 'r') as f:
			text = json.load(f)

		self.case_number = text['case_count']


@bot.command(name='uc')
@commands.has_permissions(administrator=True)
async def unload_cogs(ctx, *cogs):
	for cog in cogs:
		bot.unload_extension(f'cogs.{cog}')
	await ctx.send("The cogs have been unloaded, and their commands will not be able to be run.")

@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='discord.gg/youtubers'))
	print(f'{bot.user} is up and ready to go! Yay!')


load_cogs()
bot.run(config.TOKEN)
