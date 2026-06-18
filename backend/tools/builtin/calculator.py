# tools/builtin/calculator.py
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_ALLOWED_FUNCTIONS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sqrt": math.sqrt, "log": math.log, "log2": math.log2, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
    "ceil": math.ceil, "floor": math.floor, "trunc": math.trunc,
    "exp": math.exp, "factorial": math.factorial,
    "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf,
}


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self) -> None:
        self._result: Any = None

    def evaluate(self, expression: str) -> float:
        tree = ast.parse(expression.strip(), mode="eval")
        return self.visit(tree.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        return node.value

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op_func = _ALLOWED_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return op_func(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_func = _ALLOWED_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
        operand = self.visit(node.operand)
        return op_func(operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only built-in function calls are allowed")
        func_name = node.func.id
        func = _ALLOWED_FUNCTIONS.get(func_name)
        if func is None:
            raise ValueError(f"Function not allowed: {func_name}")
        args = [self.visit(arg) for arg in node.args]
        return func(*args)

    def visit_Name(self, node: ast.Name) -> Any:
        const = _ALLOWED_FUNCTIONS.get(node.id)
        if const is None or not isinstance(const, (int, float)):
            raise ValueError(f"Name not allowed: {node.id}")
        return const

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


CALCULATOR_SCHEMA = ToolSchema(
    name="calculator",
    description=(
        "Evaluate mathematical expressions safely. Supports: +, -, *, /, //, %, ** operators; "
        "math functions: sqrt, log, log2, log10, sin, cos, tan, ceil, floor, round, abs, exp, factorial; "
        "constants: pi, e, tau. Examples: '2 ** 32', 'sqrt(2) * pi', 'log(1000, 10)'."
    ),
    parameters=[
        ToolParameter(name="expression", type=ToolParameterType.STRING, description="Mathematical expression to evaluate", required=True),
        ToolParameter(name="precision", type=ToolParameterType.INTEGER, description="Decimal places to round result to (default: 10)", required=False, default=10),
    ],
    returns="number",
    category="math",
)


async def calculator_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    expression = arguments["expression"]
    precision = int(arguments.get("precision", 10))
    evaluator = _SafeEvaluator()
    try:
        raw_result = evaluator.evaluate(expression)
        if math.isnan(raw_result):
            raise ValueError("Result is NaN")
        if math.isinf(raw_result):
            return {"expression": expression, "result": float("inf") if raw_result > 0 else float("-inf"), "is_infinite": True}
        rounded = round(float(raw_result), precision)
        return {"expression": expression, "result": rounded, "precision": precision}
    except ZeroDivisionError:
        raise ValueError("Division by zero")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Expression error: {exc}") from exc
