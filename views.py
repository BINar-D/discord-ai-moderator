import discord


class ModerationReviewView(discord.ui.View):
    def __init__(self, message, result, db, timeout_minutes: int):
        super().__init__(timeout=86400)
        self.message = message
        self.result = result
        self.db = db
        self.timeout_minutes = timeout_minutes

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.moderate_members or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Оставить", style=discord.ButtonStyle.secondary)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.db.set_action(self.message.id, "dismissed")
        await interaction.response.send_message("Нарушение не подтверждено.", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.message.delete(reason="AI moderation: moderator decision")
            action = "deleted"
        except discord.HTTPException:
            action = "delete_failed"
        await self.db.set_action(self.message.id, action)
        await interaction.response.send_message(f"Действие: {action}", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Мут", style=discord.ButtonStyle.danger)
    async def timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(self.message.author, discord.Member):
            await interaction.response.send_message("Пользователь больше не является участником сервера.", ephemeral=True)
            return
        try:
            await self.message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=self.timeout_minutes), reason="AI moderation: moderator decision")
            action = f"timeout_{self.timeout_minutes}m"
        except discord.HTTPException as exc:
            action = f"timeout_failed: {exc}"
        await self.db.set_action(self.message.id, action)
        await interaction.response.send_message(f"Действие: {action}", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)


class AdminCallView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=86400)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администратор может закрыть обращение.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.success)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Обращение закрыто.", ephemeral=False)
        self.disable_all_items()
        await interaction.message.edit(view=self)
