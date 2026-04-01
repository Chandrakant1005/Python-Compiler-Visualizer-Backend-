import ast
from typing import List, Dict, Any

class IRGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0
    
    def generate(self, code: str) -> List[Dict[str, Any]]:
        """Generate Three Address Code from Python code"""
        try:
            tree = ast.parse(code)
            self.instructions = []
            self.temp_counter = 0
            self.label_counter = 0
            
            for node in tree.body:
                self._generate_node(node)
            
            return self.instructions
        except SyntaxError as e:
            return [{'error': f'Syntax error: {str(e)}', 'line': e.lineno}]
    
    def _new_temp(self) -> str:
        """Generate a new temporary variable"""
        self.temp_counter += 1
        return f"t{self.temp_counter}"
    
    def _new_label(self) -> str:
        """Generate a new label"""
        self.label_counter += 1
        return f"L{self.label_counter}"
    
    def _generate_node(self, node: ast.AST) -> str:
        """Generate IR for an AST node and return the result variable"""
        if isinstance(node, ast.Assign):
            result = self._generate_node(node.value)
            
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._add_instruction('assign', result, target.id)
                elif isinstance(target, ast.Tuple):
                    # Handle tuple unpacking (simplified)
                    for i, elt in enumerate(target.elts):
                        if isinstance(elt, ast.Name):
                            self._add_instruction('assign', f"{result}[{i}]", elt.id)
            
            return result
        
        elif isinstance(node, ast.AugAssign):
            # Handle augmented assignments (x += 1)
            result = self._generate_node(node.value)
            temp = self._new_temp()
            self._add_instruction('binary', node.target.id, result, temp, '+=')
            self._add_instruction('assign', temp, node.target.id)
            return node.target.id
        
        elif isinstance(node, ast.BinOp):
            left = self._generate_node(node.left)
            right = self._generate_node(node.right)
            temp = self._new_temp()
            
            op = self._get_operator(node.op)
            self._add_instruction('binary', left, right, temp, op)
            return temp
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._generate_node(node.operand)
            temp = self._new_temp()
            
            op = self._get_unary_operator(node.op)
            self._add_instruction('unary', operand, temp, op)
            return temp
        
        elif isinstance(node, ast.Compare):
            left = self._generate_node(node.left)
            result = self._new_temp()
            
            if len(node.ops) == 1 and len(node.comparators) == 1:
                right = self._generate_node(node.comparators[0])
                op = self._get_comparison_operator(node.ops[0])
                self._add_instruction('compare', left, right, result, op)
            else:
                # Handle chained comparisons (simplified)
                for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
                    right = self._generate_node(comparator)
                    temp_result = self._new_temp()
                    comp_op = self._get_comparison_operator(op)
                    self._add_instruction('compare', left, right, temp_result, comp_op)
                    
                    if i == 0:
                        self._add_instruction('assign', temp_result, result)
                        left = temp_result
                    else:
                        temp_and = self._new_temp()
                        self._add_instruction('binary', result, temp_result, temp_and, 'and')
                        self._add_instruction('assign', temp_and, result)
                        left = temp_result
            
            return result
        
        elif isinstance(node, ast.Name):
            return node.id
        
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        
        elif isinstance(node, ast.Num):  # For older Python versions
            return str(node.n)
        
        elif isinstance(node, ast.Str):  # For older Python versions
            return repr(node.s)
        
        elif isinstance(node, ast.Call):
            # Handle function calls
            args = []
            for arg in node.args:
                args.append(self._generate_node(arg))
            
            temp = self._new_temp()
            self._add_instruction('call', node.func.id if isinstance(node.func, ast.Name) else 'func', args, temp)
            return temp
        
        elif isinstance(node, ast.If):
            # Handle if statements
            condition = self._generate_node(node.test)
            else_label = self._new_label()
            end_label = self._new_label()
            
            self._add_instruction('if_false', condition, else_label)
            
            # Generate then block
            for stmt in node.body:
                self._generate_node(stmt)
            
            if node.orelse:
                self._add_instruction('goto', end_label)
            
            self._add_instruction('label', else_label)
            
            # Generate else block
            for stmt in node.orelse:
                self._generate_node(stmt)
            
            if node.orelse:
                self._add_instruction('label', end_label)
        
        elif isinstance(node, ast.For):
            # Handle for loops
            iter_var = self._generate_node(node.iter)
            start_label = self._new_label()
            end_label = self._new_label()
            
            # Initialize loop variable
            if isinstance(node.target, ast.Name):
                self._add_instruction('assign', '0', node.target.id)
            
            self._add_instruction('label', start_label)
            
            # Check condition (simplified)
            temp = self._new_temp()
            self._add_instruction('compare', node.target.id, f'len({iter_var})', temp, '<')
            self._add_instruction('if_false', temp, end_label)
            
            # Generate loop body
            for stmt in node.body:
                self._generate_node(stmt)
            
            # Increment loop variable
            if isinstance(node.target, ast.Name):
                temp_inc = self._new_temp()
                self._add_instruction('binary', node.target.id, '1', temp_inc, '+')
                self._add_instruction('assign', temp_inc, node.target.id)
            
            self._add_instruction('goto', start_label)
            self._add_instruction('label', end_label)
        
        elif isinstance(node, ast.While):
            # Handle while loops
            start_label = self._new_label()
            end_label = self._new_label()
            
            self._add_instruction('label', start_label)
            condition = self._generate_node(node.test)
            self._add_instruction('if_false', condition, end_label)
            
            # Generate loop body
            for stmt in node.body:
                self._generate_node(stmt)
            
            self._add_instruction('goto', start_label)
            self._add_instruction('label', end_label)
        
        elif isinstance(node, ast.Return):
            if node.value:
                result = self._generate_node(node.value)
                self._add_instruction('return', result)
            else:
                self._add_instruction('return', 'None')
        
        elif isinstance(node, ast.Expr):
            # Handle expression statements
            self._generate_node(node.value)
        
        return ""
    
    def _get_operator(self, op: ast.operator) -> str:
        """Get string representation of binary operator"""
        if isinstance(op, ast.Add):
            return '+'
        elif isinstance(op, ast.Sub):
            return '-'
        elif isinstance(op, ast.Mult):
            return '*'
        elif isinstance(op, ast.Div):
            return '/'
        elif isinstance(op, ast.Mod):
            return '%'
        elif isinstance(op, ast.Pow):
            return '**'
        elif isinstance(op, ast.LShift):
            return '<<'
        elif isinstance(op, ast.RShift):
            return '>>'
        elif isinstance(op, ast.BitOr):
            return '|'
        elif isinstance(op, ast.BitXor):
            return '^'
        elif isinstance(op, ast.BitAnd):
            return '&'
        elif isinstance(op, ast.FloorDiv):
            return '//'
        else:
            return '?'
    
    def _get_unary_operator(self, op: ast.unaryop) -> str:
        """Get string representation of unary operator"""
        if isinstance(op, ast.UAdd):
            return '+'
        elif isinstance(op, ast.USub):
            return '-'
        elif isinstance(op, ast.Not):
            return 'not'
        elif isinstance(op, ast.Invert):
            return '~'
        else:
            return '?'
    
    def _get_comparison_operator(self, op: ast.cmpop) -> str:
        """Get string representation of comparison operator"""
        if isinstance(op, ast.Eq):
            return '=='
        elif isinstance(op, ast.NotEq):
            return '!='
        elif isinstance(op, ast.Lt):
            return '<'
        elif isinstance(op, ast.LtE):
            return '<='
        elif isinstance(op, ast.Gt):
            return '>'
        elif isinstance(op, ast.GtE):
            return '>='
        elif isinstance(op, ast.Is):
            return 'is'
        elif isinstance(op, ast.IsNot):
            return 'is not'
        elif isinstance(op, ast.In):
            return 'in'
        elif isinstance(op, ast.NotIn):
            return 'not in'
        else:
            return '?'
    
    def _add_instruction(self, instr_type: str, *args):
        """Add an instruction to the IR list"""
        instruction = {
            'type': instr_type,
            'args': list(args),
            'line': len(self.instructions) + 1
        }
        self.instructions.append(instruction)
