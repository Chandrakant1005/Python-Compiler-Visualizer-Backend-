import ast
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SymbolEntry:
    name: str
    type: str
    scope: str
    line: int
    category: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "scope": self.scope,
            "line": self.line,
            "category": self.category,
        }


class SemanticAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.entries: Dict[Tuple[str, str], SymbolEntry] = {}
        self.scope_stack: List[str] = ["global"]
        self.function_globals: Dict[str, set[str]] = {}
        self.scope_order: List[Dict[str, Any]] = []

    def analyze(self, code: str) -> Dict[str, Any]:
        self.entries = {}
        self.scope_stack = ["global"]
        self.function_globals = {}
        self.scope_order = [{"name": "global", "display": "global", "level": 0}]

        try:
            tree = ast.parse(code)
            self.visit(tree)
            return self._build_response()
        except SyntaxError as exc:
            normalized_code = self._normalize_global_assignment_syntax(code)
            if normalized_code != code:
                try:
                    self.entries = {}
                    self.scope_stack = ["global"]
                    self.function_globals = {}
                    self.scope_order = [{"name": "global", "display": "global", "level": 0}]
                    tree = ast.parse(normalized_code)
                    self.visit(tree)
                    response = self._build_response()
                    response["normalization_note"] = "Interpreted 'global name = value' as 'global name; name = value' for symbol-table generation."
                    return response
                except SyntaxError:
                    pass

            return {
                "phase": "symbol_table",
                "error": f"Syntax error: {str(exc)}",
                "error_type": "SymbolTableError",
                "description": "The symbol table cannot be built because Python AST generation failed for this source.",
                "line": exc.lineno,
                "column": exc.offset,
            }

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        function_scope = self._current_scope()
        self._register_symbol(
            name=node.name,
            inferred_type="function",
            scope=function_scope,
            line=node.lineno,
            category="function",
        )

        local_scope_name = f"local ({node.name})"
        self.scope_order.append(
            {
                "name": node.name,
                "display": local_scope_name,
                "level": len(self.scope_stack),
            }
        )
        self.function_globals[node.name] = set()
        self.scope_stack.append(node.name)

        for arg in node.args.args:
            self._register_symbol(
                name=arg.arg,
                inferred_type="argument",
                scope=local_scope_name,
                line=getattr(arg, "lineno", node.lineno),
                category="parameter",
            )

        for statement in node.body:
            self.visit(statement)

        self.scope_stack.pop()
        return None

    def visit_Global(self, node: ast.Global) -> Any:
        current_function = self._current_scope()
        if current_function != "global":
            self.function_globals.setdefault(current_function, set()).update(node.names)
        return None

    def visit_Assign(self, node: ast.Assign) -> Any:
        inferred_type = self._infer_type(node.value)
        for target in node.targets:
            self._register_assignment_target(target, inferred_type, node.lineno)
        self.generic_visit(node.value)
        return None

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        inferred_type = self._annotation_to_type(node.annotation)
        self._register_assignment_target(node.target, inferred_type or "unknown", node.lineno)
        if node.value:
            self.visit(node.value)
        return None

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        inferred_type = self._infer_type(node.value)
        self._register_assignment_target(node.target, inferred_type, node.lineno)
        self.visit(node.value)
        return None

    def visit_For(self, node: ast.For) -> Any:
        self._register_assignment_target(node.target, "unknown", node.lineno)
        self.visit(node.iter)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)
        return None

    def _register_assignment_target(self, target: ast.AST, inferred_type: str, line: int) -> None:
        if isinstance(target, ast.Name):
            self._register_symbol(
                name=target.id,
                inferred_type=inferred_type,
                scope=self._display_scope_for_name(target.id),
                line=line,
                category="variable",
            )
            return

        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._register_assignment_target(element, inferred_type, line)

    def _register_symbol(self, name: str, inferred_type: str, scope: str, line: int, category: str) -> None:
        key = (scope, name)
        existing = self.entries.get(key)
        if existing is None:
            self.entries[key] = SymbolEntry(
                name=name,
                type=inferred_type,
                scope=scope,
                line=line,
                category=category,
            )
            return

        if existing.type == "unknown" and inferred_type != "unknown":
            existing.type = inferred_type
        if line < existing.line:
            existing.line = line

    def _current_scope(self) -> str:
        return self.scope_stack[-1]

    def _display_scope_for_name(self, name: str) -> str:
        current_scope = self._current_scope()
        if current_scope == "global":
            return "global"

        declared_globals = self.function_globals.get(current_scope, set())
        if name in declared_globals:
            return "global"

        return f"local ({current_scope})"

    def _annotation_to_type(self, annotation: ast.AST) -> Optional[str]:
        if isinstance(annotation, ast.Name):
            return annotation.id
        return None

    def _infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool):
                return "bool"
            if isinstance(value, int):
                return "int"
            if isinstance(value, float):
                return "float"
            if isinstance(value, str):
                return "string"
            if value is None:
                return "None"
            return type(value).__name__

        if isinstance(node, ast.Name):
            for scope in self._candidate_scopes_for_lookup(node.id):
                entry = self.entries.get((scope, node.id))
                if entry and entry.type != "unknown":
                    return entry.type
            return "unknown"

        if isinstance(node, ast.BinOp):
            left = self._infer_type(node.left)
            right = self._infer_type(node.right)
            if left == right and left in {"int", "float", "string"}:
                return left
            if {left, right} <= {"int", "float"}:
                return "float" if "float" in {left, right} else "int"
            return "unknown"

        if isinstance(node, ast.UnaryOp):
            return self._infer_type(node.operand)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in {"int", "float", "str", "bool"}:
                    return "string" if node.func.id == "str" else node.func.id
                if node.func.id == "print":
                    return "None"
            return "unknown"

        if isinstance(node, ast.Compare):
            return "bool"

        if isinstance(node, ast.List):
            return "list"

        if isinstance(node, ast.Tuple):
            return "tuple"

        return "unknown"

    def _candidate_scopes_for_lookup(self, name: str) -> List[str]:
        current_scope = self._current_scope()
        if current_scope == "global":
            return ["global"]

        local_scope = f"local ({current_scope})"
        declared_globals = self.function_globals.get(current_scope, set())
        if name in declared_globals:
            return ["global"]
        return [local_scope, "global"]

    def _build_response(self) -> Dict[str, Any]:
        rows = sorted(
            [entry.to_dict() for entry in self.entries.values()],
            key=lambda item: (item["scope"] != "global", item["scope"], item["line"], item["name"]),
        )

        return {
            "phase": "symbol_table",
            "entries": rows,
            "columns": ["name", "type", "scope"],
            "scope_hierarchy": self.scope_order,
            "summary": {
                "total_symbols": len(rows),
                "global_symbols": sum(1 for row in rows if row["scope"] == "global"),
                "local_symbols": sum(1 for row in rows if row["scope"] != "global"),
                "functions": sum(1 for row in rows if row["category"] == "function"),
            },
        }

    def _normalize_global_assignment_syntax(self, code: str) -> str:
        pattern = re.compile(r"^(\s*)global\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")
        normalized_lines: List[str] = []
        changed = False

        for line in code.splitlines():
            match = pattern.match(line)
            if not match:
                normalized_lines.append(line)
                continue

            indent, name, value = match.groups()
            normalized_lines.append(f"{indent}global {name}; {name} = {value}")
            changed = True

        if not changed:
            return code

        trailing_newline = "\n" if code.endswith("\n") else ""
        return "\n".join(normalized_lines) + trailing_newline
