"""
Readable native previews must not undo lazy ownership or snapshot
semantics.
"""

from unittest import TestCase

import pytest
from IPython.lib.pretty import pretty

from gana import I, P, Prg, T, V
from gana.storage.parameters import (
    ParameterMap,
    ParameterStorage,
    ParameterValues,
)
from gana.storage.symbols import SymbolMap, SymbolStorage, SymbolValues

CHECK = TestCase()
PREVIEW_SIZE = 10


def program(kind, size):
    """Register native data without accessing symbolic members."""
    p = Prg()
    p.i = I(size=size)
    options = {P: {"_": list(range(size))}, T: {"_": (0, 2)}, V: {}}
    p.e = kind(p.i, mutable=True, **options[kind])
    return p


@pytest.mark.parametrize("kind", [P, V, T])
@pytest.mark.parametrize("size", [1, 4, PREVIEW_SIZE])
@pytest.mark.parametrize("attribute", ["_", "map"])
def test_small_views_match_python_containers(kind, size, attribute):
    """
    Notebook wrapping and ordinary repr match explicitly materialized small
    views.
    """
    p = program(kind, size)
    view = getattr(p.e, attribute)
    expected = list(view) if attribute == "_" else dict(view)
    CHECK.assertEqual(repr(view), repr(expected))
    CHECK.assertEqual(str(view), str(expected))
    CHECK.assertEqual(
        pretty(view, max_width=32),
        pretty(expected, max_width=32),
    )


class ScalarReadsOnly:
    """
    Reject accidental bulk numeric export and record every displayed
    position.
    """

    def __init__(self, handle):
        """
        Wrap the real native payload after model registration has
        completed.
        """
        self.handle, self.reads = handle, []

    def __len__(self):
        """Allow cheap size queries without exporting values."""
        return len(self.handle)

    def get(self, position):
        """
        Retain evidence of exactly which scalar values the renderer
        fetched.
        """
        self.reads.append(position)
        return self.handle.get(position)

    def values(self):
        """
        Fail if a preview invokes the facade's eager whole-buffer iterator.
        """
        message = "Preview exported the full numeric buffer"
        raise AssertionError(message)


@pytest.mark.parametrize("render", [repr, pretty])
@pytest.mark.parametrize("attribute", ["_", "map"])
def test_numeric_previews_read_only_the_visible_prefix(render, attribute):
    """A thousand-value owner requires only ten reads and no bulk export."""
    p = program(P, 1000)
    storage = p.e._native_storage
    payload = ScalarReadsOnly(storage.handle)
    storage.handle = payload
    text = render(getattr(p.e, attribute))
    CHECK.assertEqual(payload.reads, list(range(PREVIEW_SIZE)))
    CHECK.assertIn("...", text)
    CHECK.assertEqual(len(p.e), 1000)


@pytest.mark.parametrize("kind", [V, T])
@pytest.mark.parametrize("render", [repr, pretty])
@pytest.mark.parametrize("attribute", ["_", "map"])
def test_symbol_previews_materialize_only_the_visible_prefix(
    kind,
    render,
    attribute,
):
    """
    Large displays cannot fill persistent Python metadata for every member.
    """
    p = program(kind, 1000)
    owner = p.e._symbol_storage
    CHECK.assertEqual(owner.states, {})
    text = render(getattr(p.e, attribute))
    CHECK.assertEqual(set(owner.states), set(range(PREVIEW_SIZE)))
    CHECK.assertIn("...", text)
    CHECK.assertEqual(len(p.e), 1000)


@pytest.mark.parametrize("kind", [V, T])
def test_scalar_member_facades_display_the_shared_member(kind):
    """
    A member's self-containing compatibility view remains finite and
    readable.
    """
    p = program(kind, 1)
    member = p.e[0]
    CHECK.assertEqual(repr(member._), "[e[0]]")
    CHECK.assertEqual(pretty(member._), "[e[0]]")
    CHECK.assertIs(member._[0], member)
    CHECK.assertEqual(pretty(member.map), pretty({member.index: member}))


@pytest.mark.parametrize("attribute", ["_", "map"])
def test_empty_native_facades_display_empty_containers(attribute):
    """Empty memberships need no coordinate lookup or scalar wrapper."""
    p = program(V, 1)
    owner = p.e._symbol_storage
    empty = SymbolStorage(p.e, owner.positions.take([]), owner)
    numeric = ParameterStorage([], [])
    facades = {
        "_": (ParameterValues(numeric), SymbolValues(empty)),
        "map": (ParameterMap(numeric), SymbolMap(empty)),
    }
    expected = "[]" if attribute == "_" else "{}"
    for view in facades[attribute]:
        CHECK.assertEqual(repr(view), expected)
        CHECK.assertEqual(pretty(view), expected)
    CHECK.assertEqual(owner.states, {})


def test_numeric_preview_respects_selected_order_and_captured_versions():
    """
    Rendering never caches stale text or detaches/mutates a captured
    payload.
    """
    p = program(P, 3)
    selected = p.e(p.i[::-1])
    CHECK.assertEqual(pretty(selected._), "[2.0, 1.0, 0.0]")
    p.e._[0] = 99
    CHECK.assertEqual(repr(p.e._), "[99.0, 1.0, 2.0]")
    CHECK.assertEqual(repr(selected._), "[2.0, 1.0, 0.0]")
    CHECK.assertEqual(pretty(selected.map), pretty(dict(selected.map)))
    selected._[0] = 7
    CHECK.assertEqual(repr(selected._), "[7.0, 1.0, 0.0]")
    CHECK.assertEqual(repr(p.e._), "[99.0, 1.0, 2.0]")


@pytest.mark.parametrize("kind", [V, T])
def test_symbol_preview_tracks_growth_metadata_and_fixed_selections(kind):
    """
    Retained root views stay live; selections preserve their member order.
    """
    p = program(kind, 3)
    selected = p.e(p.i[::-1])
    values, mapping = p.e._, p.e.map
    p.j = I("extra")
    p.e = kind(p.j, **({"_": (0, 2)} if kind is T else {}))
    p.e[0].name = "chosen"
    CHECK.assertEqual(repr(values), "[chosen, e[1], e[2], e[3]]")
    CHECK.assertEqual(repr(selected._), "[e[2], e[1], chosen]")
    CHECK.assertEqual(pretty(mapping), pretty(dict(mapping)))
