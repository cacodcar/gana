"""Parametric variable
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sympy import Idx, IndexedBase, Symbol, symbols

if TYPE_CHECKING:
    from .s import S


class T:
    """Parametric variable"""

    def __init__(self, *args: S, domain: tuple[float, float], name: str = 't'):
        self.index = args
        self.domain = domain
        self.name = name

    @property
    def sym(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.index:
            return IndexedBase(f'θ^{self.name}')[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        else:
            return Symbol(f'θ^{self.name}')

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
