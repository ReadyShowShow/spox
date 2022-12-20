import numpy
import pytest

from spox import Var, _type_system
from spox._graph import arguments, results
from spox._shape import Shape
from spox._value_prop import ORTValue, PropValue


def dummy_var(typ=None, value=None):
    """Function for creating a ``var`` without an operator but with a type and value."""
    return Var(None, typ, value)  # type: ignore


def assert_equal_value(var: Var, expected: ORTValue):
    """
    Convenience function for comparing a ``var``'s propagated value and an expected one.
    Expected Types vs value types:

    - Tensor - numpy.ndarray
    - Optional - spox.var.Nothing or the underlying type
    - Sequence - list of underlying type
    """
    assert var._value is not None, "var.value expected to be known"
    value = var._value.to_ort_value()
    if isinstance(var.type, _type_system.Tensor):
        expected = numpy.array(expected)
        assert var.type.dtype.type == expected.dtype.type, "element type must match"
        assert Shape.from_simple(expected.shape) <= var.type._shape, "shape must match"
        numpy.testing.assert_allclose(value, expected)
    elif isinstance(var.type, _type_system.Optional):
        if expected is None:
            assert value is None, "value must be Nothing when optional is empty"
        else:
            assert_equal_value(
                dummy_var(var.type.elem_type, var._value.value), expected
            )
    elif isinstance(var.type, _type_system.Sequence):
        assert isinstance(value, list), "value must be list when it is a Sequence"
        assert isinstance(
            expected, list
        ), "expected value must be list when tested type is a Sequence"
        assert len(value) == len(expected), "sequence length must match"
        for a, b in zip(value, expected):
            assert_equal_value(
                dummy_var(
                    var.type.elem_type, PropValue.from_ort_value(var.type.elem_type, a)
                ),
                b,
            )
    else:
        raise NotImplementedError(f"Datatype {var.type}")


def test_sanity_no_prop(op):
    (x,) = arguments(x=_type_system.Tensor(numpy.int64, ()))
    op.add(x, x)


def test_sanity_const(op):
    assert_equal_value(op.const(2), numpy.int64(2))


def test_add(op):
    assert_equal_value(op.add(op.const(2), op.const(2)), numpy.int64(4))


def test_div(op):
    assert_equal_value(op.div(op.const(5.0), op.const(2.0)), numpy.float32(2.5))


def test_identity(op):
    for x in [
        5,
        [1, 2, 3],
        numpy.array([[1, 2], [3, 4], [5, 6]]),
        numpy.array(0.5, dtype=numpy.float32),
    ]:
        assert_equal_value(op.const(x), x)


def test_reshape(op):
    assert_equal_value(
        op.reshape(op.const([1, 2, 3, 4]), op.const([2, 2])), [[1, 2], [3, 4]]
    )


def test_optional(op):
    assert_equal_value(op.optional(op.const(2.0)), numpy.float32(2.0))


def test_empty_optional(op):
    assert_equal_value(op.optional(type=_type_system.Tensor(numpy.float32, ())), None)


def test_empty_optional_has_no_element(op):
    assert_equal_value(
        op.optional_has_element(
            op.optional(type=_type_system.Tensor(numpy.float32, ()))
        ),
        False,
    )


def test_sequence_empty(op):
    assert_equal_value(op.sequence_empty(dtype=numpy.float32), [])


def test_sequence_append(op):
    emp = op.sequence_empty(dtype=numpy.int64)
    assert_equal_value(
        op.sequence_insert(op.sequence_insert(emp, op.const(2)), op.const(1)), [2, 1]
    )


def test_with_reconstruct(op):
    a, b = arguments(
        a=_type_system.Tensor(numpy.int64, ()),
        b=_type_system.Tensor(numpy.int64, ()),
    )
    c = op.add(a, b)
    graph = (
        results(c=c).with_arguments(a, b)._with_constructor(lambda x, y: [op.add(x, y)])
    )
    assert_equal_value(
        graph._reconstruct(op.const(2), op.const(3)).requested_results["c"], 5
    )


def test_bad_reshape_raises(op):
    op.reshape(op.const([1, 2]), op.const([2]))  # sanity
    with pytest.raises(Exception):
        op.reshape(op.const([1, 2, 3]), op.const([2]))
