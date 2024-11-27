"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from ..elements.cons import Cons


if TYPE_CHECKING:
    from ..elements.idx import Idx
    from .function import F
    from .parameter import P
    from .variable import V


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(
        self,
        funcs: F,
        leq: bool = False,
    ):
        self.funcs = funcs
        self.leq = leq

        # since indices should match, take any

        # whether the constraint is binding
        self.binding = False

        self._ = [
            Cons(
                parent=self,
                pos=n,
                func=f,
                leq=self.leq,
            )
            for n, f in enumerate(self.funcs)
        ]

        self.index = self.funcs.index

        if self.leq:
            self.name = self.funcs.name + r'<=0'

        else:
            self.name = self.funcs.name + r'=0'

        # number of the set in the program
        self.n: int = None

    @property
    def nn(self):
        """Non-negativity Constraint"""
        if self.funcs.isnnvar() and self.leq:
            return True

    @property
    def eq(self):
        """Equality Constraint"""
        return not self.leq

    @property
    def one(self):
        """element one in function"""
        return self.funcs.one

    @property
    def two(self):
        """element two in function"""
        return self.funcs.two

    def matrix(self):
        """Matrix Representation"""

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'{self.funcs.latex()} {rel} 0'

    def pprint(self, descriptive: bool = False):
        """Display the function"""

        if descriptive:
            for c in self._:
                display(Math(c.latex()))
        else:
            display(Math(self.latex()))

    def sol(self):
        """Solution"""
        for c in self._:
            c.sol()

    def __call__(self, *key: tuple[Idx] | Idx) -> Cons:
        if len(key) == 1:
            return self._[self.idx[key[0]]]
        return self[self.idx[key]]

    def __getitem__(self, pos: int) -> Cons:
        return self._[pos]

    def __iter__(self):
        for i in self._:
            yield i

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self.index._)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
