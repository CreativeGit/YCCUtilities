import config
import discord
import os
import json
import time
from discord.ext import commands
from discord.ui import View, Button

help_items = {
	1: ['this is not a command': 'this is not a description', 'this is a test': 'this is a test too'],
	2: ['this is not a command 2': 'this is not a description 2', 'this is a test 2': 'this is a test too 2']
}

class HelpView(View):
	@discord.ui.button(label='Previous', emoji='⬅️', style=discord.ButtonStyle.blurple)
	async def previous(self, button, interaction):
		return 

class HelpEmbed(discord.Embed):
	def __init__(self, page: int):
		title = f'Help - Page number {page}'
		super().__init__(title=title)
		for command in help_items[page]:
			


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or('>'), intents=intents)
bot.remove_command('help')

@bot.group(invoke_without_command=True)
async def help(ctx):


	await ctx.send()

def is_convertible(arg):
	return int(arg[:-1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[arg[-1]] if arg[-1] in 'smhd' else False

class Duration(commands.Converter):
	async def convert(self, ctx, arg):
		time_converter = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
		return (arg, int(arg[:-1]) * time_converter[arg[-1]]) # returns the exact text passed (eg: 1m, 2h) and that time in seconds

def load_cogs():
	for file in os.listdir('cogs'): # runs through every file in the cogs directory
		if file.endswith('.py'):
			bot.load_extension(f'cogs.{file[:-3]}') # loads every python file
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
	if text['users'].get(str(user_id)) is None: # if the user doesn't have any past data.
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
	if text['users'].get(str(user_id)) is None: # if the user doesn't have any past data.
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
	def empty(self):
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

@bot.event
async def on_ready():
	print(f'{bot.user} is up and ready to go!')


load_cogs()
bot.run(config.TOKEN)