import logging

import discord
from discord.ext import commands

from config import settings
from database import Database
from moderation.engine import ModerationEngine
from moderation.scoring import build_result
from views import AdminCallView, ModerationReviewView

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("moderator")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = Database(settings.database_path)
engine = ModerationEngine(settings.openai_api_key, settings.moderation_model)


def is_moderator(member: discord.Member) -> bool:
    return member.guild_permissions.manage_messages or member.guild_permissions.moderate_members or member.guild_permissions.administrator


async def send_alert(message: discord.Message, result) -> None:
    if not settings.alert_channel_id:
        log.warning("MOD_ALERT_CHANNEL_ID is not configured")
        return
    channel = bot.get_channel(settings.alert_channel_id)
    if not isinstance(channel, discord.TextChannel):
        log.warning("Alert channel %s was not found", settings.alert_channel_id)
        return

    embed = discord.Embed(title="AI moderation alert", color=discord.Color.red())
    embed.add_field(name="Risk", value=f"{result.score:.2f}/10", inline=True)
    embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Categories", value=result.category_summary or "none", inline=False)
    embed.add_field(name="Message", value=discord.utils.escape_markdown(message.content[:900]) or "[no text]", inline=False)
    embed.add_field(name="Jump", value=f"[Open message]({message.jump_url})", inline=False)
    embed.set_footer(text="AI result is advisory; moderator makes the final decision.")

    await channel.send(embed=embed, view=ModerationReviewView(message, result, db, settings.timeout_minutes))


async def warn_user(message: discord.Message, result) -> None:
    text = (
        "Ваше сообщение было отмечено системой автоматической модерации.\n\n"
        f"Возможный контекст: {result.category_summary or 'неопределённое нарушение правил'}\n"
        f"Оценка риска: {result.score:.2f}/10.\n\n"
        "Сообщение передано модераторам на проверку. При необходимости модератор может временно ограничить ваш доступ до выяснения обстоятельств."
    )
    try:
        await message.author.send(text)
    except discord.Forbidden:
        try:
            await message.reply(text, mention_author=False, delete_after=20)
        except discord.HTTPException:
            pass


@bot.event
async def on_ready() -> None:
    await bot.tree.sync()
    log.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "?")
    log.info("Mode: %s", "TEST" if settings.test_mode else "LIVE")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or not message.guild:
        return
    if settings.ignored_channel_ids and message.channel.id in settings.ignored_channel_ids:
        return
    if settings.ignored_role_ids and isinstance(message.author, discord.Member) and any(r.id in settings.ignored_role_ids for r in message.author.roles):
        return

    try:
        moderation = await engine.check_message(message)
        result = build_result(moderation)
        await db.log_result(message, result)

        if settings.test_mode:
            emoji = result.test_emoji
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass
        elif result.score >= settings.threshold:
            await send_alert(message, result)
            await warn_user(message, result)

        if settings.log_channel_id:
            channel = bot.get_channel(settings.log_channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"`{result.score:.2f}/10` | {message.author.mention} | {message.channel.mention} | {result.category_summary or 'none'} | [message]({message.jump_url})")
    except Exception:
        log.exception("Moderation failed for message %s", message.id)

    await bot.process_commands(message)


@bot.tree.command(name="testmode", description="Включить или выключить тестовый режим модерации")
async def testmode(interaction: discord.Interaction, enabled: bool):
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not is_moderator(interaction.user):
        await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
        return
    settings.test_mode = enabled
    await interaction.response.send_message(f"Тестовый режим: {'ON' if enabled else 'OFF'}", ephemeral=True)


@bot.tree.command(name="modstatus", description="Показать состояние AI-модерации")
async def modstatus(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not is_moderator(interaction.user):
        await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Режим: {'TEST' if settings.test_mode else 'LIVE'}\nПорог: {settings.threshold:.2f}/10\nМодель: `{settings.moderation_model}`",
        ephemeral=True,
    )


@bot.tree.command(name="admin", description="Вызвать администратора")
async def admin(interaction: discord.Interaction, reason: str):
    if not interaction.guild:
        await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
        return
    if not settings.admin_channel_id:
        await interaction.response.send_message("Канал администрации не настроен.", ephemeral=True)
        return
    channel = bot.get_channel(settings.admin_channel_id)
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Канал администрации не найден.", ephemeral=True)
        return
    embed = discord.Embed(title="Запрос администрации", description=reason[:1800], color=discord.Color.orange())
    embed.add_field(name="Пользователь", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
    embed.add_field(name="Канал", value=interaction.channel.mention if interaction.channel else "unknown")
    embed.set_footer(text="Создан через /admin")
    await channel.send(embed=embed, view=AdminCallView(interaction.user.id))
    await interaction.response.send_message("Запрос отправлен администрации.", ephemeral=True)


bot.run(settings.discord_token)
