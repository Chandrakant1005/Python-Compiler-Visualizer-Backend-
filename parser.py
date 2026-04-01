import ast
from typing import Dict, Any, List

class Parser:
    def __init__(self):
        self.ast_tree = None
    
    def parse(self, code: str) -> Dict[str, Any]:
        """Parse Python code and return AST representation"""
        try:
            self.ast_tree = ast.parse(code)
            return self._ast_to_dict(self.ast_tree)
        except SyntaxError as e:
            return {
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno,
                'column': e.offset
            }
    
    def _ast_to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """Convert AST node to dictionary representation"""
        result = {
            'type': node.__class__.__name__,
            'attributes': {}
        }
        
        # Get node attributes
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                result['attributes'][field] = self._ast_to_dict(value)
            elif isinstance(value, list):
                result['attributes'][field] = [self._ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
            else:
                result['attributes'][field] = value
        
        # Add line and column information if available
        if hasattr(node, 'lineno'):
            result['line'] = node.lineno
        if hasattr(node, 'col_offset'):
            result['column'] = node.col_offset
            
        return result
    
    def get_tree_structure(self) -> Dict[str, Any]:
        """Get simplified tree structure for visualization"""
        if not self.ast_tree:
            return {}
        
        return self._build_tree_structure(self.ast_tree)
    
    def _build_tree_structure(self, node: ast.AST, depth: int = 0) -> Dict[str, Any]:
        """Build simplified tree structure for D3.js visualization"""
        name = node.__class__.__name__
        
        # Add value for certain node types
        if isinstance(node, ast.Name):
            name += f": {node.id}"
        elif isinstance(node, ast.Constant):
            name += f": {repr(node.value)}"
        elif isinstance(node, ast.Num):  # For older Python versions
            name += f": {node.n}"
        elif isinstance(node, ast.Str):  # For older Python versions
            name += f": {repr(node.s)}"
        
        children = []
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                children.append(self._build_tree_structure(value, depth + 1))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        children.append(self._build_tree_structure(item, depth + 1))
        
        return {
            'name': name,
            'type': node.__class__.__name__,
            'children': children if children else None,
            'depth': depth
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Extract function definitions from AST"""
        functions = []
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'returns': ast.unparse(node.returns) if hasattr(node, 'returns') and node.returns else None
                })
        
        return functions
    
    def get_class_definitions(self) -> List[Dict[str, Any]]:
        """Extract class definitions from AST"""
        classes = []
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                
                classes.append({
                    'name': node.name,
                    'line': node.lineno,
                    'bases': [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases],
                    'methods': methods
                })
        
        return classes
