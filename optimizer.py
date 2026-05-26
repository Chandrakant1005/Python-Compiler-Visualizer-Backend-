import ast
import copy
import operator
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


TECHNIQUES = [
    "Constant Folding",
    "Constant Propagation",
    "Copy Propagation",
    "Common Subexpression Elimination (CSE)",
    "Dead Code Elimination",
    "Dead Store Elimination",
    "Strength Reduction",
    "Algebraic Simplification",
    "Loop Invariant Code Motion",
    "Loop Unrolling",
    "Loop Fusion",
    "Loop Fission (Loop Distribution)",
    "Induction Variable Elimination",
    "Code Motion",
]


@dataclass
class OptimizationEvent:
    technique: str
    description: str
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technique": self.technique,
            "description": self.description,
            "line": self.line,
        }


class Optimizer:
    def __init__(self) -> None:
        self.events: List[OptimizationEvent] = []

    def optimize(self, code: str) -> Dict[str, Any]:
        try:
            original_tree = ast.parse(code)
            optimized_tree = copy.deepcopy(original_tree)
            self.events = []

            optimized_tree = ConstantFolder(self.events).visit(optimized_tree)
            optimized_tree = AlgebraicSimplifier(self.events).visit(optimized_tree)
            optimized_tree = StrengthReducer(self.events).visit(optimized_tree)
            optimized_tree = BlockOptimizer(self.events).visit(optimized_tree)
            optimized_tree = DeadCodeEliminator(self.events).visit(optimized_tree)
            optimized_tree = LoopOptimizer(self.events).visit(optimized_tree)
            ast.fix_missing_locations(optimized_tree)

            optimized_code = ast.unparse(optimized_tree) if hasattr(ast, "unparse") else code
            original_code = ast.unparse(original_tree) if hasattr(ast, "unparse") else code

            used = {event.technique for event in self.events}
            technique_status = [
                {
                    "name": technique,
                    "used": technique in used,
                }
                for technique in TECHNIQUES
            ]

            return {
                "original_code": original_code,
                "optimized_code": optimized_code,
                "optimizations_applied": [event.to_dict() for event in self.events],
                "technique_status": technique_status,
                "summary": {
                    "applied_count": len(self.events),
                    "used_techniques": len(used),
                    "original_lines": len(original_code.splitlines()),
                    "optimized_lines": len(optimized_code.splitlines()),
                },
            }
        except SyntaxError as exc:
            return {
                "error": f"Syntax error: {str(exc)}",
                "error_type": "OptimizationError",
                "line": exc.lineno,
                "column": exc.offset,
            }


class ConstantFolder(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            result = eval_binary(node.left.value, node.right.value, node.op)
            if result is not None:
                self.events.append(
                    OptimizationEvent(
                        "Constant Folding",
                        f"Folded {render_const(node.left.value)} {op_symbol(node.op)} {render_const(node.right.value)} to {render_const(result)}",
                        getattr(node, "lineno", None),
                    )
                )
                return ast.copy_location(ast.Constant(value=result), node)
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.operand, ast.Constant):
            result = eval_unary(node.operand.value, node.op)
            if result is not None:
                self.events.append(
                    OptimizationEvent(
                        "Constant Folding",
                        f"Folded {unary_symbol(node.op)}{render_const(node.operand.value)} to {render_const(result)}",
                        getattr(node, "lineno", None),
                    )
                )
                return ast.copy_location(ast.Constant(value=result), node)
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) == 1 and len(node.comparators) == 1:
            if isinstance(node.left, ast.Constant) and isinstance(node.comparators[0], ast.Constant):
                result = eval_compare(node.left.value, node.comparators[0].value, node.ops[0])
                if result is not None:
                    self.events.append(
                        OptimizationEvent(
                            "Constant Folding",
                            f"Folded {render_const(node.left.value)} {compare_symbol(node.ops[0])} {render_const(node.comparators[0].value)} to {render_const(result)}",
                            getattr(node, "lineno", None),
                        )
                    )
                    return ast.copy_location(ast.Constant(value=result), node)
        return node


class AlgebraicSimplifier(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)

        if isinstance(node.op, ast.Add):
            if is_const_value(node.right, 0):
                self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified x + 0 to x", getattr(node, "lineno", None)))
                return node.left
            if is_const_value(node.left, 0):
                self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified 0 + x to x", getattr(node, "lineno", None)))
                return node.right

        if isinstance(node.op, ast.Sub) and is_const_value(node.right, 0):
            self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified x - 0 to x", getattr(node, "lineno", None)))
            return node.left

        if isinstance(node.op, ast.Mult):
            if is_const_value(node.right, 1):
                self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified x * 1 to x", getattr(node, "lineno", None)))
                return node.left
            if is_const_value(node.left, 1):
                self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified 1 * x to x", getattr(node, "lineno", None)))
                return node.right
            if is_const_value(node.right, 0) or is_const_value(node.left, 0):
                self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified multiplication by 0", getattr(node, "lineno", None)))
                return ast.copy_location(ast.Constant(value=0), node)

        if isinstance(node.op, ast.Div) and is_const_value(node.right, 1):
            self.events.append(OptimizationEvent("Algebraic Simplification", "Simplified x / 1 to x", getattr(node, "lineno", None)))
            return node.left

        return node


class StrengthReducer(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Mult):
            if is_const_value(node.right, 2):
                self.events.append(OptimizationEvent("Strength Reduction", "Replaced x * 2 with x + x", getattr(node, "lineno", None)))
                return ast.copy_location(ast.BinOp(left=node.left, op=ast.Add(), right=copy.deepcopy(node.left)), node)
            if is_const_value(node.left, 2):
                self.events.append(OptimizationEvent("Strength Reduction", "Replaced 2 * x with x + x", getattr(node, "lineno", None)))
                return ast.copy_location(ast.BinOp(left=node.right, op=ast.Add(), right=copy.deepcopy(node.right)), node)
        return node


class BlockOptimizer(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_Module(self, node: ast.Module) -> ast.AST:
        node.body = self._optimize_block(node.body, allow_dead_store=True)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.body = self._optimize_block(node.body, allow_dead_store=True)
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        node.test = self.visit(node.test)
        node.body = self._optimize_block(node.body, allow_dead_store=False)
        node.orelse = self._optimize_block(node.orelse, allow_dead_store=False)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        node.test = self.visit(node.test)
        node.body = self._optimize_block(node.body, allow_dead_store=False)
        node.orelse = self._optimize_block(node.orelse, allow_dead_store=False)
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        node.iter = self.visit(node.iter)
        node.body = self._optimize_block(node.body, allow_dead_store=False)
        node.orelse = self._optimize_block(node.orelse, allow_dead_store=False)
        return node

    def _optimize_block(self, statements: List[ast.stmt], allow_dead_store: bool) -> List[ast.stmt]:
        statements = [self.visit(copy.deepcopy(stmt)) for stmt in statements]
        statements = [stmt for stmt in statements if stmt is not None]
        statements = self._propagate_constants(statements)
        statements = self._propagate_copies(statements)
        statements = self._eliminate_common_subexpressions(statements)
        if allow_dead_store:
            statements = self._eliminate_dead_stores(statements)
        return statements

    def _propagate_constants(self, statements: List[ast.stmt]) -> List[ast.stmt]:
        env: Dict[str, ast.Constant] = {}
        result: List[ast.stmt] = []
        for stmt in statements:
            replacer = NameReplacer({name: const for name, const in env.items()})
            stmt = replacer.visit(stmt)
            if replacer.replaced:
                self.events.append(
                    OptimizationEvent(
                        "Constant Propagation",
                        f"Propagated constant value into line {getattr(stmt, 'lineno', '?')}",
                        getattr(stmt, "lineno", None),
                    )
                )

            assigned = assigned_names(stmt)
            for name in assigned:
                env.pop(name, None)

            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                if isinstance(stmt.value, ast.Constant):
                    env[stmt.targets[0].id] = stmt.value
                else:
                    env.pop(stmt.targets[0].id, None)

            result.append(stmt)
        return result

    def _propagate_copies(self, statements: List[ast.stmt]) -> List[ast.stmt]:
        env: Dict[str, str] = {}
        result: List[ast.stmt] = []
        for stmt in statements:
            replacer = CopyReplacer(env)
            stmt = replacer.visit(stmt)
            if replacer.replaced:
                self.events.append(
                    OptimizationEvent(
                        "Copy Propagation",
                        f"Propagated copied variable into line {getattr(stmt, 'lineno', '?')}",
                        getattr(stmt, "lineno", None),
                    )
                )

            assigned = assigned_names(stmt)
            for name in assigned:
                env.pop(name, None)
                env = {k: v for k, v in env.items() if v != name}

            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Name):
                env[stmt.targets[0].id] = stmt.value.id

            result.append(stmt)
        return result

    def _eliminate_common_subexpressions(self, statements: List[ast.stmt]) -> List[ast.stmt]:
        available: Dict[str, Tuple[str, Set[str]]] = {}
        result: List[ast.stmt] = []
        for stmt in statements:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target = stmt.targets[0].id
                key = expression_key(stmt.value)
                deps = expr_names(stmt.value)
                if key and key in available and not (deps & {target}):
                    source, source_deps = available[key]
                    stmt.value = ast.copy_location(ast.Name(id=source, ctx=ast.Load()), stmt.value)
                    self.events.append(
                        OptimizationEvent(
                            "Common Subexpression Elimination (CSE)",
                            f"Reused previously computed expression for {target}",
                            getattr(stmt, "lineno", None),
                        )
                    )
                else:
                    if key:
                        available[key] = (target, deps)

                modified = {target}
                available = {
                    expr: data for expr, data in available.items() if not (data[1] & modified or expr_depends_on_name(expr, modified))
                }
            else:
                modified = assigned_names(stmt)
                if modified:
                    available = {
                        expr: data for expr, data in available.items() if not (data[1] & modified or expr_depends_on_name(expr, modified))
                    }

            result.append(stmt)
        return result

    def _eliminate_dead_stores(self, statements: List[ast.stmt]) -> List[ast.stmt]:
        live: Set[str] = set()
        kept: List[ast.stmt] = []
        for stmt in reversed(statements):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target = stmt.targets[0].id
                if target not in live and is_pure_expression(stmt.value):
                    self.events.append(
                        OptimizationEvent(
                            "Dead Store Elimination",
                            f"Removed store to {target} because its value was never read",
                            getattr(stmt, "lineno", None),
                        )
                    )
                    continue
                live.discard(target)
                live |= expr_names(stmt.value)
            else:
                live |= used_names(stmt)
            kept.append(stmt)
        kept.reverse()
        return kept


class DeadCodeEliminator(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_Module(self, node: ast.Module) -> ast.AST:
        node.body = self._trim_after_terminator([self.visit(stmt) for stmt in node.body])
        node.body = [stmt for stmt in node.body if stmt is not None]
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.body = self._trim_after_terminator([self.visit(stmt) for stmt in node.body])
        node.body = [stmt for stmt in node.body if stmt is not None]
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant):
            if bool(node.test.value):
                self.events.append(OptimizationEvent("Dead Code Elimination", "Removed unreachable else branch", getattr(node, "lineno", None)))
                return node.body
            self.events.append(OptimizationEvent("Dead Code Elimination", "Removed unreachable if branch", getattr(node, "lineno", None)))
            return node.orelse
        return node

    def visit_While(self, node: ast.While) -> Optional[ast.AST]:
        self.generic_visit(node)
        if isinstance(node.test, ast.Constant) and not bool(node.test.value):
            self.events.append(OptimizationEvent("Dead Code Elimination", "Removed while loop with constant false condition", getattr(node, "lineno", None)))
            return None
        return node

    def _trim_after_terminator(self, statements: List[Optional[ast.stmt]]) -> List[ast.stmt]:
        result: List[ast.stmt] = []
        terminated = False
        for stmt in statements:
            if stmt is None:
                continue
            if terminated:
                self.events.append(OptimizationEvent("Dead Code Elimination", "Removed unreachable statement after control transfer", getattr(stmt, "lineno", None)))
                continue
            result.append(stmt)
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True
        return result


class LoopOptimizer(ast.NodeTransformer):
    def __init__(self, events: List[OptimizationEvent]) -> None:
        self.events = events

    def visit_For(self, node: ast.For) -> ast.AST:
        self.generic_visit(node)
        moved = self._move_invariants(node)
        if isinstance(moved, list):
            prefix = moved[:-1]
            loop_node = moved[-1]
            unrolled = self._unroll_loop(loop_node) if isinstance(loop_node, ast.For) else loop_node
            if isinstance(unrolled, list):
                return prefix + unrolled
            return prefix + [unrolled]
        return self._unroll_loop(moved)

    def visit_While(self, node: ast.While) -> ast.AST:
        self.generic_visit(node)
        return self._move_invariants(node)

    def _move_invariants(self, node: ast.AST) -> ast.AST:
        if not isinstance(node, (ast.For, ast.While)):
            return node

        loop_assigned = set()
        for stmt in node.body:
            loop_assigned |= assigned_names(stmt)

        movable: List[ast.stmt] = []
        remaining: List[ast.stmt] = []
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and is_pure_expression(stmt.value)
            ):
                deps = expr_names(stmt.value)
                if not (deps & loop_assigned):
                    movable.append(stmt)
                    self.events.append(
                        OptimizationEvent(
                            "Loop Invariant Code Motion",
                            f"Moved invariant assignment to {stmt.targets[0].id} outside the loop",
                            getattr(stmt, "lineno", None),
                        )
                    )
                    self.events.append(
                        OptimizationEvent(
                            "Code Motion",
                            f"Moved code for {stmt.targets[0].id} to a safer earlier position",
                            getattr(stmt, "lineno", None),
                        )
                    )
                    continue
            remaining.append(stmt)

        if movable:
            node.body = remaining
            return movable + [node]
        return node

    def _unroll_loop(self, node: ast.For) -> ast.AST:
        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and len(node.iter.args) == 1
            and isinstance(node.iter.args[0], ast.Constant)
            and isinstance(node.iter.args[0].value, int)
            and 0 <= node.iter.args[0].value <= 4
            and isinstance(node.target, ast.Name)
        ):
            count = node.iter.args[0].value
            unrolled: List[ast.stmt] = []
            for value in range(count):
                body_copy = [copy.deepcopy(stmt) for stmt in node.body]
                replacer = NameReplacer({node.target.id: ast.Constant(value=value)})
                body_copy = [replacer.visit(stmt) for stmt in body_copy]
                unrolled.extend(body_copy)
            self.events.append(
                OptimizationEvent(
                    "Loop Unrolling",
                    f"Unrolled range loop with {count} iterations",
                    getattr(node, "lineno", None),
                )
            )
            return unrolled
        return node


class NameReplacer(ast.NodeTransformer):
    def __init__(self, replacements: Dict[str, ast.AST]) -> None:
        self.replacements = replacements
        self.replaced = False

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.replacements:
            self.replaced = True
            return ast.copy_location(copy.deepcopy(self.replacements[node.id]), node)
        return node


class CopyReplacer(ast.NodeTransformer):
    def __init__(self, replacements: Dict[str, str]) -> None:
        self.replacements = replacements
        self.replaced = False

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.replacements:
            self.replaced = True
            return ast.copy_location(ast.Name(id=self.replacements[node.id], ctx=ast.Load()), node)
        return node


def op_symbol(op: ast.operator) -> str:
    return {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.Mod: "%",
    }.get(type(op), "?")


def unary_symbol(op: ast.unaryop) -> str:
    return {
        ast.USub: "-",
        ast.UAdd: "+",
        ast.Not: "not ",
    }.get(type(op), "")


def compare_symbol(op: ast.cmpop) -> str:
    return {
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
    }.get(type(op), "?")


def eval_binary(left: Any, right: Any, op: ast.operator) -> Any:
    func = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }.get(type(op))
    if not func:
        return None
    try:
        return func(left, right)
    except Exception:
        return None


def eval_unary(value: Any, op: ast.unaryop) -> Any:
    func = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
    }.get(type(op))
    if not func:
        return None
    try:
        return func(value)
    except Exception:
        return None


def eval_compare(left: Any, right: Any, op: ast.cmpop) -> Any:
    func = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }.get(type(op))
    if not func:
        return None
    try:
        return func(left, right)
    except Exception:
        return None


def is_const_value(node: ast.AST, value: Any) -> bool:
    return isinstance(node, ast.Constant) and node.value == value


def render_const(value: Any) -> str:
    return repr(value) if isinstance(value, str) else str(value)


def assigned_names(node: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
    return names


def used_names(node: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            names.add(child.id)
    return names


def expr_names(node: ast.AST) -> Set[str]:
    return used_names(node)


def is_pure_expression(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            return False
    return isinstance(node, (ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Tuple, ast.List))


def expression_key(node: ast.AST) -> Optional[str]:
    if not is_pure_expression(node):
        return None
    if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare)):
        return ast.dump(node, annotate_fields=False, include_attributes=False)
    return None


def expr_depends_on_name(key: str, modified: Set[str]) -> bool:
    return any(name in key for name in modified)
