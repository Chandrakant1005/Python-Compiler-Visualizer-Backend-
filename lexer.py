import tokenize
import io
from typing import List, Dict, Any

class Lexer:
    def __init__(self):
        self.tokens = []
    
    def tokenize(self, code: str) -> List[Dict[str, Any]]:
        """Tokenize Python code and return token information"""
        self.tokens = []
        
        try:
            # Convert string to BytesIO for tokenize
            code_bytes = io.BytesIO(code.encode('utf-8'))
            
            # Get tokens
            for token in tokenize.tokenize(code_bytes.readline):
                if token.type != tokenize.ENCODING:  # Skip encoding token
                    token_info = {
                        'type': tokenize.tok_name.get(token.type, 'UNKNOWN'),
                        'value': token.string,
                        'line': token.start[0],
                        'column': token.start[1],
                        'end_line': token.end[0],
                        'end_column': token.end[1]
                    }
                    self.tokens.append(token_info)
            
            return self.tokens
            
        except (tokenize.TokenError, IndentationError, SyntaxError) as e:
            return [{'error': f'Tokenization error: {str(e)}'}]
    
    def get_tokens_by_type(self, token_type: str) -> List[Dict[str, Any]]:
        """Get all tokens of a specific type"""
        return [token for token in self.tokens if token['type'] == token_type]
    
    def get_identifiers(self) -> List[str]:
        """Get all identifier tokens"""
        identifiers = []
        for token in self.tokens:
            if token['type'] == 'NAME':
                identifiers.append(token['value'])
        return list(set(identifiers))  # Remove duplicates
