import ast
import operator
from typing import List, Dict, Any, Union

class Optimizer:
    def __init__(self):
        self.optimizations_applied = []
    
    def optimize(self, code: str) -> Dict[str, Any]:
        """Apply optimizations to Python code"""
        try:
            original_tree = ast.parse(code)
            optimized_tree = self._apply_optimizations(original_tree)
            
            optimized_code = ast.unparse(optimized_tree) if hasattr(ast, 'unparse') else code
            
            return {
                'optimized_code': optimized_code,
                'optimizations_applied': self.optimizations_applied,
                'original_tree': self._ast_to_dict(original_tree),
                'optimized_tree': self._ast_to_dict(optimized_tree)
            }
        except SyntaxError as e:
            return {
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno
            }
    
    def _apply_optimizations(self, tree: ast.AST) -> ast.AST:
        """Apply all optimizations to the AST"""
        self.optimizations_applied = []
        
        # Apply constant folding
        tree = self._constant_folding(tree)
        
        # Apply dead code elimination
        tree = self._dead_code_elimination(tree)
        
        # Apply algebraic simplifications
        tree = self._algebraic_simplifications(tree)
        
        return tree
    
    def _constant_folding(self, node: ast.AST) -> ast.AST:
        """Apply constant folding optimization"""
        if isinstance(node, ast.BinOp):
            # Optimize left and right operands first
            left = self._constant_folding(node.left)
            right = self._constant_folding(node.right)
            
            # If both operands are constants, compute the result
            if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                try:
                    result = self._evaluate_binary_op(left.value, right.value, node.op)
                    if result is not None:
                        self.optimizations_applied.append({
                            'type': 'constant_folding',
                            'description': f'Folded {left.value} {self._get_op_symbol(node.op)} {right.value} to {result}',
                            'line': getattr(node, 'lineno', None)
                        })
                        return ast.Constant(value=result)
                except:
                    pass
            
            # Return node with optimized operands
            node.left = left
            node.right = right
            return node
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._constant_folding(node.operand)
            
            if isinstance(operand, ast.Constant):
                try:
                    result = self._evaluate_unary_op(operand.value, node.op)
                    if result is not None:
                        self.optimizations_applied.append({
                            'type': 'constant_folding',
                            'description': f'Folded {self._get_unary_op_symbol(node.op)}{operand.value} to {result}',
                            'line': getattr(node, 'lineno', None)
                        })
                        return ast.Constant(value=result)
                except:
                    pass
            
            node.operand = operand
            return node
        
        elif isinstance(node, ast.Compare):
            # Handle comparisons with constants
            left = self._constant_folding(node.left)
            new_comparators = []
            new_ops = []
            
            for op, comparator in zip(node.ops, node.comparators):
                right = self._constant_folding(comparator)
                
                if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                    try:
                        result = self._evaluate_compare_op(left.value, right.value, op)
                        if result is not None:
                            self.optimizations_applied.append({
                                'type': 'constant_folding',
                                'description': f'Folded {left.value} {self._get_compare_symbol(op)} {right.value} to {result}',
                                'line': getattr(node, 'lineno', None)
                            })
                            left = ast.Constant(value=result)
                        else:
                            new_comparators.append(right)
                            new_ops.append(op)
                    except:
                        new_comparators.append(right)
                        new_ops.append(op)
                else:
                    new_comparators.append(right)
                    new_ops.append(op)
                    left = right
            
            if new_ops:
                node.left = left
                node.ops = new_ops
                node.comparators = new_comparators
                return node
            else:
                return left
        
        # Handle other node types
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.AST):
                        new_list.append(self._constant_folding(item))
                    else:
                        new_list.append(item)
                setattr(node, field, new_list)
            elif isinstance(value, ast.AST):
                setattr(node, field, self._constant_folding(value))
        
        return node
    
    def _dead_code_elimination(self, node: ast.AST) -> ast.AST:
        """Apply dead code elimination"""
        if isinstance(node, ast.If):
            # Check if condition is a constant
            if isinstance(node.test, ast.Constant):
                if bool(node.test.value):
                    # Keep only the then block
                    self.optimizations_applied.append({
                        'type': 'dead_code_elimination',
                        'description': 'Removed unreachable else block (condition always true)',
                        'line': getattr(node, 'lineno', None)
                    })
                    return ast.Expr(value=ast.Constant(value=None)) if not node.body else node.body[0] if len(node.body) == 1 else ast.If(test=node.test, body=node.body, orelse=[])
                else:
                    # Keep only the else block
                    self.optimizations_applied.append({
                        'type': 'dead_code_elimination',
                        'description': 'Removed unreachable if block (condition always false)',
                        'line': getattr(node, 'lineno', None)
                    })
                    return ast.Expr(value=ast.Constant(value=None)) if not node.orelse else node.orelse[0] if len(node.orelse) == 1 else ast.If(test=node.test, body=[], orelse=node.orelse)
        
        elif isinstance(node, ast.While):
            # Check if condition is a constant
            if isinstance(node.test, ast.Constant):
                if not bool(node.test.value):
                    # Remove the entire while loop
                    self.optimizations_applied.append({
                        'type': 'dead_code_elimination',
                        'description': 'Removed unreachable while loop (condition always false)',
                        'line': getattr(node, 'lineno', None)
                    })
                    return ast.Expr(value=ast.Constant(value=None))
        
        # Handle other node types
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.AST):
                        optimized = self._dead_code_elimination(item)
                        if not (isinstance(optimized, ast.Expr) and isinstance(optimized.value, ast.Constant) and optimized.value.value is None):
                            new_list.append(optimized)
                    else:
                        new_list.append(item)
                setattr(node, field, new_list)
            elif isinstance(value, ast.AST):
                setattr(node, field, self._dead_code_elimination(value))
        
        return node
    
    def _algebraic_simplifications(self, node: ast.AST) -> ast.AST:
        """Apply algebraic simplifications"""
        if isinstance(node, ast.BinOp):
            left = self._algebraic_simplifications(node.left)
            right = self._algebraic_simplifications(node.right)
            
            # Simplify x + 0 -> x
            if isinstance(node.op, ast.Add) and isinstance(right, ast.Constant) and right.value == 0:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified x + 0 to x',
                    'line': getattr(node, 'lineno', None)
                })
                return left
            
            # Simplify 0 + x -> x
            if isinstance(node.op, ast.Add) and isinstance(left, ast.Constant) and left.value == 0:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified 0 + x to x',
                    'line': getattr(node, 'lineno', None)
                })
                return right
            
            # Simplify x * 1 -> x
            if isinstance(node.op, ast.Mult) and isinstance(right, ast.Constant) and right.value == 1:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified x * 1 to x',
                    'line': getattr(node, 'lineno', None)
                })
                return left
            
            # Simplify 1 * x -> x
            if isinstance(node.op, ast.Mult) and isinstance(left, ast.Constant) and left.value == 1:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified 1 * x to x',
                    'line': getattr(node, 'lineno', None)
                })
                return right
            
            # Simplify x * 0 -> 0
            if isinstance(node.op, ast.Mult) and isinstance(right, ast.Constant) and right.value == 0:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified x * 0 to 0',
                    'line': getattr(node, 'lineno', None)
                })
                return ast.Constant(value=0)
            
            # Simplify 0 * x -> 0
            if isinstance(node.op, ast.Mult) and isinstance(left, ast.Constant) and left.value == 0:
                self.optimizations_applied.append({
                    'type': 'algebraic_simplification',
                    'description': 'Simplified 0 * x to 0',
                    'line': getattr(node, 'lineno', None)
                })
                return ast.Constant(value=0)
            
            node.left = left
            node.right = right
            return node
        
        # Handle other node types
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.AST):
                        new_list.append(self._algebraic_simplifications(item))
                    else:
                        new_list.append(item)
                setattr(node, field, new_list)
            elif isinstance(value, ast.AST):
                setattr(node, field, self._algebraic_simplifications(value))
        
        return node
    
    def _evaluate_binary_op(self, left: Any, right: Any, op: ast.operator) -> Any:
        """Evaluate binary operation with constant operands"""
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.LShift: operator.lshift,
            ast.RShift: operator.rshift,
            ast.BitOr: operator.or_,
            ast.BitXor: operator.xor,
            ast.BitAnd: operator.and_,
        }
        
        op_func = ops.get(type(op))
        if op_func:
            try:
                return op_func(left, right)
            except:
                return None
        return None
    
    def _evaluate_unary_op(self, operand: Any, op: ast.unaryop) -> Any:
        """Evaluate unary operation with constant operand"""
        ops = {
            ast.UAdd: operator.pos,
            ast.USub: operator.neg,
            ast.Not: operator.not_,
            ast.Invert: operator.invert,
        }
        
        op_func = ops.get(type(op))
        if op_func:
            try:
                return op_func(operand)
            except:
                return None
        return None
    
    def _evaluate_compare_op(self, left: Any, right: Any, op: ast.cmpop) -> Any:
        """Evaluate comparison operation with constant operands"""
        ops = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
        }
        
        op_func = ops.get(type(op))
        if op_func:
            try:
                return op_func(left, right)
            except:
                return None
        return None
    
    def _get_op_symbol(self, op: ast.operator) -> str:
        """Get string symbol for binary operator"""
        symbols = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '//',
            ast.Mod: '%',
            ast.Pow: '**',
            ast.LShift: '<<',
            ast.RShift: '>>',
            ast.BitOr: '|',
            ast.BitXor: '^',
            ast.BitAnd: '&',
        }
        return symbols.get(type(op), '?')
    
    def _get_unary_op_symbol(self, op: ast.unaryop) -> str:
        """Get string symbol for unary operator"""
        symbols = {
            ast.UAdd: '+',
            ast.USub: '-',
            ast.Not: 'not',
            ast.Invert: '~',
        }
        return symbols.get(type(op), '?')
    
    def _get_compare_symbol(self, op: ast.cmpop) -> str:
        """Get string symbol for comparison operator"""
        symbols = {
            ast.Eq: '==',
            ast.NotEq: '!=',
            ast.Lt: '<',
            ast.LtE: '<=',
            ast.Gt: '>',
            ast.GtE: '>=',
            ast.Is: 'is',
            ast.IsNot: 'is not',
            ast.In: 'in',
            ast.NotIn: 'not in',
        }
        return symbols.get(type(op), '?')
    
    def _ast_to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """Convert AST node to dictionary representation"""
        result = {
            'type': node.__class__.__name__,
            'attributes': {}
        }
        
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                result['attributes'][field] = self._ast_to_dict(value)
            elif isinstance(value, list):
                result['attributes'][field] = [self._ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
            else:
                result['attributes'][field] = value
        
        if hasattr(node, 'lineno'):
            result['line'] = node.lineno
        if hasattr(node, 'col_offset'):
            result['column'] = node.col_offset
            
        return result
