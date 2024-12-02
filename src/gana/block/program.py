"""Mathematical Program"""

from dataclasses import dataclass, field
from warnings import warn

from typing import Self

from IPython.display import display
from pyomo.environ import ConcreteModel as PyoModel
from gurobipy import read as gpread

# from pyomo.environ import Constraint as PyoCons


# from ..elements.element import X
from ..elements.obj import Obj

from ..sets.index import I
from ..elements.idx import X
from ..sets.variable import V
from ..elements.var import Var
from ..sets.parameter import P
from ..sets.function import F
from ..elements.func import Func
from ..sets.constraint import C
from ..elements.cons import Cons


# from ..value.zero import Z
# from ..sets.ordered import Set

# from ..sets.theta import T

from .sets import Sets


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='prog')
    tol: float = field(default=None)
    canonical: bool = field(default=True)

    def __post_init__(self):
        self.names = []
        self.reserved = []
        self.sets = Sets()
        self.names_idx = []
        self.indices: list[X] = []
        self.variables: list[Var] = []
        # self.thetas: list[Th] = []
        self.functions: list[Func] = []
        self.constraints: list[Cons] = []
        self.objectives: list[Obj] = []

        # is optimized
        self._isopt = False

    def __setattr__(self, name, value) -> None:

        if hasattr(self, 'names') and name in self.names:
            raise ValueError(f'Overwriting {name}')

        if hasattr(self, 'reserved') and name in self.reserved:
            raise ValueError(f'Cannot use {name} as a name')

        if name[-1] == '_':
            warn(f'{name}: names ending with _ can cause printing issues')

        if isinstance(value, (I, V, P, F, C)):
            self.names.append(name)
            # set all element sets onto sets
            setattr(self.sets, name, value)

        if isinstance(value, (F, C, Obj)):
            # name given by user in program
            # names of constraints and functions are otherwise the operation they perform
            value.pname = name

        # Indices
        if isinstance(value, I) and not value.ordered:

            for n, idx in enumerate(value._):
                if idx.name in self.names_idx:
                    # if index already declared as part of another index set
                    # update her parent

                    idx = self.indices[self.indices.index(idx)]
                    if not value in idx.parent:
                        idx._parent.append(value)
                        idx._pos.append(n)
                        value._[n] = idx
                else:
                    setattr(self, idx.name, idx)

        if isinstance(value, X):
            value.n = len(self.indices)
            self.indices.append(value)
            self.names_idx.append(value.name)

        if isinstance(value, (V, F, C)):
            for e in value._:
                setattr(self, e.name, e)

        if isinstance(value, V):
            if value.nn:
                setattr(self, value.name + '_nn', -value <= 0)

        if isinstance(value, Var):
            value.n = len(self.variables)
            self.variables.append(value)

        if isinstance(value, Func):
            value.n = len(self.functions)
            self.functions.append(value)

        if isinstance(value, Cons):
            value.n = len(self.constraints)
            self.constraints.append(value)
            # if not value.name:
            #     value.name = name
            # setattr(self, value.name + '_f', value.func)

        if isinstance(value, Obj):
            value.n = len(self.objectives)
            self.objectives.append(value)
            # setattr(self, value.name + '_f', value.func)

        super().__setattr__(name, value)

    def vardict(self) -> dict[V, Var]:
        """Variables"""
        return {v: v._ for v in self.sets.variable}

    def nncons(self, n: bool = False) -> list[int | Cons]:
        """non-negativity constraints"""
        if n:
            return [x.n for x in self.constraints if x.nn]
        return [x for x in self.constraints if x.nn]

    def eqcons(self, n: bool = False) -> list[int | Cons]:
        """equality constraints"""
        if n:
            return [x.n for x in self.constraints if not x.leq]
        return [x for x in self.constraints if not x.leq]

    def leqcons(self, n: bool = False) -> list[int | Cons]:
        """less than or equal constraints"""
        if n:
            return [x.n for x in self.constraints if x.leq and not x.nn]
        return [x for x in self.constraints if x.leq and not x.nn]

    def cons(self, n: bool = False) -> list[int | Cons]:
        """constraints"""
        return self.leqcons(n) + self.eqcons(n) + self.nncons(n)

    def nnvars(self, n: bool = False) -> list[int | Var]:
        """non-negative variables"""
        if n:
            return [x.n for x in self.variables if x.nn]
        return [x for x in self.variables if x.nn]

    def bnrvars(self, n: bool = False) -> list[int | Var]:
        """binary variables"""
        if n:
            return [x.n for x in self.variables if x.bnr]
        return [x for x in self.variables if x.bnr]

    def intvars(self, n: bool = False) -> list[int | Var]:
        """integer variables"""
        if n:
            return [x.n for x in self.variables if x.itg]
        return [x for x in self.variables if x.itg]

    def contvars(self, n: bool = False) -> list[int | Var]:
        """continuous variables"""
        if n:
            return [x.n for x in self.variables if not x.bnr and not x.itg]
        return [x for x in self.variables if not x.bnr and not x.itg]

    def B(self, zero: bool = True) -> list[float | None]:
        """RHS Parameter vector"""
        return [c.func.B(zero) for c in self.cons()]

    def A(self, zero: bool = True) -> list[list[float | None]]:
        """Matrix of Variable coefficients"""
        a_ = []

        for c in self.cons():
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())
            for n, value in zip(c.X(), c.A()):
                row[n] = value
            a_.append(row)
        return a_

    def _A(self) -> list[list[float]]:
        """Matrix of Variable coefficients"""
        a_ = []

        for c in self.constraints:
            row = [0] * len(self.contvars())
            for n, value in zip(c.X(), c.A()):
                row[n] = value
            a_.append(row)
        return a_

    def C(self, zero: bool = True) -> list[float]:
        """Objective Coefficients"""
        c_ = []

        for o in self.objectives:
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())

            for n, value in zip(o.X(), o.A()):
                row[n] = value
            c_.append(row)
        if len(self.objectives) == 1:
            return c_[0]
        return c_

    def matrix(
        self, zero: bool = False
    ) -> tuple[list[list[float | None]], list[float | None]]:
        """Matrix Representation"""
        return self.A(zero), self.B(zero)

    def X(self) -> list[list[int]]:
        """Structure of the constraint matrix"""
        return [c.X() for c in self.constraints]

    def G(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        g < = 0
        """
        g_ = []

        for c in self.leqcons():
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())
            for n, value in zip(c.X(), c.A()):
                row[n] = value
            g_.append(row)
        return g_

    def H(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        h = 0
        """
        h_ = []

        for c in self.eqcons():
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())
            for n, value in zip(c.X(), c.A()):
                row[n] = value
            h_.append(row)
        return h_

    def NN(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for non negative cons"""
        nn_ = []

        for c in self.nncons():
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())
            for n, value in zip(c.X(), c.A()):
                row[n] = value
            nn_.append(row)
        return nn_

    def pyomo(self):
        """Pyomo Model"""

        m = PyoModel()

        for s in self.sets.index:
            setattr(m, s.name, s.pyomo())

        for v in self.sets.variable:
            setattr(m, v.name, v.pyomo())

        # for p in self.parsets:
        #     setattr(m, p.name, p.pyomo())

        # for c in self.conssets:
        #     setattr(m, c.name, c.pyomo(m))

        return m

    def mps(self, name: str = None):
        """MPS File"""
        ws = ' '
        with open(f'{name or self.name}.mps', 'w', encoding='utf-8') as f:
            f.write(f'NAME{ws*10}{self.name.upper()}\n')
            f.write('ROWS\n')
            f.write(f'{ws}N{ws*3}{self.objectives[0].mps()}\n')
            for c in self.leqcons():
                f.write(f'{ws}L{ws*3}{c.mps()}\n')
            for c in self.eqcons():
                f.write(f'{ws}E{ws*3}{c.mps()}\n')
            f.write('COLUMNS\n')
            for v in self.variables:
                vs = len(v.mps())
                for c in v.features:
                    vfs = len(c.mps())
                    f.write(ws * 4)
                    f.write(v.mps())
                    f.write(ws * (10 - vs))
                    f.write(c.mps())
                    f.write(ws * (10 - vfs))
                    if isinstance(c, Obj):
                        f.write(f'{self.C()[v.n]}')
                    else:
                        f.write(f'{self._A()[c.n][v.n]}')
                    f.write('\n')

            f.write('RHS\n')
            for n, c in enumerate(self.leqcons() + self.eqcons()):
                f.write(ws * 4)
                f.write(f'RHS{n}')
                f.write(ws * (10 - len(f'RHS{n+1}')))
                f.write(c.mps())
                f.write(ws * (10 - len(c.mps())))
                f.write(f'{c.B()}')
                f.write('\n')
            f.write('ENDATA')

    def gurobi(self):
        """Gurobi Model"""
        self.mps()
        return gpread(f'{self.name}.mps')

    def lp(self):
        """LP File"""
        m = self.gurobi()
        m.write(f'{self.name}.lp')

    def opt(self, using: str = 'gurobi'):
        """Solve the program"""

        if using == 'gurobi':
            m = self.gurobi()
            m.optimize()
            vals = [v.X for v in m.getVars()]
            for v, val in zip(self.variables, vals):
                v._ = val

            for f in self.functions:
                f.eval()

        self._isopt = True

    def vars(self):
        """Optimal Variable Values"""
        return {v: v._ for v in self.variables}

    def obj(self):
        """Objective Values"""
        if len(self.objectives) == 1:
            return self.objectives[0]._
        return {o: o._ for o in self.objectives}

    def slack(self):
        """Slack in each constraint"""
        return {c: c._ for c in self.leqcons()}

    def sol(self):
        """Print sol"""

        if not self._isopt:
            return r'Use .opt() to generate solution'

        print(rf'Solution for {self.name}')
        print()
        print(r'---Objective Value(s)---')
        print()
        for o in self.objectives:
            o.sol()

        print()
        print(r'---Variable Value---')
        print()

        for v in self.variables:
            v.sol()

        print()
        print(r'---Constraint Slack---')
        print()

        for c in self.leqcons() + self.eqcons():
            c.sol()

    # Displaying the program
    def latex(self, descriptive: bool = False):
        """Display LaTeX"""

        for s in self.sets.index:
            display(s.latex(True))

        for o in self.objectives:
            display(o.latex())

        if descriptive:
            for c in self.cons():
                display(c.latex())

        else:
            for c in self.sets.cons():  # + self.objectives:
                display(c.latex())

            for c in self.cons():
                if not c.parent:
                    display(c.latex())

    def pprint(self, descriptive: bool = False):
        """Pretty Print"""

        print(rf'Mathematical Program for {self.name}')
        print()
        print(r'---Index Sets---')
        print()

        for i in self.sets.index:
            i.pprint(True)

        print()
        print(r'---Objective(s)---')
        print()

        for o in self.objectives:
            o.pprint()

        print()
        print(r'---Such that---')
        print()

        if descriptive:
            for c in self.cons():
                c.pprint()

        else:
            for c in self.sets.cons():
                c.pprint()

            for c in self.cons():
                if not c.parent:
                    c.pprint()

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __add__(self, other: Self):
        """Add two programs"""

        if not isinstance(other, Prg):
            raise ValueError('Can only add programs')

        prg = Prg(name=rf'{self.name}_{other.name}')

        # for i in self.sets.index:
        #     if i in other.sets.index:
        #         i = i | getattr(other.sets, i.name)
        #     setattr(prg, i.name, i)
        # for i in other.sets.index:
        #     if i in self.sets.index:
        #         i = i | getattr(self.sets, i.name)
        #     setattr(prg, i.name, i)

        # for v in self.sets.variable:
        #     if v in other.sets.variable:
        #         v = V(v)

        for i in (
            self.sets.index
            + other.sets.index
            + self.sets.variable
            + other.sets.variable
            + self.sets.parameter
            + other.sets.parameter
        ):
            if i.name not in prg.names:
                setattr(prg, i.name, i)

        for i in (
            self.sets.function
            + other.sets.function
            + self.sets.leqcons()
            + self.sets.eqcons()
            + other.sets.leqcons()
            + other.sets.eqcons()
            + self.objectives
            + other.objectives
        ):
            if i.name not in prg.names:
                setattr(prg, i.pname, i)

        return prg
