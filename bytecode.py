import dis
import types
from typing import Any, Dict, List


class BytecodeGenerator:
    def __init__(self) -> None:
        self.bytecode: List[Dict[str, Any]] = []

    def generate(self, code: str) -> List[Dict[str, Any]]:
        """Generate a JSON-safe bytecode listing for the module and nested functions."""
        try:
            compiled_code = compile(code, "<string>", "exec")
            self.bytecode = []
            self._disassemble(compiled_code, scope_name="module", depth=0)
            return self.bytecode
        except SyntaxError as exc:
            return [
                {
                    "error": f"Syntax error: {str(exc)}",
                    "error_type": "BytecodeError",
                    "line": exc.lineno,
                    "column": exc.offset,
                }
            ]
        except Exception as exc:
            return [
                {
                    "error": f"Bytecode generation error: {str(exc)}",
                    "error_type": "BytecodeError",
                }
            ]

    def _disassemble(self, code_obj: types.CodeType, scope_name: str, depth: int) -> None:
        instructions = list(dis.get_instructions(code_obj))
        for index, instr in enumerate(instructions, start=1):
            positions = instr.positions if hasattr(instr, "positions") else None
            line_number = getattr(instr, "line_number", None)
            if line_number is None and positions is not None:
                line_number = getattr(positions, "lineno", None)
            if line_number is None:
                line_number = instr.starts_line

            self.bytecode.append(
                {
                    "scope": scope_name,
                    "depth": depth,
                    "index": index,
                    "offset": instr.offset,
                    "opcode": instr.opcode,
                    "opname": instr.opname,
                    "arg": instr.arg,
                    "argval": self._sanitize_value(instr.argval),
                    "argrepr": instr.argrepr,
                    "line": line_number,
                    "starts_line": instr.starts_line,
                    "is_jump_target": instr.is_jump_target,
                    "positions": self._serialize_positions(positions),
                    "category": self._categorize_instruction(instr.opname),
                }
            )

        for const in code_obj.co_consts:
            if isinstance(const, types.CodeType):
                nested_scope = f"{scope_name}.{const.co_name}" if scope_name != "module" else const.co_name
                self._disassemble(const, scope_name=nested_scope, depth=depth + 1)

    def _serialize_positions(self, positions: Any) -> Any:
        if positions is None:
            return None
        return {
            "lineno": getattr(positions, "lineno", None),
            "end_lineno": getattr(positions, "end_lineno", None),
            "col_offset": getattr(positions, "col_offset", None),
            "end_col_offset": getattr(positions, "end_col_offset", None),
        }

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, types.CodeType):
            return {
                "kind": "code_object",
                "name": value.co_name,
                "argcount": value.co_argcount,
                "nlocals": value.co_nlocals,
                "stacksize": value.co_stacksize,
            }
        if isinstance(value, tuple):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)

    def _categorize_instruction(self, opname: str) -> str:
        if opname.startswith(("LOAD_", "STORE_", "DELETE_")):
            return "Data Access"
        if opname.startswith(("POP_JUMP", "JUMP", "FOR_ITER")):
            return "Control Flow"
        if opname.startswith(("CALL", "PUSH_NULL", "PRECALL", "RETURN_")):
            return "Calls / Return"
        if opname.startswith(("COMPARE_", "IS_OP", "CONTAINS_OP")):
            return "Comparison"
        if opname.startswith(("BINARY_", "UNARY_", "INPLACE_")) or opname in {"BINARY_OP"}:
            return "Arithmetic"
        if opname.startswith(("MAKE_", "BUILD_", "FORMAT_", "LIST_", "DICT_", "SET_")):
            return "Object Construction"
        if opname.startswith(("RESUME", "CACHE", "NOP", "COPY", "SWAP")):
            return "VM / Stack"
        return "Other"
