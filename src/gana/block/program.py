"""Mathematical Program"""

from dataclasses import dataclass, field
from typing import Self

from gurobipy import read as gpread
from IPython.display import display

from ..elements.cons import Cons
from ..elements.func import Func
from ..elements.idx import X
from ..elements.obj import Obj
from ..elements.pvar import PVar
from ..elements.var import Var
from ..sets.constraint import C
from ..sets.function import F
from ..sets.index import I
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.variable import V
from .sets import Sets

try:
    from pyomo.environ import ConcreteModel as PyoModel

    has_pyomo = True
except ImportError:
    has_pyomo = False

# from ..value.zero import Z
# from ..sets.ordered import Set

# from ..sets.theta import T


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='prog')
    tol: float = field(default=None)
    canonical: bool = field(default=True)

    def __post_init__(self):
        self.names = []
        self.sets = Sets()
        self.names_idx = []
        self.indices: list[X] = []
        self.variables: list[Var] = []
        self.thetas: list[PVar] = []
        self.functions: list[Func] = []
        self.constraints: list[Cons] = []
        self.objectives: list[Obj] = []

        # is optimized
        self._isopt = False

        # number of:
        self._nx = 0  # index elements
        self._nvar = 0  # variables
        self._npvar = 0  # parametric variables
        self._nfunc = 0  # functions
        self._ncons = 0  # constraints
        self._nobj = 0  # objectives

    def __setattr__(self, name, value) -> None:

        if isinstance(value, (str, float, int, list, Sets)) or value is None:
            super().__setattr__(name, value)
            return

        if name in self.names:
            if isinstance(value, (I, V, P, T)) and getattr(self, name).mutable:
                value.mutable = True
            else:
                raise ValueError(f'{self.name}: Overwriting {name}')

        # set objects are set to self.sets
        # .pname is the name given by the user
        # F, C, Obj name are operations they perform

        if isinstance(value, I):
            if not name in self.names:
                self.names.append(name)
                setattr(self.sets, name, value)
                skip_set = False

            else:
                if getattr(self, name).mutable:
                    setattr(self.sets, name, getattr(self, name) | value)
                    skip_set = True
                skip_set = False

            if not value.ordered:
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

            if not skip_set:
                super().__setattr__(name, value)
            return

        elif isinstance(value, V):
            add_len = len(value._)
            add_vars = list(value._)

            for n, var in enumerate(add_vars):
                var.n = self._nvar + n

            self._nvar += add_len

            if not name in self.names:
                self.names.append(name)
                setattr(self.sets, name, value)
                if value.nn:
                    setattr(self, value.name + '_nn', -value <= 0)
                skip_set = False

            else:

                # the var set is mutable and new vars are being add
                var_ex: V = getattr(self.sets, name)  # existing var set

                if set(value.index).issubset(var_ex.index):
                    return

                for var in value._:
                    # push the positions of the new variables ahead
                    var.pos += len(var_ex._)
                    var.parent = var_ex

                # update the vars and index sets
                var_ex._ += value._
                var_ex.index |= value.index
                var_ex.idx = {idx: var for idx, var in zip(var_ex.index, var_ex._)}

                skip_set = True
                if value.nn:
                    setattr(
                        self,
                        var_ex.name + '_nn',
                        -var_ex(value.index) <= 0,
                    )

            self.variables += add_vars
            if not skip_set:
                super().__setattr__(name, value)
            return

        elif isinstance(value, P):
            add_len = len(value._)

            if not name in self.names:
                self.names.append(name)
                setattr(self.sets, name, value)
                make_set = False
            else:
                par_ex: P = getattr(self.sets, name)
                if par_ex.isnum and value.isnum:
                    make_set = False
                    par_ex.name = f'[ {par_ex.name}, {value.name} ]'
                else:
                    make_set = True

                if set(value.index).issubset(par_ex.index):
                    return

                par_ex._ += value._
                par_ex.index |= value.index
                par_ex.idx = {idx: par for idx, par in zip(par_ex.index, par_ex._)}

            if not make_set:
                super().__setattr__(name, value)
            return

        elif isinstance(value, T):
            add_len = len(value._)
            add_pvars = list(value._)

            if not name in self.names:
                self.names.append(name)
                setattr(self.sets, name, value)
                skip_set = False
            else:
                pvar_ex: P = getattr(self.sets, name)

                if set(value.index).issubset(pvar_ex.index):
                    return

                for pvar in value._:
                    # push the positions of the new variables ahead
                    pvar.pos += len(pvar_ex._)
                    pvar.parent = pvar_ex

                pvar_ex._ += value._
                pvar_ex.index |= value.index
                pvar_ex.idx = {idx: pvar for idx, pvar in zip(pvar_ex.index, pvar_ex._)}

                skip_set = True

            for n, pvar in enumerate(add_pvars):
                pvar.n = self._npvar + n

            self._npvar += add_len

            self.thetas += add_pvars
            if not skip_set:
                super().__setattr__(name, value)
            return

        elif isinstance(value, F):
            setattr(self.sets, name, value)
            value.pname = name
            self.functions += value._

            for n, f in enumerate(value._):
                f.n = self._nfunc + n

            self._nfunc += len(value._)

            super().__setattr__(name, value)
            return

        elif isinstance(value, C):
            setattr(self.sets, name, value)
            value.pname = name
            self.constraints += value._

            for n, c in enumerate(value._):
                c.n = self._ncons + n

            self._ncons += len(value._)

            super().__setattr__(name, value)
            return

        elif isinstance(value, Obj):
            self.names.append(name)
            value.pname = name
            value.n = self._nobj
            self._nobj += 1
            self.objectives.append(value)

            super().__setattr__(name, value)
            return

        elif isinstance(value, X):
            value.n = self._nx
            self._nx += 1
            self.indices.append(value)
            self.names_idx.append(value.name)

            super().__setattr__(name, value)
            return

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

    @property
    def B(self, zero: bool = True) -> list[float | None]:
        """RHS Parameter vector"""
        return [c.B for c in self.constraints]
        # return [c.func.B(zero) for c in self.cons()]

    @property
    def A(self, zero: bool = True) -> list[list[float | None]]:
        """Matrix of Variable coefficients"""
        if zero:
            _A = [[0] * len(self.contvars()) for _ in range(len(self.cons()))]
        else:
            _A = [[None] * len(self.contvars()) for _ in range(len(self.cons()))]
        for n, c in enumerate(self.constraints):
            for x, a in zip(c.X, c.A):
                if x is not None:
                    _A[n][x] = a

        return _A

    @property
    def F(self, zero: bool = True) -> list[list[float | None]]:
        """Matrix of Variable coefficients"""
        if zero:
            _F = [[0] * len(self.thetas) for _ in range(len(self.cons()))]
        else:
            _F = [[None] * len(self.thetas) for _ in range(len(self.cons()))]

        n = 0
        for c in self.sets.constraint:
            m = 0
            for z, f in zip(c.Z, c.F):
                if z[m]:
                    _F[n][z[m]] = f[m]
                n += 1
                m += 1
        return _F

    @property
    def C(self, zero: bool = True) -> list[float]:
        """Objective Coefficients"""
        c_ = []

        for o in self.objectives:
            if zero:
                row = [0] * len(self.contvars())
            else:
                row = [None] * len(self.contvars())

            for n, value in zip(o.X, o.A):
                row[n] = value
            c_.append(row)
        if len(self.objectives) == 1:
            return c_[0]
        return c_

    @property
    def X(self) -> list[list[int]]:
        """Structure of the constraint matrix"""
        return [c.X for c in self.constraints]

    @property
    def Z(self) -> list[list[int]]:
        """Structure of the constraint matrix"""
        return [c.Z for c in self.constraints]

    @property
    def G(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        g < = 0
        """
        if zero:
            _G = [[0] * len(self.contvars()) for _ in range(len(self.leqcons()))]
        else:
            _G = [[None] * len(self.contvars()) for _ in range(len(self.leqcons()))]

        for n, c in enumerate(self.leqcons()):
            for x, a in zip(c.X, c.A):
                if x is not None:
                    _G[n][x] = a

        return _G

    @property
    def H(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        h = 0
        """
        if zero:
            _H = [[0] * len(self.contvars()) for _ in range(len(self.eqcons()))]
        else:
            _H = [[None] * len(self.contvars()) for _ in range(len(self.eqcons()))]

        for n, c in enumerate(self.eqcons()):
            for x, a in zip(c.X, c.A):
                if x is not None:
                    _H[n][x] = a

        return _H

    @property
    def NN(self, zero: bool = True) -> list[float | None]:
        """Matrix of Variable coefficients for non negative cons"""
        if zero:
            _NN = [[0] * len(self.contvars()) for _ in range(len(self.nncons()))]
        else:
            _NN = [[None] * len(self.contvars()) for _ in range(len(self.nncons()))]

        for n, c in enumerate(self.nncons()):
            for x, a in zip(c.X, c.A):
                if x is not None:
                    _NN[n][x] = a

        return _NN

    @property
    def CRa(self) -> list[list[float | None]]:
        """Critical Region Matrix"""
        CRa_UB = [[0] * len(self.thetas) for _ in range(len(self.thetas))]
        CRa_LB = [[0] * len(self.thetas) for _ in range(len(self.thetas))]

        for n in range(len(self.thetas)):
            CRa_UB[n][n] = 1.0
            CRa_LB[n][n] = -1.0

        CRa_ = []

        for n in range(len(self.thetas)):
            CRa_.append(CRa_UB[n])
            CRa_.append(CRa_LB[n])

        return CRa_

    @property
    def CRb(self) -> list[float | None]:
        """CRb"""
        CRb_ = []
        for t in self.thetas:
            CRb_.append(t._[1])
            CRb_.append(-t._[0])

        return CRb_

    def pyomo(self):
        """Pyomo Model"""
        if has_pyomo:
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
        print(
            'pyomo is an optional dependency, pip install gana[all] to get optional dependencies'
        )

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
                        f.write(f'{self.C[v.n]}')
                    else:
                        f.write(f'{self.A[c.n][v.n]}')
                    f.write('\n')

            f.write('RHS\n')
            for n, c in enumerate(self.leqcons() + self.eqcons()):
                f.write(ws * 4)
                f.write(f'RHS{n}')
                f.write(ws * (10 - len(f'RHS{n+1}')))
                f.write(c.mps())
                f.write(ws * (10 - len(c.mps())))
                f.write(f'{c.B}')
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
            for c in self.sets.cons():
                display(c.latex())

            for c in self.cons():
                if not c.parent:
                    display(c.latex())

    def pprint(self, descriptive: bool = False):
        """Pretty Print"""

        print(rf'Mathematical Program for {self.name}')

        if self.sets.index:
            print()
            print(r'---Index Sets---')
            print()

            for i in self.sets.index:
                if len(i) != 0:
                    i.pprint(True)

        if self.objectives:
            print()
            print(r'---Objective(s)---')
            print()

            for o in self.objectives:
                o.pprint()
        if self.functions:
            print()
            print(r'---Functions---')
            print()
            for f in self.functions:
                f.pprint()

        if descriptive:

            print()
            print(r'---Such that---')
            print()

            if self.leqcons():
                print(r'Inequality Constraints:')
                for c in self.leqcons():
                    c.pprint()
            if self.eqcons():
                print(r'Equality Constraints:')
                for c in self.eqcons():
                    c.pprint()

            if self.nncons():
                print(r'Non-Negativity Constraints:')
                for c in self.nncons():
                    c.pprint()

        else:

            if self.sets.nncons():
                print(r'Non-Negative Variables:')
                self.sets.I_nn.pprint()

            print()
            print(r'---Such that---')
            print()

            if self.sets.leqcons():
                print(r'Inequality Constraints:')
                for c in self.sets.leqcons():
                    c.pprint()
            if self.sets.eqcons():
                print(r'Equality Constraints:')
                for c in self.sets.eqcons():
                    c.pprint()

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(str(self))

    def __add__(self, other: Self):
        """Add two programs"""

        if not isinstance(other, Prg):
            raise ValueError('Can only add programs')

        prg = Prg(name=rf'{self.name}')

        for i in (
            self.sets.index
            + other.sets.index
            + self.sets.variable
            + other.sets.variable
            + self.sets.parameter
            + other.sets.parameter
        ):
            if not i.name in prg.names:
                setattr(prg, i.name, i)
            else:
                if isinstance(i, I) and i.mutable:
                    setattr(prg, i.name, getattr(prg, i.name) | i)

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
            if not i.name in prg.names:
                setattr(prg, i.pname, i)

        return prg
