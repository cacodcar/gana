"""An index"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .element import X

if TYPE_CHECKING:
    from ..sets.index import I


class Idx(X):
    """An index"""

    def __init__(self):
        super().__init__(self)
        self.parents: list[I] = []

