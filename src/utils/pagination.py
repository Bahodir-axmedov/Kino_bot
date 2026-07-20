"""Small pagination helper shared by list-style admin/user views."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page:
    """Pagination window derived from a 0-based page index and page size."""

    index: int
    size: int

    @property
    def offset(self) -> int:
        """Return the SQL ``OFFSET`` corresponding to this page."""
        return max(self.index, 0) * self.size

    @property
    def limit(self) -> int:
        """Return the SQL ``LIMIT`` corresponding to this page."""
        return self.size

    def next(self) -> "Page":
        """Return the next page."""
        return Page(index=self.index + 1, size=self.size)

    def previous(self) -> "Page":
        """Return the previous page, clamped at zero."""
        return Page(index=max(self.index - 1, 0), size=self.size)
