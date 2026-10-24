"""Objective serialization preserves cycles, shared rows and copied owners."""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, Prg, V, inf, sigma
from gana.storage.parameters import NATIVE

CHECK = TestCase()


def roundtrip(value, operation):
    """Exercise memoized Python copying and actual pickle reconstruction."""
    if operation == "deepcopy":
        return deepcopy(value)
    return pickle.loads(pickle.dumps(value))


@pytest.mark.parametrize("operation", ["deepcopy", "pickle"])
@pytest.mark.parametrize("root", ["function", "objective", "program", "pair"])
@pytest.mark.parametrize("exposed", [False, True])
def test_registered_objective_copy(operation, root, exposed):
    """Every graph entry point retains one objective and isolated variables.

    Starting at the function reaches its objective through variable membership
    before the function has received its state. The restore order must not
    affect coefficients, ownership, or the active objective used for export.
    """
    program = Prg()
    program.i = I(size=3)
    program.x = V(program.i)
    program.o = inf(sigma(2 * program.x) + 5)
    function = program.o.function
    if exposed:
        list(function.variables)
    roots = {
        "function": function,
        "objective": program.o,
        "program": program,
        "pair": (function, program.o),
    }
    restored = roundtrip(roots[root], operation)
    objective = copied_objective(restored, root)
    check_objective(objective, program)


def copied_objective(restored, root):
    """
    Locate the same objective when reconstruction starts at different roots.
    """
    if root == "function":
        objective = restored.variables[0].min_by[0]
        CHECK.assertTrue(objective.function is restored)
    elif root == "program":
        objective = restored.o
        CHECK.assertTrue(restored.C == [2, 2, 2])
    elif root == "pair":
        copied_function, objective = restored
        CHECK.assertTrue(objective.function is copied_function)
    else:
        objective = restored
    return objective


def check_objective(objective, program):
    """
    Check exact coefficients, shared graph identity and isolated membership.
    """
    CHECK.assertTrue(objective is not program.o)
    CHECK.assertTrue(objective.function is objective._)
    CHECK.assertTrue(objective.matrix == {0: 2, 1: 2, 2: 2})
    CHECK.assertEqual(objective.constant, 5)
    for copied, original in zip(objective.variables, program.o.variables):
        CHECK.assertTrue(copied is not original)
        CHECK.assertTrue(any(item is objective for item in copied.min_by))
        CHECK.assertTrue(all(item is not program.o for item in copied.min_by))
    if NATIVE:
        CHECK.assertTrue(
            objective._native_batch is objective.function._native_batch,
        )
    objective.unregister_variables()
    CHECK.assertTrue(
        all(not variable.min_by for variable in objective.variables),
    )
    CHECK.assertTrue(
        all(variable.min_by == [program.o] for variable in program.x),
    )
    objective.update_variables()
    CHECK.assertTrue(
        all(
            variable.min_by == [objective] for variable in objective.variables
        ),
    )
