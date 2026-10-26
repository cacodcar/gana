"""Native-only contracts beyond the unchanged Python compatibility suite."""

import copy
import gc
import weakref
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, V, inf
from gana._native import NumericOwner, NumericPayload

CHECK = TestCase()


def parameter():
    """Build a mutable registered parameter with named coordinates."""
    p = Prg()
    p.i = I("a", "b", "c")
    p.k = P(p.i, _=[1, 2, 3], mutable=True)
    return p


def test_synchronized_atomic_raw_writes():
    """Both facades reflect one batch and invalid batches change neither."""
    p = parameter()
    values, mapping = p.k._, p.k.map
    values[::2] = [4, 6]
    CHECK.assertEqual(list(mapping.values()), [4, 2, 6])
    mapping.update({(p.a,): 7, (p.b,): 8})
    CHECK.assertEqual(list(values), [7, 8, 6])
    version = p.k._native_storage.handle.version
    with pytest.raises((ValueError, TypeError)):
        mapping.update({(p.a,): 9, (p.b,): object()})
    with pytest.raises(TypeError):
        mapping.update({(p.a,): 9, ("missing",): 0})
    with pytest.raises(TypeError):
        values[:] = [9]
    CHECK.assertEqual(list(values), [7, 8, 6])
    CHECK.assertEqual(p.k._native_storage.handle.version, version)


@pytest.mark.parametrize(
    "operation",
    [
        lambda p: p.k._.append(4),
        lambda p: p.k._.pop(),
        lambda p: p.k._.reverse(),
        lambda p: p.k.map.clear(),
        lambda p: setattr(p.k, "_", [4, 5, 6]),
        lambda p: setattr(p.k, "map", {}),
    ],
)
def test_structural_edits_rejected(operation):
    """
    Raw growth, deletion, reordering and container replacement cannot drift.
    """
    p = parameter()
    with pytest.raises(TypeError, match="through its program"):
        operation(p)
    CHECK.assertEqual(list(p.k._), [1, 2, 3])


def test_nested_snapshots_detach_and_preserve_expression_capture():
    """
    Nested selections retain the original version through later raw writes.
    """
    p = parameter()
    selected = p.k(p.i[::-2])
    nested = selected(p.a)
    p.x = V(p.i)
    p.o = inf((nested * p.x(p.a))[0])
    p.k._[:] = [4, 5, 6]
    selected._[0] = 20
    CHECK.assertEqual(list(selected._), [20, 1])
    CHECK.assertEqual(list(nested._), [1])
    CHECK.assertEqual(list(p.k._), [4, 5, 6])
    np.testing.assert_array_equal(p.C, [1, 0, 0])


def test_root_identity_replacement_and_reclamation():
    """Retained old containers do not pin the replacement owner or program."""
    p = parameter()
    owner = p.k._native_storage.owner
    owner_ref, program_ref = weakref.ref(owner), weakref.ref(p)
    old = p.k._
    with pytest.warns(UserWarning):
        p.k = P(p.i, _=[4, 5, 6])
    CHECK.assertIs(p.k._native_storage.owner, owner)
    old[0] = 99
    CHECK.assertEqual(list(p.k._), [4, 5, 6])
    del owner, p
    gc.collect()
    CHECK.assertIs(owner_ref(), None)
    CHECK.assertIs(program_ref(), None)
    CHECK.assertEqual(list(old), [99, 2, 3])


def test_native_lifetimes_and_detached_export():
    """
    Native views survive their handles; explicit exports cannot mutate them.
    """
    owner = NumericOwner([1, 2, 3])
    payload = owner.payload()
    selected = payload.span(2, -1, 3)
    ref = weakref.ref(payload)
    exported = selected.values()
    exported[0] = 99
    del owner, payload
    gc.collect()
    CHECK.assertIs(ref(), None)
    CHECK.assertEqual(selected.values(), [3, 2, 1])
    CHECK.assertGreaterEqual(selected.reserved_bytes, 24)


def test_native_invalid_batches_do_not_advance_versions():
    """Boundary checks and Python extraction failures precede mutation."""
    payload = NumericPayload([1, 2])
    for positions, values, error in [
        ([0, 9], [3, 4], IndexError),
        ([0], [3, 4], ValueError),
        ([0, 1], [3, object()], TypeError),
    ]:
        with pytest.raises(error):
            payload.set_many(positions, values)
    CHECK.assertEqual(payload.values(), [1, 2])
    CHECK.assertEqual(payload.version, 0)


def test_deepcopy_preserves_shared_facades_and_program_binding():
    """Serialization recreates native state without serializing locks."""
    p = copy.deepcopy(parameter())
    CHECK.assertIs(p.k._.storage, p.k.map.storage)
    p.k.map[(p.a,)] = 7
    CHECK.assertEqual(list(p.k._), [7, 2, 3])
    with pytest.warns(UserWarning):
        p.k = P(p.i, _=[4, 5, 6])
    CHECK.assertEqual(list(p.k._), [4, 5, 6])
    CHECK.assertIs(p.k._owner_root._program_token, p._owner_token)


def test_numpy_export_and_constant_case_refresh():
    """NumPy copies detach and raw writes invalidate constant shortcuts."""
    p = parameter()
    array = np.asarray(p.k._)
    array[0] = 99
    CHECK.assertEqual(list(p.k._), [1, 2, 3])
    p.constant = P(p.i, _=2)
    p.constant._[0] = 7
    CHECK.assertEqual(list((p.constant + 1)._), [8, 3, 3])


def test_nan_registration_remains_compatible():
    """A shared payload needs no contradictory NaN equality comparison."""
    p = parameter()
    p.k._[0] = float("nan")
    CHECK.assertTrue(np.isnan(p.k._validated_values()[(p.a,)]))
