"""Resolved inverse links stay live without repeated high-arity scans."""

from unittest import TestCase

import pytest

from gana import I, Prg, V, sigma
from gana.backends.native import membership

CHECK = TestCase()


def model(size):
    """Register a vector bound and one row containing every variable."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i)
    bound = 10
    p.first = 2 * p.x <= bound
    p.total = sigma(p.x) <= size
    return p


@pytest.mark.parametrize("size", [8, 64])
def test_inverse_lookup_queries_each_member_once(size, monkeypatch):
    """Repeated lookups cost one initial member pass, including a dense row."""
    p = model(size)
    row = p.total[0]
    calls = []
    original = membership.read

    def counted(member):
        """Count member queries without changing their behavior."""
        calls.append(id(member))
        return original(member)

    monkeypatch.setattr(membership, "read", counted)
    positions = row.cons_by_pos
    for variable in row.variables:
        CHECK.assertIs(row.cons_by_pos, positions)
        CHECK.assertEqual(row.cons_by_pos[variable], 1)
    CHECK.assertEqual(len(calls), size)
    CHECK.assertEqual(len(set(calls)), size)
    CHECK.assertNotIn("_legacy_cache", p.total.__dict__)


def test_inverse_alias_survives_registration_replacement_and_edits():
    """Refresh and removal update escaped dictionaries without rescanning."""
    p = model(8)
    row = p.total[0]
    positions = row.cons_by_pos
    first_member = p.x[0]
    links = first_member.cons_by
    extra_bound, replacement_bound = 12, 16
    p.extra = 3 * p.x <= extra_bound
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertIs(first_member.cons_by, links)
    CHECK.assertIs(links[positions[first_member]], row)
    p.first = 4 * p.x <= replacement_bound
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertIs(first_member.cons_by, links)
    for variable in row.variables:
        CHECK.assertIs(variable.cons_by[positions[variable]], row)
    edited = 123
    positions[first_member] = edited
    CHECK.assertEqual(row.cons_by_pos[first_member], edited)
    CHECK.assertIs(p.total[0], row)
