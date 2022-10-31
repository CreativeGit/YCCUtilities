# How-To 
Before adding the bot, do this:
1. Create the following files in the same directory as the main.py script:
  database.json
  faq.json
  persist.json
  kills.json
  trivia.json
  qna.json (uploaded)
  
  Please make sure that to write {} in all the above files except qna.json

2. Change the following channel/role ids in the config.yaml file:
  modlogs_channel: channel id
  lock_bypass: role id
  suggestions: channel id
  suggestion_bl: role id
  summon_channel: channel id
  trivia_channel: channel id
  color_role: role id
 
3. After startup run the command '?uc commands_5' to remove the buggy extension.

## Creative's Personal Guide
- make changes locally (not on VPS), commit and push changes
- open terminal → `ssh ubuntu@149.56.132.223`
- `cd YCCUtilities/`
- git pull
- python3 main.py
