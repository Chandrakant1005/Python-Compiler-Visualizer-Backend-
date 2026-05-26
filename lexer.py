from typing import Any, Dict, List

from parser import ManualTokenizer, ParseError


TOKEN_TYPE_MAP = {
    "IDENTIFIER": "identifier",
    "NUMBER": "const",
    "STRING": "const",
    "KEYWORD": "keyword",
    "OPERATOR": "op",
    "SEPARATOR": "sep",
    "NEWLINE": "newline",
    "INDENT": "indent",
    "DEDENT": "dedent",
    "EOF": "eof",
}


class Lexer:
    def __init__(self) -> None:
        self.tokens: List[Dict[str, Any]] = []

    def tokenize(self, code: str) -> List[Dict[str, Any]]:
        self.tokens = []
        tokenizer = ManualTokenizer()

        try:
            raw_tokens = tokenizer.tokenize(code)
            for token in raw_tokens:
                self.tokens.append(
                    {
                        "type": TOKEN_TYPE_MAP.get(token.kind, token.kind.lower()),
                        "value": token.value,
                        "line": token.line,
                        "column": token.column,
                        "end_line": token.line,
                        "end_column": token.column + max(len(token.value), 1) - 1,
                        "grammar_role": self._describe_role(token.kind, token.value),
                    }
                )
            return self.tokens
        except ParseError as exc:
            partial_tokens = exc.partial_tokens or tokenizer.partial_tokens
            for token in partial_tokens:
                self.tokens.append(
                    {
                        "type": TOKEN_TYPE_MAP.get(token.kind, token.kind.lower()),
                        "value": token.value,
                        "line": token.line,
                        "column": token.column,
                        "end_line": token.line,
                        "end_column": token.column + max(len(token.value), 1) - 1,
                        "grammar_role": self._describe_role(token.kind, token.value),
                    }
                )
            self.tokens.append(
                {
                    "error": f"Tokenization error: {str(exc)}",
                    "error_type": "LexicalError",
                    "description": "Lexical analysis stopped because the source contains a character or token outside the supported grammar.",
                    "line": exc.line,
                    "column": exc.column,
                }
            )
            return self.tokens

    def get_tokens_by_type(self, token_type: str) -> List[Dict[str, Any]]:
        return [token for token in self.tokens if token.get("type") == token_type]

    def get_identifiers(self) -> List[str]:
        identifiers = [token["value"] for token in self.tokens if token.get("type") == "identifier"]
        return sorted(set(identifiers))

    def _describe_role(self, kind: str, value: str) -> str:
        if kind == "KEYWORD":
            return "grammar keyword"
        if kind == "IDENTIFIER":
            return "identifier"
        if kind in {"NUMBER", "STRING"}:
            return "constant"
        if kind == "OPERATOR":
            return "operator"
        if kind == "SEPARATOR":
            return "separator"
        if kind == "NEWLINE":
            return "line break"
        if kind in {"INDENT", "DEDENT"}:
            return "block marker"
        if kind == "EOF":
            return "end of file"
        return value
