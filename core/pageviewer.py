from discord import (
    Interaction,
    ui,
    Button,
    ButtonStyle,
    Message,
    Embed)
from math import floor


class PageButtons(ui.View):
    def __init__(self, embed_pages: dict, interaction: Interaction = None, message: Message = None,
                 author_id: int = None):
        super().__init__(timeout=90)
        self.embed_pages = embed_pages
        self.current_page = 1

        self.interaction = interaction

        self.message = message
        self.author_id = author_id

        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = False
        self.previous_page.disabled = False
        self.next_page.disabled = False
        self.last_page.disabled = False
        if self.current_page == 1:
            self.first_page.disabled = True
            self.previous_page.disabled = True
        if self.current_page == len(self.embed_pages):
            self.next_page.disabled = True
            self.last_page.disabled = True

    async def update_embed(self):
        if self.message:
            await self.message.edit(embed=self.embed_pages[self.current_page], view=self)
        elif self.interaction:
            await self.interaction.edit_original_response(embed=self.embed_pages[self.current_page], view=self)

    @ui.button(label='<<', style=ButtonStyle.grey)
    async def first_page(self, interaction: Interaction, button: Button):
        self.current_page = 1
        self.update_buttons()

        await self.update_embed()
        await interaction.response.defer()

    @ui.button(label='Previous Page', emoji='⬅', style=ButtonStyle.grey)
    async def previous_page(self, interaction: Interaction, button: Button):
        self.current_page -= 1
        self.update_buttons()

        await self.update_embed()
        await interaction.response.defer()

    @ui.button(label='Next Page', emoji='➡', style=ButtonStyle.grey)
    async def next_page(self, interaction: Interaction, button: Button):
        self.current_page += 1
        self.update_buttons()

        await self.update_embed()
        await interaction.response.defer()

    @ui.button(label='>>', style=ButtonStyle.grey)
    async def last_page(self, interaction: Interaction, button: Button):
        self.current_page = len(self.embed_pages)
        self.update_buttons()

        await self.update_embed()
        await interaction.response.defer()

    @ui.button(label='Stop', style=ButtonStyle.red)
    async def _stop(self, interaction: Interaction, button: Button):
        self.stop()
        await interaction.response.defer()
        await interaction.message.delete()

    async def interaction_check(self, interaction: Interaction):
        if self.author_id:
            return self.author_id == interaction.user.id
        elif self.interaction:
            return self.interaction.user.id == interaction.user.id

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)
        elif self.interaction:
            await self.interaction.edit_original_response(view=None)


class BulkDeletionViewer(ui.View):
    def __init__(self, message: Message, payload: list[Message]):
        super().__init__(timeout=604800)
        self.message = message
        self.payload = payload

    @ui.button(label='View Deleted Messages', style=ButtonStyle.grey)
    async def view_payload(self, interaction: Interaction, button: Button):
        page_count = 1
        embed_pages_dict = {1: Embed(colour=0x337fd5, title='Deleted Messages (Page 1/<page-count>)')}

        field_count = 0
        for message in self.payload:
            if len(embed_pages_dict[page_count]) < 5000 and field_count < 7:
                field_count += 1
            else:
                page_count += 1
                field_count = 1

                embed_pages_dict.update({page_count: Embed(
                    colour=0x337fd5, title=f'Deleted Messages (Page {page_count}/<page-count>)')})

            embed_pages_dict[page_count].add_field(
                name=f'Message {self.payload.index(message) + 1}',
                value=f'**Sent by {message.author.mention} at <t:{floor(message.created_at.timestamp())}:F>**\n'
                      f'{message.content if message.content else "`None`"}', inline=False)

        for i in range(1, page_count + 1):
            new_title = embed_pages_dict[i].title.replace('<page-count>', str(page_count))
            embed_pages_dict[i].title = new_title

        await interaction.response.send_message(embed=embed_pages_dict[1],
                                                view=PageButtons(embed_pages_dict, interaction=interaction),
                                                ephemeral=True)

    async def on_timeout(self):
        await self.message.edit(view=None)
