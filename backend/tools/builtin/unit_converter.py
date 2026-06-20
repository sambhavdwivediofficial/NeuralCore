# tools/builtin/unit_converter.py
from __future__ import annotations

from typing import Any

from tools.schemas import ToolParameter, ToolParameterType, ToolSchema

_LENGTH_TO_METERS: dict[str, float] = {
    "m": 1.0, "meter": 1.0, "meters": 1.0, "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
    "cm": 0.01, "mm": 0.001, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
    "ft": 0.3048, "feet": 0.3048, "foot": 0.3048, "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
    "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
}

_WEIGHT_TO_GRAMS: dict[str, float] = {
    "g": 1.0, "gram": 1.0, "grams": 1.0, "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
    "lb": 453.592, "lbs": 453.592, "pound": 453.592, "pounds": 453.592,
    "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
}

_VOLUME_TO_LITERS: dict[str, float] = {
    "l": 1.0, "liter": 1.0, "liters": 1.0, "ml": 0.001, "milliliter": 0.001,
    "gal": 3.78541, "gallon": 3.78541, "gallons": 3.78541,
    "cup": 0.236588, "cups": 0.236588, "fl_oz": 0.0295735, "floz": 0.0295735,
}

UNIT_CONVERTER_SCHEMA = ToolSchema(
    name="unit_converter",
    description=(
        "Convert between units of measurement: length/distance (m, km, mi, ft, in, yd), "
        "weight/mass (g, kg, lb, oz), volume (l, ml, gal, cup), and temperature (celsius, fahrenheit, kelvin). "
        "Use this for precise conversions instead of guessing."
    ),
    parameters=[
        ToolParameter(name="value", type=ToolParameterType.NUMBER, description="The numeric value to convert", required=True),
        ToolParameter(name="from_unit", type=ToolParameterType.STRING, description="Source unit (e.g. 'km', 'lb', 'celsius', 'mi')", required=True),
        ToolParameter(name="to_unit", type=ToolParameterType.STRING, description="Target unit (e.g. 'miles', 'kg', 'fahrenheit')", required=True),
    ],
    returns="object with converted value and units",
    category="utility",
)


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    from_unit = from_unit.lower().replace("°", "").strip()
    to_unit = to_unit.lower().replace("°", "").strip()

    celsius_map = {"c": "celsius", "celsius": "celsius", "f": "fahrenheit", "fahrenheit": "fahrenheit", "k": "kelvin", "kelvin": "kelvin"}
    from_norm = celsius_map.get(from_unit, from_unit)
    to_norm = celsius_map.get(to_unit, to_unit)

    if from_norm == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_norm == "kelvin":
        celsius = value - 273.15
    else:
        celsius = value

    if to_norm == "fahrenheit":
        return celsius * 9 / 5 + 32
    if to_norm == "kelvin":
        return celsius + 273.15
    return celsius


async def unit_converter_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    value = float(arguments["value"])
    from_unit = str(arguments["from_unit"]).lower().strip()
    to_unit = str(arguments["to_unit"]).lower().strip()

    temp_units = {"c", "celsius", "f", "fahrenheit", "k", "kelvin", "°c", "°f"}
    if from_unit in temp_units or to_unit in temp_units:
        result = _convert_temperature(value, from_unit, to_unit)
        return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": round(result, 4), "category": "temperature"}

    for unit_map, category in ((_LENGTH_TO_METERS, "length"), (_WEIGHT_TO_GRAMS, "weight"), (_VOLUME_TO_LITERS, "volume")):
        if from_unit in unit_map and to_unit in unit_map:
            base_value = value * unit_map[from_unit]
            result = base_value / unit_map[to_unit]
            return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": round(result, 6), "category": category}

    raise ValueError(f"Cannot convert between '{from_unit}' and '{to_unit}' — incompatible or unsupported units")
