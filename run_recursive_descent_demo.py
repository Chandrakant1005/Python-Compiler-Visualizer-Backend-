import json
import sys
from pathlib import Path

from lexer import Lexer
from parser import Parser


DEFAULT_SAMPLE = """a = 10
b = a + 20
if a > b:
    print(True)
else:
    print(False)
"""


def load_code() -> str:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).read_text(encoding="utf-8")

    piped = sys.stdin.read()
    if piped.strip():
        return piped

    return DEFAULT_SAMPLE


def main() -> None:
    code = load_code()
    lexer = Lexer()
    parser = Parser()

    output = {
        "source": code,
        "tokens": lexer.tokenize(code),
        "parser": parser.parse(code),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
