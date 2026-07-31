"""Media Queue: an admin drops media into a source group and the bot auto-captures it.

Removes the need to manually copy a ``file_id`` -- the bot receives the
media, remembers its ``file_id``/source location, and simply asks the admin
for a movie code in reply. This is the recommended workflow used by large
movie-delivery bots, per spec.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.plugin import register_admin_plugin
from src.models.movie import MediaType
from src.services.admin_service import AdminService
from src.services.log_service import LogService
from src.services.movie_service import MovieService
from src.states.movie_states import MediaQueueStates
from src.utils.exceptions import CodeReservedError, MovieCodeAlreadyExistsError
from src.utils.formatters import format_movie_caption
from src.utils.validators import normalize_movie_code

router = Router(name="admin.media_queue")

_MEDIA_TYPE_BY_ATTR: list[tuple[str, MediaType]] = [
    ("video", MediaType.VIDEO),
    ("document", MediaType.DOCUMENT),
    ("audio", MediaType.AUDIO),
    ("animation", MediaType.ANIMATION),
    ("photo", MediaType.PHOTO),
]


def _extract_media(message: Message) -> tuple[str, MediaType] | None:
    """Return ``(file_id, media_type)`` for the first supported media on a message."""
    for attr, media_type in _MEDIA_TYPE_BY_ATTR:
        value = getattr(message, attr, None)
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            return value[-1].file_id, media_type
        return value.file_id, media_type
    return None


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.content_type.in_({"video", "document", "audio", "animation", "photo"}),
)
async def capture_media(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    """Auto-capture media an admin drops into a source group and ask for a code."""
    if message.from_user is None or not await admin_service.is_admin(message.from_user.id):
        return
    if await state.get_state() is not None:
        return  # another flow (e.g. bulk upload) already owns this admin's state

    media = _extract_media(message)
    if media is None:
        return
    file_id, media_type = media

    await state.update_data(
        telegram_file_id=file_id,
        media_type=media_type.value,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        caption=message.caption or "",
    )
    await state.set_state(MediaQueueStates.waiting_for_code)
    await message.reply(
        "Media qabul qilindi va indekslandi.\n"
        "Endi shu media uchun kodni yuboring.\n"
        "Ixtiyoriy: 'kod | nom' formatida nom bilan birga yuborishingiz mumkin."
    )


@router.message(MediaQueueStates.waiting_for_code, F.text)
async def receive_code(
    message: Message,
    state: FSMContext,
    movie_service: MovieService,
    log_service: LogService,
) -> None:
    """Persist the queued media under the admin-provided code -- indexed and search-ready."""
    data = await state.get_data()
    await state.clear()
    if not message.text:
        return

    raw = message.text.strip()
    if "|" in raw:
        raw_code, _, raw_title = raw.partition("|")
        code = normalize_movie_code(raw_code)
        title = raw_title.strip() or f"Kino {code}"
    else:
        code = normalize_movie_code(raw)
        title = data.get("caption") or f"Kino {code}"

    try:
        movie = await movie_service.create_movie(
            code=code,
            title=title,
            telegram_file_id=data["telegram_file_id"],
            media_type=MediaType(data["media_type"]),
            source_chat_id=data.get("source_chat_id"),
            source_message_id=data.get("source_message_id"),
            added_by=message.from_user.id if message.from_user else None,
        )
    except (MovieCodeAlreadyExistsError, CodeReservedError) as error:
        await message.answer(str(error))
        return

    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="movie_created",
        entity_type="movie",
        entity_id=movie.code,
        new_value={"title": movie.title, "code": movie.code, "via": "media_queue"},
    )
    await message.answer(f"Media Queue orqali qo'shildi!\n\n{format_movie_caption(movie)}")


register_admin_plugin(router)
