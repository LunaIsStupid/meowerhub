import discord
from discord.ext import commands


class HelpPaginator(discord.ui.View):
    def __init__(self, pages, author, cog_names):
        super().__init__(timeout=120)
        self.pages = pages
        self.author = author
        self.current = 0
        self.cog_names = cog_names

        options = [
            discord.SelectOption(label=name, value=str(i))
            for i, name in enumerate(cog_names)
        ]
        self.cog_select.options = options

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author

    @discord.ui.select(placeholder="Select a category...")
    async def cog_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        self.current = int(select.values[0])
        await interaction.response.edit_message(
            embed=self.pages[self.current], view=self
        )


class MeowHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        pages = []
        cog_names = []
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if not filtered:
                continue
            name = cog.qualified_name if cog else "No Category"
            value = "\n".join(
                f"**`!{command.name}`** - {command.short_doc or 'No description.'}"
                for command in filtered
            )
            embed = discord.Embed(
                title=f"Help: {name}",
                description=value,
                color=discord.Color.yellow(),
                timestamp=discord.utils.utcnow(),
            )
            if self.context.bot.user:
                embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
            pages.append(embed)
            cog_names.append(name)

        if not pages:
            embed = discord.Embed(
                title="Help",
                description="No commands available.",
                color=discord.Color.yellow(),
                timestamp=discord.utils.utcnow(),
            )
            if self.context.bot.user:
                embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
            await self.get_destination().send(embed=embed)
            return

        for i, embed in enumerate(pages):
            embed.set_footer(text=f"Page {i + 1} of {len(pages)}")

        if len(pages) == 1:
            await self.get_destination().send(embed=pages[0])
            return

        view = HelpPaginator(pages, self.context.author, cog_names)
        await self.get_destination().send(embed=pages[0], view=view)

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        value = "\n".join(
            f"**`!{command.name}`** - {command.short_doc or 'No description.'}"
            for command in filtered
        )
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=value,
            color=discord.Color.yellow(),
            timestamp=discord.utils.utcnow(),
        )
        if self.context.bot.user:
            embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"`!{command.name}`",
            description=command.help or command.short_doc or "No description.",
            color=discord.Color.yellow(),
            timestamp=discord.utils.utcnow(),
        )
        if self.context.bot.user:
            embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error):
        embed = discord.Embed(
            title="Error",
            description=error,
            color=discord.Color.yellow(),
            timestamp=discord.utils.utcnow(),
        )
        if self.context.bot.user:
            embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.get_destination().send(embed=embed)
