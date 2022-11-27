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

# How to Host/Make Changes on the Public Bot (by Creative)
- make changes locally (not on VPS), commit and push changes
- open terminal and type ```ssh ubuntu@149.56.132.223```
- Change directory into the folder where the bot is ```cd YCCUtilities/```
- Enter the command ```pm2 stop YCCUtilities```
- Pull your changes with ```git pull```
- Run the command ```pm2 start YCCUtilities```
- To view any logs, run ```pm2 logs YCCUtilities```
- You can now close the terminal if you wish, and the bot will still be on. Please make changes locally, test them out, and then pull.
