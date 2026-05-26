from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


KEYWORDS = {
    "if",
    "elif",
    "else",
    "while",
    "for",
    "in",
    "def",
    "return",
    "and",
    "or",
    "not",
    "True",
    "False",
}

MULTI_CHAR_OPERATORS = ["==", "!=", "<=", ">="]
SINGLE_CHAR_OPERATORS = set("=+-*/%<>")
SEPARATORS = {"(", ")", ",", ":"}


class ParseError(Exception):
    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        partial_tokens: Optional[List["Token"]] = None,
    ) -> None:
        super().__init__(message)
        self.line = line
        self.column = column
        self.partial_tokens = partial_tokens or []


@dataclass
class Token:
    kind: str
    value: str
    line: int
    column: int


@dataclass
class ParseTreeNode:
    label: str
    type: str
    children: List["ParseTreeNode"] = field(default_factory=list)
    production: Optional[str] = None
    field: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.label,
            "type": self.type,
            "kind": "nonterminal" if self.children else "terminal",
            "production": self.production,
            "line": self.line,
            "column": self.column,
            "children": [child.to_dict() for child in self.children],
        }
        if self.field:
            payload["field"] = self.field
        return payload


class ManualTokenizer:
    def __init__(self) -> None:
        self.partial_tokens: List[Token] = []

    def tokenize(self, code: str) -> List[Token]:
        tokens: List[Token] = []
        self.partial_tokens = tokens
        indent_stack = [0]
        lines = code.splitlines()

        for line_number, raw_line in enumerate(lines, start=1):
            if "\t" in raw_line:
                raise ParseError("Tabs are not supported. Use spaces for indentation.", line_number, 1, tokens.copy())

            stripped = raw_line.lstrip(" ")
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(raw_line) - len(stripped)
            if indent > indent_stack[-1]:
                indent_stack.append(indent)
                tokens.append(Token("INDENT", "INDENT", line_number, 1))
            else:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    tokens.append(Token("DEDENT", "DEDENT", line_number, 1))
                if indent != indent_stack[-1]:
                    raise ParseError("Invalid indentation level.", line_number, 1, tokens.copy())

            self._scan_line(stripped, line_number, indent, tokens)
            tokens.append(Token("NEWLINE", "\\n", line_number, len(raw_line) + 1))

        while len(indent_stack) > 1:
            indent_stack.pop()
            tokens.append(Token("DEDENT", "DEDENT", len(lines) + 1, 1))

        tokens.append(Token("EOF", "EOF", len(lines) + 1, 1))
        return tokens

    def _scan_line(self, line: str, line_number: int, indent: int, tokens: List[Token]) -> None:
        index = 0
        while index < len(line):
            char = line[index]
            column = indent + index + 1

            if char.isspace():
                index += 1
                continue

            if char == "#":
                break

            if char.isdigit():
                token, index = self._read_number(line, index, line_number, column)
                tokens.append(token)
                continue

            if char in {"'", '"'}:
                token, index = self._read_string(line, index, line_number, column)
                tokens.append(token)
                continue

            if char.isalpha() or char == "_":
                token, index = self._read_identifier(line, index, line_number, column)
                tokens.append(token)
                continue

            matched = False
            for operator in MULTI_CHAR_OPERATORS:
                if line.startswith(operator, index):
                    tokens.append(Token("OPERATOR", operator, line_number, column))
                    index += len(operator)
                    matched = True
                    break
            if matched:
                continue

            if char in SINGLE_CHAR_OPERATORS:
                tokens.append(Token("OPERATOR", char, line_number, column))
                index += 1
                continue

            if char in SEPARATORS:
                tokens.append(Token("SEPARATOR", char, line_number, column))
                index += 1
                continue

            raise ParseError(f"Unsupported character {char!r}.", line_number, column, tokens.copy())

    def _read_number(self, line: str, start: int, line_number: int, column: int) -> tuple[Token, int]:
        index = start
        seen_dot = False
        while index < len(line):
            char = line[index]
            if char.isdigit():
                index += 1
                continue
            if char == "." and not seen_dot:
                seen_dot = True
                index += 1
                continue
            break
        return Token("NUMBER", line[start:index], line_number, column), index

    def _read_string(self, line: str, start: int, line_number: int, column: int) -> tuple[Token, int]:
        quote = line[start]
        index = start + 1
        while index < len(line) and line[index] != quote:
            if line[index] == "\\" and index + 1 < len(line):
                index += 2
                continue
            index += 1
        if index >= len(line):
            raise ParseError("Unterminated string literal.", line_number, column, self.partial_tokens.copy())
        index += 1
        return Token("STRING", line[start:index], line_number, column), index

    def _read_identifier(self, line: str, start: int, line_number: int, column: int) -> tuple[Token, int]:
        index = start
        while index < len(line) and (line[index].isalnum() or line[index] == "_"):
            index += 1
        value = line[start:index]
        kind = "KEYWORD" if value in KEYWORDS else "IDENTIFIER"
        return Token(kind, value, line_number, column), index


class Parser:
    def __init__(self) -> None:
        self.tokens: List[Token] = []
        self.position = 0
        self.parse_tree: Optional[ParseTreeNode] = None
        self.production_counts: Counter[str] = Counter()

    def parse(self, code: str) -> Dict[str, Any]:
        try:
            self.tokens = ManualTokenizer().tokenize(code)
            self.position = 0
            self.parse_tree = None
            self.production_counts = Counter()
            self._skip_newlines()
            self.parse_tree = self._parse_file()
            self._expect("EOF")

            tree = self.parse_tree.to_dict()
            tree["grammar_productions"] = self._build_grammar_productions()
            tree["verification"] = {
                "is_valid": True,
                "message": "Source code is accepted by the recursive descent grammar.",
            }
            tree["summary"] = {
                "root_type": tree["type"],
                "total_nodes": self._count_nodes(self.parse_tree),
                "tree_depth": self._tree_depth(self.parse_tree),
                "production_count": len(self.production_counts),
            }
            return tree
        except ParseError as exc:
            return {
                "error": str(exc),
                "error_type": "ParseError",
                "line": exc.line,
                "column": exc.column,
                "grammar_productions": self._build_grammar_productions(),
                "verification": {
                    "is_valid": False,
                    "message": "Source code does not match the recursive descent grammar.",
                },
            }

    def get_tree_structure(self) -> Dict[str, Any]:
        return self.parse_tree.to_dict() if self.parse_tree else {}

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        return []

    def get_class_definitions(self) -> List[Dict[str, Any]]:
        return []

    def _parse_file(self) -> ParseTreeNode:
        children: List[ParseTreeNode] = []
        while not self._match("EOF"):
            if self._match("DEDENT"):
                raise ParseError("Unexpected dedent at file level.", self.current().line, self.current().column)
            children.append(self._with_field(self._parse_statement(), f"statement[{len(children)}]"))
            while self._match("NEWLINE"):
                children.append(self._with_field(self._newline_leaf(self.advance()), "newline"))
            self._skip_newlines()

        if not children:
            raise ParseError("Expected at least one statement.", self.current().line, self.current().column)

        return self._node("File", "File", children, "File -> Statement ('\\n' Statement)*")

    def _parse_block(self) -> ParseTreeNode:
        indent = self._indent_leaf(self._expect("INDENT"))
        children: List[ParseTreeNode] = [self._with_field(indent, "indent")]

        while not self._match("DEDENT"):
            if self._match("EOF"):
                raise ParseError("Expected DEDENT to close the block.", self.current().line, self.current().column)
            children.append(self._with_field(self._parse_statement(), f"statement[{len(children) - 1}]"))
            while self._match("NEWLINE"):
                children.append(self._with_field(self._newline_leaf(self.advance()), "newline"))
            self._skip_newlines()

        children.append(self._with_field(self._dedent_leaf(self._expect("DEDENT")), "dedent"))
        return self._node("Block", "Block", children, "Block -> INDENT Statement+ DEDENT")

    def _parse_statement(self) -> ParseTreeNode:
        token = self.current()

        if token.kind == "KEYWORD":
            if token.value == "if":
                return self._node("Statement", "Statement", [self._with_field(self._parse_if(), "value")], "Statement -> Cond")
            if token.value == "while":
                return self._node("Statement", "Statement", [self._with_field(self._parse_while(), "value")], "Statement -> While")
            if token.value == "for":
                return self._node("Statement", "Statement", [self._with_field(self._parse_for(), "value")], "Statement -> For")
            if token.value == "def":
                return self._node("Statement", "Statement", [self._with_field(self._parse_function_def(), "value")], "Statement -> FunctionDef")
            if token.value == "return":
                return self._node("Statement", "Statement", [self._with_field(self._parse_return(), "value")], "Statement -> Return")

        if self._is_assignment():
            return self._node("Statement", "Statement", [self._with_field(self._parse_assignment(), "value")], "Statement -> Arithmetic")

        if self._is_function_call():
            return self._node("Statement", "Statement", [self._with_field(self._parse_function_call(), "value")], "Statement -> Function")

        expr = self._parse_expression()
        return self._node("Statement", "Statement", [self._with_field(expr, "value")], "Statement -> Expression")

    def _parse_assignment(self) -> ParseTreeNode:
        target = self._wrap_e(self._identifier_leaf(self._expect("IDENTIFIER")), "E -> id")
        operator = self._operator_leaf(self._expect("OPERATOR", "="))
        value = self._parse_expression()
        return self._node(
            "Arithmetic",
            "Arithmetic",
            [
                self._with_field(target, "left"),
                self._with_field(operator, "operator"),
                self._with_field(value, "right"),
            ],
            "Arithmetic -> E '=' E",
        )

    def _parse_if(self) -> ParseTreeNode:
        children = [
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "if")), "keyword"),
            self._with_field(self._parse_relational_expression(), "condition"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))

        while self._match("KEYWORD", "elif"):
            children.append(self._with_field(self._parse_elif(), f"elif[{len(children)}]"))

        if self._match("KEYWORD", "else"):
            children.append(self._with_field(self._parse_else(), "else"))

        return self._node(
            "Cond",
            "Cond",
            children,
            "Cond -> 'if' RelArith ':' Block ('elif' RelArith ':' Block)* ('else' ':' Block)?",
        )

    def _parse_elif(self) -> ParseTreeNode:
        children = [
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "elif")), "keyword"),
            self._with_field(self._parse_relational_expression(), "condition"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))
        return self._node("Elif", "Elif", children, "Elif -> 'elif' RelArith ':' Block")

    def _parse_else(self) -> ParseTreeNode:
        children = [
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "else")), "keyword"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))
        return self._node("Else", "Else", children, "Else -> 'else' ':' Block")

    def _parse_while(self) -> ParseTreeNode:
        children = [
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "while")), "keyword"),
            self._with_field(self._parse_relational_expression(), "condition"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))
        return self._node("While", "While", children, "While -> 'while' RelArith ':' Block")

    def _parse_for(self) -> ParseTreeNode:
        keyword = self._keyword_leaf(self._expect("KEYWORD", "for"))
        target = self._wrap_e(self._identifier_leaf(self._expect("IDENTIFIER")), "E -> id")
        children = [
            self._with_field(keyword, "keyword"),
            self._with_field(target, "target"),
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "in")), "in"),
            self._with_field(self._parse_e(), "iterable"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))
        return self._node("For", "For", children, "For -> 'for' E 'in' E ':' Block")

    def _parse_function_def(self) -> ParseTreeNode:
        children = [
            self._with_field(self._keyword_leaf(self._expect("KEYWORD", "def")), "keyword"),
            self._with_field(self._identifier_leaf(self._expect("IDENTIFIER")), "name"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", "(")), "open"),
            self._with_field(self._parse_parameters(), "parameters"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ")")), "close"),
            self._with_field(self._separator_leaf(self._expect("SEPARATOR", ":")), "colon"),
        ]
        self._expect("NEWLINE")
        children.append(self._with_field(self._parse_block(), "body"))
        return self._node("FunctionDef", "FunctionDef", children, "FunctionDef -> 'def' id '(' Parameters ')' ':' Block")

    def _parse_parameters(self) -> ParseTreeNode:
        children: List[ParseTreeNode] = []
        if self._match("SEPARATOR", ")"):
            return self._node("Parameters", "Parameters", [], "Parameters -> epsilon")

        children.append(self._with_field(self._identifier_leaf(self._expect("IDENTIFIER")), "parameter"))
        while self._match("SEPARATOR", ","):
            children.append(self._with_field(self._separator_leaf(self.advance()), "comma"))
            children.append(self._with_field(self._identifier_leaf(self._expect("IDENTIFIER")), "parameter"))

        return self._node("Parameters", "Parameters", children, "Parameters -> id (',' id)*")

    def _parse_return(self) -> ParseTreeNode:
        children = [self._with_field(self._keyword_leaf(self._expect("KEYWORD", "return")), "keyword")]
        if not self._match("NEWLINE") and not self._match("DEDENT") and not self._match("EOF"):
            children.append(self._with_field(self._parse_expression(), "value"))
            production = "Return -> 'return' Expression"
        else:
            production = "Return -> 'return'"
        return self._node("Return", "Return", children, production)

    def _parse_expression(self) -> ParseTreeNode:
        if self._has_relational_operator_ahead():
            return self._parse_relational_expression()
        return self._parse_e()

    def _parse_relational_expression(self) -> ParseTreeNode:
        left = self._parse_e()
        if self._match("OPERATOR") and self.current().value in {"==", "!=", "<", ">", "<=", ">="}:
            operator = self._operator_leaf(self.advance())
            right = self._parse_e()
            return self._node(
                "RelArith",
                "RelArith",
                [
                    self._with_field(left, "left"),
                    self._with_field(operator, "operator"),
                    self._with_field(right, "right"),
                ],
                "RelArith -> E relop E",
            )
        return self._node("RelArith", "RelArith", [self._with_field(left, "value")], "RelArith -> E")

    def _parse_e(self) -> ParseTreeNode:
        node = self._parse_term()
        while (self._match("OPERATOR") and self.current().value in {"+", "-"}) or (
            self._match("KEYWORD") and self.current().value in {"and", "or"}
        ):
            operator = self._keyword_leaf(self.advance()) if self.current().kind == "KEYWORD" else self._operator_leaf(self.advance())
            right = self._parse_term()
            node = self._node(
                "E",
                "E",
                [
                    self._with_field(node, "left"),
                    self._with_field(operator, "operator"),
                    self._with_field(right, "right"),
                ],
                "E -> E addop Term",
            )
        return node

    def _parse_term(self) -> ParseTreeNode:
        node = self._parse_factor()
        while self._match("OPERATOR") and self.current().value in {"*", "/", "%"}:
            operator = self._operator_leaf(self.advance())
            right = self._parse_factor()
            node = self._node(
                "E",
                "E",
                [
                    self._with_field(node, "left"),
                    self._with_field(operator, "operator"),
                    self._with_field(right, "right"),
                ],
                "E -> E mulop Factor",
            )
        return node

    def _parse_factor(self) -> ParseTreeNode:
        if self._match("OPERATOR", "-"):
            operator = self._operator_leaf(self.advance())
            operand = self._parse_factor()
            return self._node("E", "E", [self._with_field(operator, "operator"), self._with_field(operand, "value")], "E -> '-' E")

        if self._match("KEYWORD", "not"):
            operator = self._keyword_leaf(self.advance())
            operand = self._parse_factor()
            return self._node("E", "E", [self._with_field(operator, "operator"), self._with_field(operand, "value")], "E -> 'not' E")

        if self._match("SEPARATOR", "("):
            open_paren = self._separator_leaf(self.advance())
            expr = self._parse_expression()
            close_paren = self._separator_leaf(self._expect("SEPARATOR", ")"))
            return self._node(
                "E",
                "E",
                [
                    self._with_field(open_paren, "open"),
                    self._with_field(expr, "value"),
                    self._with_field(close_paren, "close"),
                ],
                "E -> '(' Expression ')'",
            )

        if self._is_function_call():
            return self._wrap_e(self._parse_function_call(), "E -> Function")

        if self._match("NUMBER"):
            return self._wrap_e(self._number_leaf(self.advance()), "E -> const")

        if self._match("STRING"):
            return self._wrap_e(self._string_leaf(self.advance()), "E -> const")

        if self._match("KEYWORD") and self.current().value in {"True", "False"}:
            token = self.advance()
            return self._wrap_e(ParseTreeNode(f"const: {token.value}", "ConstToken", line=token.line, column=token.column), "E -> const")

        if self._match("IDENTIFIER"):
            return self._wrap_e(self._identifier_leaf(self.advance()), "E -> id")

        token = self.current()
        raise ParseError("Expected an expression.", token.line, token.column)

    def _parse_function_call(self) -> ParseTreeNode:
        function_name = self._identifier_leaf(self._expect("IDENTIFIER"))
        open_paren = self._separator_leaf(self._expect("SEPARATOR", "("))
        arguments = self._parse_arguments()
        close_paren = self._separator_leaf(self._expect("SEPARATOR", ")"))
        return self._node(
            "Function",
            "Function",
            [
                self._with_field(function_name, "function"),
                self._with_field(open_paren, "open"),
                self._with_field(arguments, "arguments"),
                self._with_field(close_paren, "close"),
            ],
            "Function -> id '(' Arguments ')'",
        )

    def _parse_arguments(self) -> ParseTreeNode:
        children: List[ParseTreeNode] = []
        if self._match("SEPARATOR", ")"):
            return self._node("Arguments", "Arguments", [], "Arguments -> epsilon")

        children.append(self._with_field(self._parse_expression(), "argument"))
        while self._match("SEPARATOR", ","):
            children.append(self._with_field(self._separator_leaf(self.advance()), "comma"))
            children.append(self._with_field(self._parse_expression(), "argument"))
        return self._node("Arguments", "Arguments", children, "Arguments -> Expression (',' Expression)*")

    def _is_assignment(self) -> bool:
        return self._match("IDENTIFIER") and self._peek().kind == "OPERATOR" and self._peek().value == "="

    def _is_function_call(self) -> bool:
        return self._match("IDENTIFIER") and self._peek().kind == "SEPARATOR" and self._peek().value == "("

    def _has_relational_operator_ahead(self) -> bool:
        probe = self.position
        depth = 0
        while probe < len(self.tokens):
            token = self.tokens[probe]
            if depth == 0 and token.kind in {"NEWLINE", "DEDENT", "EOF"}:
                return False
            if token.kind == "SEPARATOR" and token.value == "(":
                depth += 1
            elif token.kind == "SEPARATOR" and token.value == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and token.kind == "OPERATOR" and token.value in {"==", "!=", "<", ">", "<=", ">="}:
                return True
            probe += 1
        return False

    def _skip_newlines(self) -> None:
        while self._match("NEWLINE"):
            self.advance()

    def current(self) -> Token:
        return self.tokens[self.position]

    def _peek(self) -> Token:
        return self.tokens[min(self.position + 1, len(self.tokens) - 1)]

    def advance(self) -> Token:
        token = self.current()
        self.position += 1
        return token

    def _expect(self, kind: str, value: Optional[str] = None) -> Token:
        token = self.current()
        if token.kind != kind or (value is not None and token.value != value):
            expected = f"{kind} {value}" if value is not None else kind
            raise ParseError(f"Expected {expected}, found {token.value!r}.", token.line, token.column)
        self.position += 1
        return token

    def _match(self, kind: str, value: Optional[str] = None) -> bool:
        token = self.current()
        return token.kind == kind and (value is None or token.value == value)

    def _node(self, label: str, node_type: str, children: List[ParseTreeNode], production: str) -> ParseTreeNode:
        line = None
        column = None
        for child in children:
            if child.line is not None:
                line = child.line
                column = child.column
                break
        return ParseTreeNode(
            label=label,
            type=node_type,
            children=children,
            production=self._record_production(production),
            line=line,
            column=column,
        )

    def _wrap_e(self, child: ParseTreeNode, production: str) -> ParseTreeNode:
        return self._node("E", "E", [self._with_field(child, "value")], production)

    def _with_field(self, node: ParseTreeNode, field_name: str) -> ParseTreeNode:
        node.field = field_name
        return node

    def _record_production(self, production: str) -> str:
        self.production_counts[production] += 1
        return production

    def _build_grammar_productions(self) -> List[Dict[str, Any]]:
        return [{"production": production, "count": count} for production, count in self.production_counts.items()]

    def _identifier_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"id: {token.value}", "IdentifierToken", line=token.line, column=token.column)

    def _number_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"const: {token.value}", "ConstToken", line=token.line, column=token.column)

    def _string_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"const: {token.value}", "ConstToken", line=token.line, column=token.column)

    def _keyword_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"keyword: {token.value}", "KeywordToken", line=token.line, column=token.column)

    def _operator_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"op: {token.value}", "OperatorToken", line=token.line, column=token.column)

    def _separator_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode(f"sep: {token.value}", "SeparatorToken", line=token.line, column=token.column)

    def _newline_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode("\\n", "NewlineToken", line=token.line, column=token.column)

    def _indent_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode("INDENT", "IndentToken", line=token.line, column=token.column)

    def _dedent_leaf(self, token: Token) -> ParseTreeNode:
        return ParseTreeNode("DEDENT", "DedentToken", line=token.line, column=token.column)

    def _count_nodes(self, node: ParseTreeNode) -> int:
        return 1 + sum(self._count_nodes(child) for child in node.children)

    def _tree_depth(self, node: ParseTreeNode) -> int:
        if not node.children:
            return 0
        return 1 + max(self._tree_depth(child) for child in node.children)
