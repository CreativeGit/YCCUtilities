import yaml
from yaml.loader import SafeLoader

with open('config_data.yaml', 'r') as f:
    data = yaml.load(f, Loader=SafeLoader)

TOKEN = data['token']
DATABASE = data['database']
KILLS = data['halloween']
TRIVIA = data['trivia']
QNA = data['qna']
VALID_COLOR = data['valid_color']
INVALID_COLOR = data['invalid_color']
FAQ = data['faq']
PERSIST = data['persist']
MODLOGS = data['modlogs_channel']
LOCK_BYPASS = data['lock_bypass']
SUGGESTIONS_CHANNEL = data['suggestions']
SUGGESTIONS_BL = data['suggestion_bl']
NAMES = data['names']
COLOR_ROLE = data['color_role']
SUB_ROLES = data['sub_roles']
SUMMON_CHANNEL = data['summon_channel']
TRIVIA_CHANNEL = data['trivia_channel']
