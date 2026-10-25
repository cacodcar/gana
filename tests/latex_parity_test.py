"""Mathematical display contracts shared by Python and deferred native rows."""

from copy import deepcopy
from importlib import import_module
from unittest import TestCase

import pytest

from gana import I, P, Prg, V, inf, sigma, sup

CHECK = TestCase()


def model():
    """Create named coefficients and symbols with independent oracles."""
    p = Prg()
    p.i = I("a", "b", "c")
    p.x = V(p.i, ltx=r"\chi", mutable=True)
    p.k = P(p.i, _=[20, 6, 8])
    return p


@pytest.mark.parametrize("compose, sign", [(inf, 1), (sup, -1)])
@pytest.mark.parametrize("roundtrip", [False, True])
def test_scalar_objective_prints_captured_numbers(compose, sign, roundtrip):
    """Expand numeric coefficients, retain signs and show scalar IDs."""
    p = model()
    expression = sum(p.k(i) * p.x(i) for i in p.i)
    p.o = compose(expression)
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    if roundtrip:
        p = deepcopy(p)
    p.k._[:] = [99, 99, 99]
    terms = [
        r"20.0 \cdot {\mathbf{\chi}}_{{a}}",
        r"6.0 \cdot {\mathbf{\chi}}_{{b}}",
        r"8.0 \cdot {\mathbf{\chi}}_{{c}}",
    ]
    body = " + ".join(terms) if sign == 1 else "-" + " - ".join(terms)
    expected = r"min \hspace{0.2cm} " + body
    for _ in range(2):
        CHECK.assertEqual(p.o.latex(), expected)
        CHECK.assertEqual(p.o.function.latex(), body)
        CHECK.assertEqual(p.o.function.n, 0)
        CHECK.assertEqual(p.o.matrix, {0: sign * 20, 1: sign * 6, 2: sign * 8})


@pytest.mark.parametrize(
    "selected, expected",
    [
        (False, r"{\mathrm{k}}_{{i}} \cdot {\mathbf{{\mathbf{\chi}}}}_{{i}}"),
        (
            True,
            r"{\mathrm{{\mathrm{k}}}}_{{a}} \cdot "
            r"{\mathbf{{\mathbf{{\mathbf{\chi}}}}}}_{{a}}",
        ),
    ],
)
def test_snapshot_retains_existing_font_depth(selected, expected):
    """Private snapshots must not add a public-copy font wrapper."""
    p = model()
    x, k = (p.x(p.a), p.k(p.a)) if selected else (p.x, p.k)
    expression = k * x
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertEqual(expression.latex(), expected)
    CHECK.assertEqual(expression.latex(), expected)
    CHECK.assertEqual(p.x.latex(), r"{\mathbf{\chi}}_{{i}}")


def test_reduction_display_and_registration_remain_independent(monkeypatch):
    """Retain compact sums and update displayed IDs after registration."""
    p = model()
    expression = sigma(p.k * p.x)
    expected = (
        r"\sum \left({\mathrm{k}}_{{i}} \cdot "
        r"{\mathbf{{\mathbf{\chi}}}}_{{i}}\right)"
    )
    CHECK.assertEqual(expression.latex(), expected)
    p.first = p.x + 1
    p.total = expression
    p.o = inf(expression)
    CHECK.assertEqual(p.o.latex(), r"min \hspace{0.2cm} " + expected)
    CHECK.assertEqual(p.total.n, 1)
    CHECK.assertEqual(p.total[0].n, 3)
    displayed = []
    monkeypatch.setattr(
        import_module("gana.sets.function"),
        "display",
        displayed.append,
    )
    p.total.show()
    p.o.function.show()
    CHECK.assertEqual(
        [value.data for value in displayed],
        [
            r"[1]\text{   }" + expected,
            r"[1]\text{   }" + expected,
        ],
    )


def test_scalar_objective_does_not_relabel_original_expression():
    """Keep a reused collection's syntax after scalar objective formatting."""
    p = model()
    p.term = p.k(p.a) * p.x(p.a)
    before = p.term.latex()
    p.o = inf(p.term)
    CHECK.assertEqual(
        p.o.latex(),
        r"min \hspace{0.2cm} 20.0 \cdot {\mathbf{\chi}}_{{a}}",
    )
    CHECK.assertEqual(p.term.latex(), before)
    CHECK.assertEqual(p.term.n, 0)


def test_objective_retains_named_reduction_metadata():
    """Deferred selection preserves names and categories on retained roots."""
    p = model()
    p.total = sigma(p.k * p.x)
    p.total.category = "Costs"
    p.o = inf(p.total)
    CHECK.assertEqual(p.o.function.pname, "total")
    CHECK.assertEqual(p.o.function.category, "Costs")
    CHECK.assertEqual(p.o.function.n, 0)
    p.total.category = "Updated costs"
    p.total.pname = "updated_total"
    CHECK.assertEqual(p.o.function.category, "Updated costs")
    CHECK.assertEqual(p.o.function.pname, "updated_total")
