# YCC Utilities
YouTube Creator Café Utilities Discord Bot.

# What is it?
YCC Utilities aims to be an all-in-one moderation/utility application for Discord. Some key features include:
- Robust, persistent punishment commands that cannot be circumvented by means of leaving/re-joining the guild.
- Lock/lockdown, slow-mode, purge and channel-ban commands to easily manage your guild's channels.
- An advanced mod-logs system to keep track of member punishments.
- Create your own custom commands with ease. These can be unique moderation commands or a simple shortcut/response command.
- Further utility features such as suggestions, ban appeals, trivia, role-reactions and more.

You can view the full command documentation for YCC Utilities [here](https://ycc-utilities.gitbook.io/commands-docs/).
# How To Use
- Create a new Discord application [here](https://discord.com/developers/applications). Create a bot user for this application and copy the token. Keep this safe and do not give it to anybody.
- Make sure you have `Python >= 3.10` as well as the listed requirements installed. Many are dependencies of the `discord.py` library.
- Open `example.env` and replace the example values with your own. Keep this file in the same directory as the `main.py` file. For environment variables that take a list of values, separate each value with only a comma.
- Navigate into the YCC Utilities directory in your terminal and start the bot using `python3 main.py`.