import ast
from typing import Any, Dict, List, Optional


class IRGenerator:
    def __init__(self) -> None:
        self.instructions: List[Dict[str, Any]] = []
        self.temp_counter = 0
        self.label_counter = 0

    def generate(self, code: str) -> List[Dict[str, Any]]:
        """Generate numbered three-address code."""
        try:
            tree = ast.parse(code)
            self.instructions = []
            self.temp_counter = 0
            self.label_counter = 0

            for node in tree.body:
                self._emit_statement(node)

            self._emit("EOF", kind="end")
            self._resolve_labels()
            return self.instructions
        except SyntaxError as exc:
            return [
                {
                    "error": f"Syntax error: {str(exc)}",
                    "error_type": "IRError",
                    "line": exc.lineno,
                    "column": exc.offset,
                }
            ]

    def _emit_statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Assign):
            value = self._emit_expression(node.value)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._emit(f"{target.id} = {value}", kind="assign")
            return

        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            right = self._emit_expression(node.value)
            op = self._binary_symbol(node.op)
            self._emit(f"{node.target.id} = {node.target.id} {op} {right}", kind="assign")
            return

        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                self._emit_call(node.value, discard_result=True)
            else:
                self._emit_expression(node.value)
            return

        if isinstance(node, ast.If):
            self._emit_if(node)
            return

        if isinstance(node, ast.While):
            self._emit_while(node)
            return

        if isinstance(node, ast.For):
            self._emit_for(node)
            return

        if isinstance(node, ast.FunctionDef):
            self._emit_function(node)
            return

        if isinstance(node, ast.Return):
            value = self._emit_expression(node.value) if node.value else "None"
            self._emit(f"return {value}", kind="return")
            return

        if isinstance(node, ast.Global):
            return

    def _emit_if(self, node: ast.If) -> None:
        then_label = self._new_label()
        end_label = self._new_label()
        test_text = self._emit_condition_text(node.test)

        self._emit(f"if {test_text} goto {then_label}", kind="branch_true", branch_label=then_label, branch_mode="true")

        if node.orelse:
            for statement in node.orelse:
                self._emit_statement(statement)
            self._emit(f"goto {end_label}", kind="goto", branch_label=end_label)
        else:
            self._emit(f"goto {end_label}", kind="goto", branch_label=end_label)

        self._mark_label(then_label)

        for statement in node.body:
            self._emit_statement(statement)

        self._mark_label(end_label)

    def _emit_while(self, node: ast.While) -> None:
        start_label = self._new_label()
        exit_label = self._new_label()
        self._mark_label(start_label)
        test_text = self._emit_condition_text(node.test)
        self._emit(f"ifFalse {test_text} goto {exit_label}", kind="branch_false", branch_label=exit_label, branch_mode="false")
        for statement in node.body:
            self._emit_statement(statement)
        self._emit(f"goto {start_label}", kind="goto", branch_label=start_label)
        self._mark_label(exit_label)

    def _emit_for(self, node: ast.For) -> None:
        if not isinstance(node.target, ast.Name):
            return

        iterable = self._emit_expression(node.iter)
        start_label = self._new_label()
        exit_label = self._new_label()
        self._emit(f"{node.target.id} = 0", kind="assign")
        self._mark_label(start_label)
        self._emit(
            f"if {node.target.id} >= {iterable} goto {exit_label}",
            kind="branch_true",
            branch_label=exit_label,
            branch_mode="true",
        )
        for statement in node.body:
            self._emit_statement(statement)
        temp = self._new_temp()
        self._emit(f"{temp} = {node.target.id} + 1", kind="temp")
        self._emit(f"{node.target.id} = {temp}", kind="assign")
        self._emit(f"goto {start_label}", kind="goto", branch_label=start_label)
        self._mark_label(exit_label)

    def _emit_function(self, node: ast.FunctionDef) -> None:
        self._emit(f"func {node.name} begin", kind="function")
        for arg in node.args.args:
            self._emit(f"arg {arg.arg}", kind="argument")
        for statement in node.body:
            self._emit_statement(statement)
        self._emit(f"func {node.name} end", kind="function")

    def _emit_expression(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return repr(node.value)
            return str(node.value)

        if isinstance(node, ast.UnaryOp):
            operand = self._emit_expression(node.operand)
            if isinstance(node.op, ast.USub):
                temp = self._new_temp()
                self._emit(f"{temp} = -{operand}", kind="temp")
                return temp
            if isinstance(node.op, ast.Not):
                temp = self._new_temp()
                self._emit(f"{temp} = not {operand}", kind="temp")
                return temp

        if isinstance(node, ast.BinOp):
            left = self._emit_expression(node.left)
            right = self._emit_expression(node.right)
            temp = self._new_temp()
            self._emit(f"{temp} = {left} {self._binary_symbol(node.op)} {right}", kind="temp")
            return temp

        if isinstance(node, ast.Compare):
            left = self._emit_expression(node.left)
            right = self._emit_expression(node.comparators[0])
            temp = self._new_temp()
            self._emit(f"{temp} = {left} {self._compare_symbol(node.ops[0])} {right}", kind="temp")
            return temp

        if isinstance(node, ast.Call):
            return self._emit_call(node)

        return "?"

    def _emit_call(self, node: ast.Call, discard_result: bool = False) -> str:
        func_name = node.func.id if isinstance(node.func, ast.Name) else "func"
        rendered_args = [self._emit_expression(arg) for arg in node.args]
        if func_name == "print":
            for arg in rendered_args:
                self._emit(f"print {arg}", kind="print")
            return "None"

        for arg in rendered_args:
            self._emit(f"param {arg}", kind="param")

        if discard_result:
            self._emit(f"call {func_name}, {len(rendered_args)}", kind="call")
            return "None"

        temp = self._new_temp()
        self._emit(f"{temp} = call {func_name}, {len(rendered_args)}", kind="call")
        return temp

    def _emit_condition_text(self, node: ast.AST) -> str:
        if isinstance(node, ast.Compare):
            left = self._emit_expression(node.left)
            right = self._emit_expression(node.comparators[0])
            return f"{left} {self._compare_symbol(node.ops[0])} {right}"

        value = self._emit_expression(node)
        return f"{value} == False"

    def _emit(self, text: str, kind: str, branch_label: Optional[str] = None, branch_mode: Optional[str] = None) -> None:
        self.instructions.append(
            {
                "line": len(self.instructions) + 1,
                "text": text,
                "kind": kind,
                "branch_label": branch_label,
                "branch_mode": branch_mode,
            }
        )

    def _mark_label(self, label: str) -> None:
        self.instructions.append(
            {
                "line": len(self.instructions) + 1,
                "text": f"{label}:",
                "kind": "label",
                "label": label,
            }
        )

    def _resolve_labels(self) -> None:
        label_map = {item["label"]: item["line"] for item in self.instructions if item.get("label")}
        filtered: List[Dict[str, Any]] = []

        for instruction in self.instructions:
            text = instruction["text"]
            label = instruction.get("branch_label")
            if label and label in label_map:
                target_line = label_map[label]
                text = text.replace(label, str(target_line))
            if instruction["kind"] == "label":
                continue
            filtered.append(
                {
                    "line": len(filtered) + 1,
                    "text": text,
                    "kind": instruction["kind"],
                }
            )

        self.instructions = filtered

    def _new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def _new_label(self) -> str:
        self.label_counter += 1
        return f"L{self.label_counter}"

    def _binary_symbol(self, operator: ast.operator) -> str:
        mapping = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
        }
        for node_type, symbol in mapping.items():
            if isinstance(operator, node_type):
                return symbol
        return "?"

    def _compare_symbol(self, operator: ast.cmpop) -> str:
        mapping = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        for node_type, symbol in mapping.items():
            if isinstance(operator, node_type):
                return symbol
        return "?"
