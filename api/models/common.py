from typing import Literal


Decision = Literal["execute", "confirm", "reject"]
Confidence = Literal["high", "medium", "low"]
SlotType = Literal["string", "number", "integer", "boolean", "enum"]
TargetScope = Literal["equipment", "component"]
