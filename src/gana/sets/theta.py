"""Parametric variable
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sympy import Idx, IndexedBase, Symbol, symbols

if TYPE_CHECKING:
    from .index import I


class T:
    """Parametric variable"""

    def __init__(self, *args: I, _: tuple[float, float], name: str = 'mpvar'):
        self.index = args

        # Parametric variables can take a value within a domain
        # Can be especially useful when value are uncertain
        self._ = _
        self.name = name

        # keeps a count of, updated in program
        self.count: int = None

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __call__(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.index:
            return IndexedBase(f'θ^{self.name}')[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        else:
            return Symbol(f'θ^{self.name}')

    # TODO - __mul__ and __add__ methods
