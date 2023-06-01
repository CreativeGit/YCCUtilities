# YCC Utilities
Moderation/Utility bot for the YouTube Creator Café.

# What is it?
YCC Utilities aims to be an all-in-one application for Discord. Some key features include:
- Robust, persistent moderation commands that cannot be circumvented by means of leaving/re-joining the guild.
- Lock/lockdown, slow-mode, purge and channel-ban commands to easily manage your guild's channels.
- An advanced mod-logs system to keep track of moderations.
- Create your own custom commands with ease. These can be unique moderation commands or a simple shortcut/response command.
- Further utility features such as suggestions, trivia, role-reactions and more.

# How To Use
- Create a new Discord application [here](https://discord.com/developers/applications). Create a bot user for this application and copy the token. Keep this safe and do not give it to anybody.
- Make sure you have `Python >= 3.10` as well as the listed requirements installed. Many are dependencies of the `discord.py` library.
- Open `.env` and replace the example values with your own. Keep this file in the same directory as the `main.py` file. For environment variables that take a list of values, separate each value with only a comma.
- Navigate into the YCC Utilities directory in your terminal and start the bot using `python3 main.py`.