"""
Bounded container previews for native views, without exporting full owners.
"""

from collections.abc import Mapping, Sequence
from itertools import islice
from reprlib import recursive_repr

DISPLAY_LIMIT = 10


def _representation(
    parts: list[str],
    size: int,
    opening: str,
    closing: str,
) -> str:
    """
    Mark omitted entries without fetching an additional value or
    coordinate.
    """
    if size > len(parts):
        parts.append("...")
    return opening + ", ".join(parts) + closing


def _pretty(printer, entries, size, opening, closing, *, mapping=False):
    """Use notebook line wrapping while visiting only the bounded preview."""
    with printer.group(1, opening, closing):
        for position, entry in enumerate(entries):
            if position:
                printer.text(",")
                printer.breakable()
            if mapping:
                key, value = entry
                printer.pretty(key)
                printer.text(": ")
            else:
                value = entry
            printer.pretty(value)
        if size > len(entries):
            printer.text(",")
            printer.breakable()
            printer.text("...")


class SequencePreview(Sequence):
    """
    List-shaped previews that avoid a facade's potentially eager iterator.
    """

    def _preview(self):
        """
        Read at most ten positions; numeric iteration exports the full
        buffer.
        """
        return [
            self[position] for position in range(min(len(self), DISPLAY_LIMIT))
        ]

    @recursive_repr(fillvalue="[...]")
    def __repr__(self) -> str:
        """Match ordinary list representations for small native views."""
        return _representation(
            [repr(value) for value in self._preview()],
            len(self),
            "[",
            "]",
        )

    def _repr_pretty_(self, printer, cycle) -> None:
        """
        Render notebook lists with native line wrapping and cycle
        protection.
        """
        if cycle:
            printer.text("[...]")
            return
        _pretty(printer, self._preview(), len(self), "[", "]")


class MappingPreview(Mapping):
    """
    Dictionary-shaped previews for insertion-ordered, lazily decoded maps.
    """

    def _preview(self):
        """
        Stop the native maps' lazy items iterators before full
        materialization.
        """
        return list(islice(self.items(), DISPLAY_LIMIT))

    @recursive_repr(fillvalue="{...}")
    def __repr__(self) -> str:
        """
        Show actual coordinates and values, with an explicit omission
        marker.
        """
        parts = [f"{key!r}: {value!r}" for key, value in self._preview()]
        return _representation(parts, len(self), "{", "}")

    def _repr_pretty_(self, printer, cycle) -> None:
        """Render notebook mappings without exporting every key or member."""
        if cycle:
            printer.text("{...}")
            return
        _pretty(printer, self._preview(), len(self), "{", "}", mapping=True)
