"""Inline keyboards for the in-bot admin panel."""

from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.keyboards.callback_data import (
    AdActionCallback,
    AdminMenuCallback,
    BlacklistActionCallback,
    BlacklistTypeCallback,
    CollectionActionCallback,
    DatabaseActionCallback,
    LogFilterCallback,
    MediaSourceActionCallback,
    MediaSourceTypeCallback,
    PaymentReviewCallback,
    SecurityActionCallback,
    SettingsCategoryCallback,
    SettingsEditCallback,
    WhitelistActionCallback,
    WhitelistTypeCallback,
)
from src.models.blacklist_entry import BlacklistEntryType
from src.models.whitelist_entry import WhitelistEntryType


def build_admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Return the top-level admin panel menu."""
    rows = [
        [
            InlineKeyboardButton(
                text="🎬 Kino boshqaruvi",
                callback_data=AdminMenuCallback(section="movies").pack(),
            ),
            InlineKeyboardButton(
                text="👥 Foydalanuvchilar",
                callback_data=AdminMenuCallback(section="users").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📢 Broadcast",
                callback_data=AdminMenuCallback(section="broadcast").pack(),
            ),
            InlineKeyboardButton(
                text="🔐 Majburiy obuna",
                callback_data=AdminMenuCallback(section="force_sub").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 Statistika", callback_data=AdminMenuCallback(section="stats").pack()
            ),
            InlineKeyboardButton(
                text="💾 Backup / Restore",
                callback_data=AdminMenuCallback(section="backup").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛡 Adminlar", callback_data=AdminMenuCallback(section="admins").pack()
            ),
            InlineKeyboardButton(
                text="⚙️ Sozlamalar", callback_data=AdminMenuCallback(section="settings").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="📈 Dashboard", callback_data=AdminMenuCallback(section="dashboard").pack()
            ),
            InlineKeyboardButton(
                text="🎞 Media Center",
                callback_data=AdminMenuCallback(section="media_center").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗂 Collections",
                callback_data=AdminMenuCallback(section="media_collections").pack(),
            ),
            InlineKeyboardButton(
                text="⛔ Blacklist", callback_data=AdminMenuCallback(section="blacklist").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="✅ Whitelist", callback_data=AdminMenuCallback(section="whitelist").pack()
            ),
            InlineKeyboardButton(
                text="📣 Reklama", callback_data=AdminMenuCallback(section="ads").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🛡 Xavfsizlik", callback_data=AdminMenuCallback(section="security").pack()
            ),
            InlineKeyboardButton(
                text="🗄 Loglar", callback_data=AdminMenuCallback(section="logs").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎞 Media manbalari",
                callback_data=AdminMenuCallback(section="media_sources").pack(),
            ),
            InlineKeyboardButton(
                text="💽 Database", callback_data=AdminMenuCallback(section="database").pack()
            ),
        ],
        [
            InlineKeyboardButton(
                text="💎 Premium",
                callback_data=AdminMenuCallback(section="premium_center").pack(),
            ),
            InlineKeyboardButton(
                text="📄 Docs", callback_data=AdminMenuCallback(section="docs").pack()
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_back_to_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Return a single "back" button that returns to the admin main menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack()
                )
            ]
        ]
    )


def build_movies_menu_keyboard() -> InlineKeyboardMarkup:
    """Return the movie-management submenu."""
    rows = [
        [
            InlineKeyboardButton(
                text="➕ Kino qo'shish",
                callback_data=AdminMenuCallback(section="movie_add").pack(),
            ),
            InlineKeyboardButton(
                text="🔍 Kino qidirish",
                callback_data=AdminMenuCallback(section="movie_search").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="✏️ Kod almashtirish",
                callback_data=AdminMenuCallback(section="movie_edit_code").pack(),
            ),
            InlineKeyboardButton(
                text="📝 Caption almashtirish",
                callback_data=AdminMenuCallback(section="movie_edit_caption").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📦 Bulk upload",
                callback_data=AdminMenuCallback(section="movie_bulk_upload").pack(),
            ),
            InlineKeyboardButton(
                text="🗑 Bulk delete",
                callback_data=AdminMenuCallback(section="movie_bulk_delete").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Premium Center ----------------------------------------------------


def build_admin_premium_keyboard(pending_count: int) -> InlineKeyboardMarkup:
    """Return the Premium Center admin menu (edit price/card, review payments)."""
    rows = [
        [
            InlineKeyboardButton(
                text="✏️ Narx va karta sozlamalari",
                callback_data=SettingsCategoryCallback(category="premium").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🧾 Kutilayotgan to'lovlar ({pending_count})",
                callback_data=AdminMenuCallback(section="premium_payments").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_payment_review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Return approve/reject buttons for one pending card payment request."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=PaymentReviewCallback(
                        action="approve", request_id=request_id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=PaymentReviewCallback(
                        action="reject", request_id=request_id
                    ).pack(),
                ),
            ]
        ]
    )


# --- Settings Center ---------------------------------------------------

_CATEGORY_LABELS: dict[str, str] = {
    "general": "🏠 Umumiy",
    "messages": "💬 Xabarlar",
    "support": "🆘 Yordam",
    "maintenance": "🛠 Texnik ishlar",
    "limits": "🚦 Limitlar",
    "premium": "⭐️ Premium",
    "referral": "🤝 Referral",
    "force_subscribe": "🔐 Majburiy obuna",
    "media": "🎬 Media",
    "scheduler": "⏰ Scheduler",
    "backup": "💾 Backup",
    "database": "💽 Database",
    "logging": "🗄 Logging",
    "notifications": "🔔 Bildirishnoma",
    "railway": "🚂 Railway",
    "advertisement": "📢 Reklama",
    "security": "🛡 Xavfsizlik",
}


def category_label(category: str) -> str:
    """Return a human-friendly label for a Settings Center category key."""
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def key_label(key: str) -> str:
    """Derive a human-friendly label for a raw settings key (e.g. "rate_limit_per_minute")."""
    return key.replace("_", " ").capitalize()


def build_settings_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """Return one button per Settings Center category, two per row."""
    buttons = [
        InlineKeyboardButton(text=category_label(category), callback_data=SettingsCategoryCallback(category=category).pack())
        for category in categories
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_settings_category_keyboard(category: str, entries: dict[str, dict[str, Any]]) -> InlineKeyboardMarkup:
    """Return one button per setting key in a category (booleans show a ✅/❌ toggle)."""
    rows = []
    for key, info in entries.items():
        value = info["value"]
        is_boolean = info["is_boolean"]
        if is_boolean:
            text = f"{'✅' if value else '❌'} {key_label(key)}"
        else:
            shown = str(value) if value not in (None, "") else "—"
            if len(shown) > 20:
                shown = shown[:20] + "…"
            text = f"✏️ {key_label(key)}: {shown}"
        rows.append([InlineKeyboardButton(text=text, callback_data=SettingsEditCallback(key=key).pack())])
    rows.append(
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data=AdminMenuCallback(section="settings").pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Media Collections ---------------------------------------------------


def build_collections_keyboard(collections: list) -> InlineKeyboardMarkup:
    """Return one row per collection (toggle/rename/delete) plus a "create" row."""
    rows = []
    for collection in collections:
        state_icon = "🟢" if collection.is_active else "⚪️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{state_icon} {collection.name}",
                    callback_data=CollectionActionCallback(action="toggle", collection_id=collection.id).pack(),
                ),
                InlineKeyboardButton(
                    text="⬆️", callback_data=CollectionActionCallback(action="up", collection_id=collection.id).pack()
                ),
                InlineKeyboardButton(
                    text="⬇️", callback_data=CollectionActionCallback(action="down", collection_id=collection.id).pack()
                ),
                InlineKeyboardButton(
                    text="🗑", callback_data=CollectionActionCallback(action="delete", collection_id=collection.id).pack()
                ),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Yangi collection", callback_data=CollectionActionCallback(action="create", collection_id=0).pack())]
    )
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Blacklist / Whitelist Center ---------------------------------------------------


def build_blacklist_type_keyboard() -> InlineKeyboardMarkup:
    """Return one button per :class:`BlacklistEntryType`."""
    rows = [
        [InlineKeyboardButton(text=entry_type.value, callback_data=BlacklistTypeCallback(entry_type=entry_type.value).pack())]
        for entry_type in BlacklistEntryType
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_blacklist_entries_keyboard(entry_type: str, entries: list) -> InlineKeyboardMarkup:
    """Return one row per blacklist entry of a type, with a remove button, plus an "add" row."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'🔴' if entry.is_active else '⚪️'} {entry.value}",
                callback_data=BlacklistActionCallback(entry_id=entry.id).pack(),
            )
        ]
        for entry in entries
    ]
    rows.append([InlineKeyboardButton(text="➕ Qo'shish", callback_data=BlacklistTypeCallback(entry_type=entry_type).pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Turlar", callback_data=AdminMenuCallback(section="blacklist").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_whitelist_type_keyboard() -> InlineKeyboardMarkup:
    """Return one button per :class:`WhitelistEntryType`."""
    rows = [
        [InlineKeyboardButton(text=entry_type.value, callback_data=WhitelistTypeCallback(entry_type=entry_type.value).pack())]
        for entry_type in WhitelistEntryType
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_whitelist_entries_keyboard(entry_type: str, entries: list) -> InlineKeyboardMarkup:
    """Return one row per whitelist entry of a type, with a remove button, plus an "add" row."""
    rows = [
        [InlineKeyboardButton(text=f"🟢 {entry.value}", callback_data=WhitelistActionCallback(entry_id=entry.id).pack())]
        for entry in entries
    ]
    rows.append([InlineKeyboardButton(text="➕ Qo'shish", callback_data=WhitelistTypeCallback(entry_type=entry_type).pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Turlar", callback_data=AdminMenuCallback(section="whitelist").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Advertisement Center ---------------------------------------------------


def build_ads_keyboard(campaigns: list) -> InlineKeyboardMarkup:
    """Return one row per ad campaign (toggle/delete), plus a "create" row."""
    rows = []
    for campaign in campaigns:
        state_icon = "🟢" if campaign.is_active else "⚪️"
        label = campaign.text[:24] if campaign.text else campaign.content_type.value
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{state_icon} {label}",
                    callback_data=AdActionCallback(action="toggle", campaign_id=campaign.id).pack(),
                ),
                InlineKeyboardButton(
                    text="🗑", callback_data=AdActionCallback(action="delete", campaign_id=campaign.id).pack()
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Yangi reklama", callback_data=AdActionCallback(action="create", campaign_id=0).pack())])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Security Center ---------------------------------------------------


def build_security_keyboard(pin_set: bool, two_factor_enabled: bool) -> InlineKeyboardMarkup:
    """Return the admin Security Center action menu."""
    rows = [
        [
            InlineKeyboardButton(
                text=("🔑 PIN-ni almashtirish" if pin_set else "🔑 PIN o'rnatish"),
                callback_data=SecurityActionCallback(action="set_pin").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=("🔓 2FA-ni o'chirish" if two_factor_enabled else "🔒 2FA-ni yoqish"),
                callback_data=SecurityActionCallback(action=("disable_2fa" if two_factor_enabled else "enable_2fa")).pack(),
            )
        ],
        [InlineKeyboardButton(text="📋 Faol sessiyalar", callback_data=SecurityActionCallback(action="list_sessions").pack())],
        [InlineKeyboardButton(text="🚪 Barcha sessiyalarni yopish", callback_data=SecurityActionCallback(action="logout_all").pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_security_login_keyboard() -> InlineKeyboardMarkup:
    """Return a minimal keyboard shown while an admin is going through the login gate."""
    return InlineKeyboardMarkup(inline_keyboard=[])


# --- Log Center ---------------------------------------------------


def build_log_filter_keyboard() -> InlineKeyboardMarkup:
    """Return one filter button per log level, plus "all"."""
    rows = [
        [
            InlineKeyboardButton(text="🟢 Info", callback_data=LogFilterCallback(level="info").pack()),
            InlineKeyboardButton(text="🟡 Warning", callback_data=LogFilterCallback(level="warning").pack()),
        ],
        [
            InlineKeyboardButton(text="🔴 Error", callback_data=LogFilterCallback(level="error").pack()),
            InlineKeyboardButton(text="⛔ Critical", callback_data=LogFilterCallback(level="critical").pack()),
        ],
        [InlineKeyboardButton(text="📄 Barchasi", callback_data=LogFilterCallback(level="all").pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Database Manager ---------------------------------------------------


def build_database_manager_keyboard() -> InlineKeyboardMarkup:
    """Return the Database Manager action menu (VACUUM/ANALYZE/REINDEX/optimize all)."""
    rows = [
        [InlineKeyboardButton(text="🧹 VACUUM", callback_data=DatabaseActionCallback(action="vacuum").pack())],
        [InlineKeyboardButton(text="📈 ANALYZE", callback_data=DatabaseActionCallback(action="analyze").pack())],
        [InlineKeyboardButton(text="🧱 REINDEX", callback_data=DatabaseActionCallback(action="reindex").pack())],
        [InlineKeyboardButton(text="⚡ To'liq optimizatsiya", callback_data=DatabaseActionCallback(action="optimize").pack())],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data=DatabaseActionCallback(action="refresh").pack())],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Media Sources ---------------------------------------------------


def build_media_source_type_keyboard() -> InlineKeyboardMarkup:
    """Return the channel-vs-group choice shown before the tap-to-pick list."""
    rows = [
        [
            InlineKeyboardButton(
                text="📢 Kanal", callback_data=MediaSourceTypeCallback(source_type="ch").pack()
            ),
            InlineKeyboardButton(
                text="👥 Guruh", callback_data=MediaSourceTypeCallback(source_type="gr").pack()
            ),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="media_sources").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_media_sources_keyboard(sources: list) -> InlineKeyboardMarkup:
    """Return one row per active media source (with a remove button) plus an add row."""
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources:
        rows.append(
            [
                InlineKeyboardButton(
                    text=source.title[:48],
                    callback_data=MediaSourceActionCallback(action="noop", chat_id=source.chat_id).pack(),
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=MediaSourceActionCallback(action="remove", chat_id=source.chat_id).pack(),
                ),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Manba qo'shish", callback_data=MediaSourceActionCallback(action="add", chat_id=0).pack())]
    )
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
