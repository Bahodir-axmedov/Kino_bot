"""Finite-state-machine states for movie-catalogue admin flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MovieFormStates(StatesGroup):
    """Add/edit a single movie entry, one field at a time."""

    waiting_for_media = State()
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_genre = State()
    waiting_for_language = State()
    waiting_for_country = State()
    waiting_for_year = State()
    waiting_for_quality = State()
    waiting_for_description = State()
    confirm = State()


class EditCodeStates(StatesGroup):
    """Replace the code of an existing movie."""

    waiting_for_movie_code = State()
    waiting_for_new_code = State()


class EditCaptionStates(StatesGroup):
    """Replace the caption of an existing movie."""

    waiting_for_movie_code = State()
    waiting_for_new_caption = State()


class BulkUploadStates(StatesGroup):
    """Accept a stream of media messages and auto-index each one."""

    collecting = State()


class SearchMovieStates(StatesGroup):
    """Free-text admin/user movie search."""

    waiting_for_query = State()


class MediaQueueStates(StatesGroup):
    """Media Queue: media was auto-captured in a group, now waiting for its code."""

    waiting_for_code = State()


class CodeManagementStates(StatesGroup):
    """Kod boshqaruvi: reserve/release a movie code from the admin panel."""

    waiting_for_code_to_reserve = State()
    waiting_for_code_to_release = State()


class MediaCenterStates(StatesGroup):
    """Media Center: search/preview/replace-code/replace-caption/export/import."""

    waiting_for_preview_code = State()
    waiting_for_move_code = State()
    waiting_for_move_destination = State()
    waiting_for_import_file = State()
    # Search (#16): free-text advanced search (title/genre/year/language/
    # country/actor/director) from the Media Center.
    waiting_for_search_query = State()


class MediaSourceStates(StatesGroup):
    """Multi Media Source (#1): create/edit a named media source category."""

    waiting_for_chat_id = State()
    waiting_for_title = State()
    waiting_for_category = State()


class SupportStates(StatesGroup):
    """Admin Reply (#12): user writes to support; admin replies from the panel."""

    waiting_for_user_message = State()
    waiting_for_admin_reply = State()
