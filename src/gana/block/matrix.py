"""Matrix Representation of a Program"""

from dataclasses import dataclass, field


@dataclass
class Mtx:
    """Matrix representation of Program

    Attributes:
        a (list[list[float]]): Constraint matrix for variables
        b (list[float]): Constraint matrix for parameters
        f (list[list[float]]): Constraint matrix for thetas
        c (list[float]): Objective matrix for linear variables
        q (list[list[float]]): Objective matrix for quadratic variables
        h (list[list[float]]): Objective matrix for thetas
        at (list[list[float]]): Critical region bounds for thetas
        bt (list[float]): Critical region bounds for parameters

    """

    # constaint matrices
    # equality functions = 0 (with some tolerance)
    h: list[list[float]] = field(default_factory=list)
    
    # inequality functions <= 0 (with some tolerance)
    g: list[list[float]] = field(default_factory=list)

    # objective functions
    c: list[float] = field(default_factory=list)

    # # constaint matrices
    # # vars lhs
    # a: list[list[float]] = field(default_factory=list)
    # # params lhs
    # b: list[float] = field(default_factory=list)
    # # thetas rhs
    # f: list[list[float]] = field(default_factory=list)

    # # objective matrices
    # # vars linear
    # c: list[float] = field(default_factory=list)
    # # vars quadratic
    # q: list[list[float]] = field(default_factory=list)
    # # thetas
    # h: list[list[float]] = field(default_factory=list)

    # # critical region bounds
    # # thetas
    # at: list[list[float]] = field(default_factory=list)
    # # params
    # bt: list[float] = field(default_factory=list)
