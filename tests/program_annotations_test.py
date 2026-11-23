"""Program signatures remain inspectable with deferred annotations."""

from inspect import signature
from typing import TypeAliasType, get_args

from gana import Prg
from gana.sets.constraint import C


def test_nonnegativity_signature_resolves_constraint_rows():
    """Prg.C must not replace the constraint type during introspection."""
    result = signature(Prg.nncons).return_annotation
    alternatives = {
        item.__value__ if isinstance(item, TypeAliasType) else item
        for item in get_args(result)
    }
    assert alternatives == {list[C], list[int]}
