import ast
from typing import Dict, List, Any, Set
from collections import defaultdict

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = defaultdict(list)
        self.undefined_variables = []
        self.scopes = []
        self.current_scope = 'global'
        self.errors = []
        self.warnings = []
    
    def analyze(self, code: str) -> Dict[str, Any]:
        """Perform semantic analysis on Python code"""
        try:
            tree = ast.parse(code)
            self._analyze_node(tree)
            
            return {
                'symbol_table': dict(self.symbol_table),
                'undefined_variables': self.undefined_variables,
                'scopes': self.scopes,
                'errors': self.errors,
                'warnings': self.warnings,
                'variable_usage': self._get_variable_usage()
            }
        except SyntaxError as e:
            return {
                'error': f'Syntax error: {str(e)}',
                'line': e.lineno,
                'column': e.offset
            }
    
    def _analyze_node(self, node: ast.AST, scope: str = 'global'):
        """Recursively analyze AST nodes"""
        if isinstance(node, ast.FunctionDef):
            self._enter_scope(node.name)
            self._add_symbol(node.name, 'function', node.lineno, scope)
            
            # Analyze function parameters
            for arg in node.args.args:
                self._add_symbol(arg.arg, 'parameter', node.lineno, node.name)
            
            # Analyze function body
            for stmt in node.body:
                self._analyze_node(stmt, node.name)
            
            self._exit_scope()
            
        elif isinstance(node, ast.ClassDef):
            self._enter_scope(node.name)
            self._add_symbol(node.name, 'class', node.lineno, scope)
            
            # Analyze class body
            for stmt in node.body:
                self._analyze_node(stmt, node.name)
            
            self._exit_scope()
            
        elif isinstance(node, ast.Assign):
            # Handle variable assignments
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._add_symbol(target.id, 'variable', node.lineno, scope)
                elif isinstance(target, ast.Tuple):
                    # Handle tuple unpacking
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            self._add_symbol(elt.id, 'variable', node.lineno, scope)
            
            # Analyze right-hand side
            self._analyze_node(node.value, scope)
            
        elif isinstance(node, ast.AugAssign):
            # Handle augmented assignments (x += 1)
            if isinstance(node.target, ast.Name):
                self._add_symbol(node.target.id, 'variable', node.lineno, scope)
            self._analyze_node(node.value, scope)
            
        elif isinstance(node, ast.Name):
            # Check for variable usage
            if isinstance(node.ctx, ast.Load):
                if not self._is_defined(node.id, scope):
                    self.undefined_variables.append({
                        'name': node.id,
                        'line': node.lineno,
                        'scope': scope
                    })
                    
        elif isinstance(node, ast.For):
            # Handle for loop variables
            if isinstance(node.target, ast.Name):
                self._add_symbol(node.target.id, 'variable', node.lineno, scope)
            elif isinstance(node.target, ast.Tuple):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        self._add_symbol(elt.id, 'variable', node.lineno, scope)
            
            # Analyze iter and body
            self._analyze_node(node.iter, scope)
            for stmt in node.body:
                self._analyze_node(stmt, scope)
                
        elif isinstance(node, ast.With):
            # Handle with statement context managers
            for item in node.items:
                if item.optional_vars:
                    if isinstance(item.optional_vars, ast.Name):
                        self._add_symbol(item.optional_vars.id, 'variable', node.lineno, scope)
                    elif isinstance(item.optional_vars, ast.Tuple):
                        for elt in item.optional_vars.elts:
                            if isinstance(elt, ast.Name):
                                self._add_symbol(elt.id, 'variable', node.lineno, scope)
            
            # Analyze body
            for stmt in node.body:
                self._analyze_node(stmt, scope)
        
        # Handle other node types
        for child in ast.iter_child_nodes(node):
            self._analyze_node(child, scope)
    
    def _enter_scope(self, scope_name: str):
        """Enter a new scope"""
        self.scopes.append({
            'name': scope_name,
            'parent': self.current_scope,
            'level': len(self.scopes)
        })
        self.current_scope = scope_name
    
    def _exit_scope(self):
        """Exit current scope"""
        if self.scopes:
            self.scopes.pop()
        if self.scopes:
            self.current_scope = self.scopes[-1]['name']
        else:
            self.current_scope = 'global'
    
    def _add_symbol(self, name: str, symbol_type: str, line: int, scope: str):
        """Add a symbol to the symbol table"""
        symbol_info = {
            'type': symbol_type,
            'line': line,
            'scope': scope
        }
        
        # Check for redefinition
        for existing in self.symbol_table[name]:
            if existing['scope'] == scope:
                self.warnings.append({
                    'type': 'redefinition',
                    'message': f'Variable "{name}" redefined in scope {scope}',
                    'line': line,
                    'original_line': existing['line']
                })
        
        self.symbol_table[name].append(symbol_info)
    
    def _is_defined(self, name: str, current_scope: str) -> bool:
        """Check if a variable is defined in the current or parent scopes"""
        # Check current scope
        for symbol in self.symbol_table[name]:
            if symbol['scope'] == current_scope:
                return True
        
        # Check parent scopes
        for scope_info in reversed(self.scopes):
            if scope_info['name'] == current_scope:
                break
            for symbol in self.symbol_table[name]:
                if symbol['scope'] == scope_info['name']:
                    return True
        
        # Check global scope
        for symbol in self.symbol_table[name]:
            if symbol['scope'] == 'global':
                return True
        
        return False
    
    def _get_variable_usage(self) -> Dict[str, Any]:
        """Get detailed variable usage information"""
        usage = {
            'variables': [],
            'functions': [],
            'classes': [],
            'parameters': []
        }
        
        for name, symbols in self.symbol_table.items():
            for symbol in symbols:
                usage[f'{symbol["type"]}s'].append({
                    'name': name,
                    'line': symbol['line'],
                    'scope': symbol['scope']
                })
        
        return usage
