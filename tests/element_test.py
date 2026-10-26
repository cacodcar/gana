"""Regression checks for shared element storage and selection behavior."""

import io
from contextlib import redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from src.gana import I, P, Prg, T, V, inf
from src.gana.sets._element import _E


class ElementTests(TestCase):
    """Protect numerical members, symbolic identity, and compiled semantics."""

    def setUp(self):
        """Create registered elements with distinct values and theta bounds."""
        self.program = Prg(name="element_contract")
        self.program.i = I("a", "b")
        self.program.j = I("c", "d")
        self.program.p = P(
            self.program.i,
            _=[2, -3],
            tag="input",
            mutable=True,
        )
        self.program.x = V(self.program.i, tag="decision", itg=True)
        self.program.t = T(
            self.program.i,
            _=[(0, 5), (1, 9)],
            tag="uncertainty",
        )

    def test_abstract_contract(self):
        """Require selection and rendering without imposing arithmetic
        dispatch.
        """
        self.assertEqual(_E.__abstractmethods__, {"__call__", "ltx", "latex"})
        with self.assertRaises(TypeError):
            _E()

    def test_parameter_members_remain_numbers(self):
        """Indexing, slicing, and iteration expose numerical values."""
        parameter = self.program.p
        self.assertEqual(list(parameter), [2.0, -3.0])
        self.assertEqual(parameter[1:], [-3.0])
        self.assertIsInstance(parameter[0], float)
        self.assertEqual(parameter(self.program.a)._, [2.0])
        self.assertIs(parameter(self.program.i), parameter)

    def test_variable_selection_preserves_identity(self):
        """Selections and copies refer to the original registered scalar
        objects.
        """
        variable = self.program.x
        selected = variable(self.program.a)
        copied = variable.copy()
        self.assertIs(selected[0], variable[0])
        self.assertIs(copied[0], variable[0])
        self.assertIs(copied.copyof, variable)
        self.assertIsNot(copied.map, variable.map)
        self.assertIsNot(copied._, variable._)
        self.assertEqual(variable[1:], [variable[1]])

    def test_exact_variable_selection_preserves_copy_flag(self):
        """Exact calls flag the original; forced selections return a view."""
        variable = self.program.x
        self.assertFalse(variable.make_copy)
        self.assertIs(variable(self.program.i), variable)
        self.assertTrue(variable.make_copy)
        selected = variable(self.program.i, make_new=True)
        self.assertIsNot(selected, variable)
        self.assertIs(selected[0], variable[0])

    def test_missing_indices_retain_subclass_policies(self):
        """Parameter misses raise; variable misses remain empty slots."""
        with self.assertRaises(KeyError):
            self.program.p(self.program.c)
        self.assertEqual(self.program.x(self.program.c)._, [None])

    def test_variable_as_index_remains_atomic(self):
        """A variable coordinate stays atomic when used as an index."""
        coordinate = self.program.x[0]
        parameter = P(coordinate, _=7)
        self.assertEqual(parameter._, [7.0])
        self.assertIs(parameter.index[0][0], coordinate)
        self.assertIs(next(iter(parameter.map))[0], coordinate)
        self.assertIs(parameter(coordinate), parameter)

    def test_union_of_products_keeps_map_order(self):
        """Overlapping index groups retain first-seen keys and their values."""
        program = self.program
        parameter = P((program.i, program.c), (program.a, program.j), _=4)
        keys = [tuple(item.name for item in key) for key in parameter.map]
        self.assertEqual(keys, [("a", "c"), ("b", "c"), ("a", "d")])
        self.assertEqual(parameter._, [4.0, 4.0, 4.0])

    def test_constructor_metadata_survives_selection(self):
        """Common metadata and variable domains survive view creation."""
        parameter = self.program.p(self.program.a)
        variable = self.program.x(self.program.a)
        self.assertEqual(parameter.tag, "input")
        self.assertTrue(parameter.mutable)
        self.assertEqual(parameter.name, self.program.p.name)
        self.assertEqual(parameter.n, self.program.p.n)
        self.assertEqual(variable.tag, "decision")
        self.assertTrue(variable.itg)
        self.assertTrue(variable.nn)
        self.assertFalse(variable.bnr)
        self.assertEqual(self.program.t.args["tag"], "uncertainty")

    def test_registered_theta_members_keep_bounds_and_identity(self):
        """Theta registration connects each coordinate to its bounds."""
        theta = self.program.t
        self.assertIs(theta(self.program.i), theta)
        self.assertIs(theta[0].parent, theta)
        self.assertIs(theta.map[(self.program.a,)], theta[0])
        self.assertEqual(
            [(item.lb, item.ub) for item in theta],
            [(0, 5), (1, 9)],
        )
        self.assertEqual(self.program.CrB, [5, 0, 9, -1])

    def test_length_policies_are_preserved(self):
        """Unregistered V counts children; P and T count coordinates."""
        self.assertEqual(len(V(self.program.i)), 0)
        self.assertEqual(len(P(self.program.i, _=3)), 2)
        self.assertEqual(len(T(self.program.i, _=[(0, 1), (0, 1)])), 2)

    def test_names_and_hashes_are_preserved(self):
        """Inherited naming uses the parent while repr/hash retain legacy
        rules.
        """
        self.assertEqual(self.program.x.longname, "x(i)")
        self.assertEqual(self.program.x[0].longname, "x(a)")
        self.assertEqual(self.program.t[1].longname, "t(b)")
        for element in (self.program.p, self.program.x, self.program.t):
            self.assertEqual(repr(element), element.name)
            self.assertEqual(hash(element), hash(element.name))

    def test_symbolic_display_uses_each_member(self):
        """Descriptive V/T output renders scalars; ordinary output renders
        sets.
        """
        for element in (self.program.x, self.program.t):
            with patch("src.gana.sets._element.display") as render:
                element.show(descriptive=True)
                actual = [call.args[0].data for call in render.call_args_list]
                self.assertEqual(
                    actual,
                    [member.latex() for member in element],
                )
                render.reset_mock()
                element.show()
                self.assertEqual(
                    render.call_args.args[0].data,
                    element.latex(),
                )

    def test_parameter_display_preserves_numbers_and_collection(self):
        """Descriptive P output prints values and still renders its full
        symbol.
        """
        output = io.StringIO()
        with (
            redirect_stdout(output),
            patch("src.gana.sets._element.display") as render,
        ):
            self.program.p.show(descriptive=True)
        self.assertEqual(output.getvalue(), "2.0\n-3.0\n")
        self.assertEqual(render.call_args.args[0].data, self.program.p.latex())

    def test_compiled_coefficients_are_unchanged(self):
        """Check an indexed formulation against expected matrices."""
        program = self.program
        program.c = program.x >= program.p
        program.o = inf(sum(program.x))
        self.assertEqual(program.A, [[-1, 0], [0, -1]])
        self.assertEqual(program.B, [-2, 3])
        self.assertEqual(program.C, [1, 1])
