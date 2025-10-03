"""Printing Utilities"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..sets.index import I


def multi_name(*index: I):
    """returns a name for tuple index with underscores"""
    return "_".join([i.name for i in index])
