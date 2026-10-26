"""Protect timing decorator behavior before extracting message construction."""

import logging
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gana.utils.decorators import timer


@pytest.mark.parametrize(
    "kind,result,message",
    [
        ("generate-mps", "sample", "📝  Generated sample.mps"),
        (
            "generate-solution",
            "sample",
            "📝  Generated Solution object for sample. See .solution",
        ),
        ("generate-ppopt", True, "📝  Generated MPLP. See .formulation"),
        (
            "generate-gurobi",
            True,
            "📝  Generated gurobipy model. See .formulation",
        ),
        ("solve-mpqp", True, "✅  Solved MPLP using PPOPT. See .solution"),
        (
            "optimize",
            ("sample", "gurobi"),
            "✅  sample optimized using gurobi. Display using .output()",
        ),
    ],
)
@pytest.mark.parametrize("with_return", [False, True])
def test_timer_messages_and_return_policy(
    monkeypatch,
    kind,
    result,
    message,
    with_return,
):
    """Retain exact message text, elapsed formatting and object identity."""
    module = import_module("gana.utils.decorators")
    clock = SimpleNamespace(time=Mock(side_effect=(10.0, 10.125)))
    monkeypatch.setattr(module, "time", clock)
    logger = Mock(spec=logging.Logger)
    operation = Mock(return_value=result)
    wrapped = timer(logger, kind, with_return, logging.DEBUG)(operation)
    actual = wrapped("input", enabled=True)
    operation.assert_called_once_with("input", enabled=True)
    logger.log.assert_called_once_with(
        logging.DEBUG,
        f"{message:<75} ⏱ {0.125:.4f} s",
    )
    assert actual is (result if with_return else None)


@pytest.mark.parametrize("result", [None, False, 0, "", []])
@pytest.mark.parametrize("with_return", [False, True])
def test_timer_falsey_results_do_not_log(result, with_return):
    """Unsuccessful calls skip message construction even for unknown kinds."""
    logger = Mock(spec=logging.Logger)
    wrapped = timer(logger, "unknown", with_return)(Mock(return_value=result))
    actual = wrapped()
    assert actual is (result if with_return else None)
    logger.log.assert_not_called()


def test_timer_propagates_operation_failure():
    """Exceptions from the wrapped function escape without a success log."""
    logger = Mock(spec=logging.Logger)
    error = RuntimeError("operation failed")
    wrapped = timer(logger, "generate-mps")(Mock(side_effect=error))
    with pytest.raises(RuntimeError) as caught:
        wrapped()
    assert caught.value is error
    logger.log.assert_not_called()


@pytest.mark.parametrize("kind", [None, "unknown"])
def test_timer_unknown_kind_retains_failure(kind):
    """Keep the existing unsupported-kind failure during this refactor."""
    logger = Mock(spec=logging.Logger)
    wrapped = timer(logger, kind)(Mock(return_value=True))
    with pytest.raises(UnboundLocalError):
        wrapped()
    logger.log.assert_not_called()
