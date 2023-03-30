from spox.opset.ai.onnx import v17 as op17
from spox.opset.ai.onnx import v18 as op18
from spox.opset.ai.onnx.ml import v3 as ml3


def test_ai_onnx_v17():
    op17.add(op17.constant(value_int=2), op17.constant(value_int=2))


def test_ai_onnx_v18():
    op18.bitwise_and(op17.constant(value_int=7), op17.constant(value_int=10))


def test_ai_onnx_ml_v3():
    ml3.label_encoder(
        op17.constant(value_ints=[1, 2, 3]),
        keys_int64s=[0, 1, 2],
        values_strings=["a", "b", "c"],
        default_string="?",
    )