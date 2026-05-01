"""Tests for the OperationResult helpers used by frontend service wrappers."""

from __future__ import annotations

from patrimony.frontend.services.models import (
    OperationResult,
    operation_result,
    safe_query,
)


def test_operation_result_wraps_plain_return():
    @operation_result(failure="boom", success="ok")
    def fn():
        return None

    result = fn()
    assert isinstance(result, OperationResult)
    assert result.success is True
    assert result.message == "ok"
    assert result.data is None


def test_operation_result_uses_dict_as_data():
    @operation_result()
    def fn():
        return {"id": 7}

    result = fn()
    assert result.success is True
    assert result.data == {"id": 7}


def test_operation_result_passes_through_existing_result():
    inner = OperationResult(success=False, message="custom")

    @operation_result()
    def fn():
        return inner

    assert fn() is inner


def test_operation_result_catches_exception():
    @operation_result(failure="add failed")
    def fn():
        raise ValueError("bad ticker")

    result = fn()
    assert result.success is False
    assert "add failed" in result.message
    assert "bad ticker" in result.message


def test_safe_query_returns_default_on_exception():
    @safe_query(default=[])
    def fn():
        raise RuntimeError("db down")

    assert fn() == []


def test_safe_query_passes_through_value():
    @safe_query(default=[])
    def fn():
        return [1, 2, 3]

    assert fn() == [1, 2, 3]


def test_safe_query_returns_none_when_no_default():
    @safe_query()
    def fn():
        raise RuntimeError("db down")

    assert fn() is None
