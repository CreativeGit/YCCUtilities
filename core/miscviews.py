from discord import (
    ui,
    Interaction,
    Button,
    ButtonStyle,
    Forbidden,
    NotFound,
    HTTPException,
    Role,
    Embed)


class RolesButton(ui.Button):
    def __init__(self, bot, role: Role, emoji: str):
        super().__init__(label=role.name, emoji=emoji, style=ButtonStyle.grey, custom_id=f'r{role.id}')
        self.bot = bot
        self.role = role

    async def callback(self, interaction: Interaction):
        try:
            if self.role not in interaction.user.roles:
                await interaction.user.add_roles(self.role)
                await self.bot.send_ephemeral_response(interaction, f'*{self.role.mention} added.*', 0x43b582)
                return
            await interaction.user.remove_roles(self.role)
            await self.bot.send_ephemeral_response(interaction, f'*{self.role.mention} removed.*', 0x43b582)
        except (Forbidden, NotFound, HTTPException):
            await self.bot.send_ephemeral_response(
                interaction, '❌ Something went wrong, please contact a staff member.', 0xf04a47)


class RolesView(ui.View):
    def __init__(self, bot, roles: list[Role]):
        super().__init__(timeout=None)
        emotes_mapping = {'Art/Animation': '🖌️', 'Music': '🎵', 'Gaming': '🎮', 'Technology': '💻',
                          'Finance': '💸', 'Infotainment': '📺', 'Other Niches': '❓'}
        for role in roles:
            if len(self.children) <= 25:
                emoji = emotes_mapping[role.name] if role.name in emotes_mapping else '<:role:1014718526075961374>'
                self.add_item(RolesButton(bot, role, emoji))


class RulesButtons(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ui.Button(
            label='Apply For Staff',
            url=bot.staff_form))

    @ui.button(label='Ban Appeals', emoji='<:icons_banhammer:1016821788270932028>',
               style=ButtonStyle.grey, custom_id='appeal_button')
    async def appeal_button(self, interaction: Interaction, button: Button):
        appeal_embed = Embed(
            colour=0x337fd5,
            title=f'Appeal Ban - {self.bot.guild.name}',
            description=f'**Invite: https://discord.gg/youtubers**\n\n'
                        f'Banned users should have received a DM from {self.bot.user.mention} with the ban reason, as '
                        f'well as a button to appeal. The button will bring up an appeal form once clicked, which can '
                        f'be filled out and submitted for reviewal.\n\nPlease do not misuse this appeal form or you '
                        f'may be permanently blacklisted from appealing and/or banned from the server.')
        await interaction.response.send_message(embed=appeal_embed, ephemeral=True)
