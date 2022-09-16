import config
import discord
import os
import json
import time
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='>', intents=intents)

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

def fetch_user_data(user_id: int): # gets the users data from the database
	with open(config.DATABASE, 'r') as f:
		text = json.load(f)
	if text.get(str(user_id)) is None: # if the user doesn't have any past data.
		text[str(user_id)] = {
			'violations': {
				'bans': [],
				'kicks': [],
				'mutes': [],
				'cbans': [],
				'warns': []
			},
			'note': 'Nothing special.'
		}
		with open(config.DATABASE, 'w') as f:
			json.dump(text, f, indent=4)
	data = text[str(user_id)]
	data['violations']['bans'][:] = [Punishment.python(_data) for _data in data['violations']['bans']]
	data['violations']['kicks'][:] = [Punishment.python(_data) for _data in data['violations']['kicks']]
	data['violations']['mutes'][:] = [Punishment.python(_data) for _data in data['violations']['mutes']]
	data['violations']['cbans'][:] = [Punishment.python(_data) for _data in data['violations']['cbans']]
	data['violations']['warns'][:] = [Punishment.python(_data) for _data in data['violations']['warns']]

	return data

def dump_user_data(user_id: int, data):
	with open(config.DATABASE, 'r') as f:
		text = json.load(f)
	for subclass in data['violations']:
		data['violations'][subclass] = list(map(lambda i: i.json(), data['violations'][subclass]))
	text[str(user_id)] = data

	with open(config.DATABASE, 'w') as f:
		json.dump(text, f, indent=4)

class PunishmentMaster:
	def __init__(self, ctx=0, reason=0, user=0, link=0, duration=0):
		self.issued_on = round(time.time())
		self.responsible_mod = ctx.author.id if ctx != 0 else ctx
		self.reason = reason
		self.inflicted_on = user.id if user != 0 else user
		self.link = link
		with open(config.DATABASE, 'r') as f:
			text = json.load(f)

		self.case_number = text['case_count'] + 1
		if duration:
			self.duration = duration

	def json(self):
		return vars(self)

class Punishment(PunishmentMaster):
	def __init__(self, ctx, reason, user, link, duration=None):
		super().__init__(ctx, reason, user, link, duration)

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
		if data.get('duration') is not None:
			base.duration = data['duration']
		return base

@bot.event
async def on_ready():
	print(f'{bot.user} is up and ready to go!')

load_cogs()
bot.run(config.TOKEN)