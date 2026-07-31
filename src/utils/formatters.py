"""Human-readable text formatting helpers for bot replies."""

from __future__ import annotations

from datetime import datetime

from src.models.force_sub_channel import TELEGRAM_AUTO_VERIFIABLE_PLATFORMS, ForceSubChannel
from src.models.movie import Movie
from src.models.user import User


def format_movie_caption(movie: Movie) -> str:
    """Render a rich caption for a movie delivered to an end-user."""
    lines = [f"🎬 <b>{movie.title}</b>"]
    if movie.year:
        lines.append(f"📅 Yil: {movie.year}")
    if movie.genre:
        lines.append(f"🎭 Janr: {movie.genre}")
    if movie.country:
        lines.append(f"🌍 Davlat: {movie.country}")
    if movie.language:
        lines.append(f"🗣 Til: {movie.language}")
    if movie.quality:
        lines.append(f"🖼 Sifat: {movie.quality}")
    if movie.duration_minutes:
        lines.append(f"⏱ Davomiyligi: {movie.duration_minutes} daqiqa")
    lines.append(f"🔑 Kod: <code>{movie.code}</code>")
    if movie.description:
        lines.append("")
        lines.append(movie.description)
    if movie.caption:
        lines.append("")
        lines.append(movie.caption)
    return "\n".join(lines)


def format_user_profile(user: User) -> str:
    """Render an admin-facing profile summary for a single user."""
    full_name = " ".join(part for part in (user.first_name, user.last_name) if part)
    status = "🚫 Bloklangan" if user.is_banned else ("🔇 Ovozi o'chirilgan" if user.is_muted else "✅ Faol")
    premium = (
        f"⭐️ Premium (tugaydi: {format_datetime(user.premium_expires_at)})"
        if user.is_premium
        else "👤 Oddiy"
    )
    username_line = f"🔗 Username: @{user.username}" if user.username else "🔗 Username: -"
    lines = [
        "<b>👤 Foydalanuvchi profili</b>",
        "",
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>",
        f"👤 Ism: {full_name or '-'}",
        username_line,
        f"🌐 Til: {user.language_code}",
        f"📅 Qo'shilgan: {format_datetime(user.joined_at)}",
        f"🕑 Oxirgi faollik: {format_datetime(user.last_active_at)}",
        f"🎬 Olingan kinolar: {user.movies_received_count}",
        f"🔍 Qidiruvlar: {user.searches_count}",
        f"👥 Taklif qilganlar: {user.invite_count}",
        premium,
        status,
    ]
    return "\n".join(lines)


def format_force_sub_gate_message(channels: list[ForceSubChannel]) -> str:
    """Render the mandatory-subscription gate message shown to a blocked user.

    Lists every outstanding target with its type and, for manually verified
    (non-Telegram) platforms, the admin-provided instructions.
    """
    lines = [
        "🔐 <b>Botdan foydalanish uchun avval quyidagilarga obuna bo'ling:</b>",
        "",
    ]
    for channel in channels:
        marker = "🔒" if channel.is_mandatory else "🔹"
        lines.append(f"{marker} {channel.title}")
        if channel.platform not in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS and channel.instructions:
            lines.append(f"   ℹ️ {channel.instructions}")
    lines.append("")
    lines.append(
        "Obuna/tasdiqdan so'ng pastdagi tugmani bosing. Obuna bo'lmaguningizcha bot "
        "hech qanday funksiyani bajarmaydi."
    )
    return "\n".join(lines)


def format_datetime(value: datetime | None) -> str:
    """Render an optional datetime as ``YYYY-MM-DD HH:MM`` UTC, or a dash."""
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M") + " UTC"


def pluralize_count(count: int, singular: str) -> str:
    """Render a count with its label -- kept simple since Uzbek has no plural suffix rule here."""
    return f"{count} {singular}"
