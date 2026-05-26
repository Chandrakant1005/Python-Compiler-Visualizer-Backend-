from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from ir_generator import IRGenerator
from optimizer import Optimizer
from bytecode import BytecodeGenerator

app = FastAPI(title="Python Compiler Visualizer API", version="1.0.0")

# Enable CORS for all origins (for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

class CodeRequest(BaseModel):
    code: str

class AnalysisResponse(BaseModel):
    tokens: list
    parser: dict
    symbols: dict
    ir: list
    optimization: dict
    bytecode: list
    success: bool
    error: Optional[str] = None


def has_phase_error(payload: Any) -> bool:
    if isinstance(payload, dict):
        return bool(payload.get("error"))
    if isinstance(payload, list):
        return any(isinstance(item, dict) and item.get("error") for item in payload)
    return False


def build_analysis_response(
    *,
    tokens: list,
    parser: dict,
    symbols: Optional[dict] = None,
    ir: Optional[list] = None,
    optimization: Optional[dict] = None,
    bytecode: Optional[list] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> dict:
    return {
        "tokens": tokens,
        "parser": parser,
        "symbols": symbols or {},
        "ir": ir or [],
        "optimization": optimization or {},
        "bytecode": bytecode or [],
        "success": success,
        "error": error,
    }

@app.get("/")
async def root():
    return {"message": "Python Compiler Visualizer API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze_code(request: CodeRequest):
    """Analyze Python code through all compiler phases"""
    
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    
    try:
        # Initialize all analyzers
        lexer = Lexer()
        parser = Parser()
        semantic_analyzer = SemanticAnalyzer()
        ir_generator = IRGenerator()
        optimizer = Optimizer()
        bytecode_generator = BytecodeGenerator()
        
        # Phase 1: Lexical Analysis
        tokens = lexer.tokenize(request.code)

        if has_phase_error(tokens):
            parser_result = parser.parse(request.code)
            return build_analysis_response(
                tokens=tokens,
                parser=parser_result,
            )
        
        # Phase 2: Parser Analysis (recursive descent using the PDF grammar subset)
        parser_result = parser.parse(request.code)

        # Phase 3: Semantic Analysis
        semantic_result = semantic_analyzer.analyze(request.code)

        if has_phase_error(semantic_result):
            return build_analysis_response(
                tokens=tokens,
                parser=parser_result,
                symbols=semantic_result,
            )

        if parser_result.get("error"):
            return build_analysis_response(
                tokens=tokens,
                parser=parser_result,
                symbols=semantic_result,
            )
        
        # Phase 4: Intermediate Representation (Three Address Code)
        ir_result = ir_generator.generate(request.code)

        if has_phase_error(ir_result):
            return build_analysis_response(
                tokens=tokens,
                parser=parser_result,
                symbols=semantic_result,
                ir=ir_result,
            )
        
        # Phase 5: Optimization
        optimization_result = optimizer.optimize(request.code)

        if has_phase_error(optimization_result):
            return build_analysis_response(
                tokens=tokens,
                parser=parser_result,
                symbols=semantic_result,
                ir=ir_result,
                optimization=optimization_result,
            )
        
        # Phase 6: Code Generation (Bytecode)
        bytecode_result = bytecode_generator.generate(request.code)
        
        return build_analysis_response(
            tokens=tokens,
            parser=parser_result,
            symbols=semantic_result,
            ir=ir_result,
            optimization=optimization_result,
            bytecode=bytecode_result,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/tokenize")
async def tokenize_only(request: CodeRequest):
    """Perform only lexical analysis"""
    try:
        lexer = Lexer()
        tokens = lexer.tokenize(request.code)
        return {"tokens": tokens, "success": True}
    except Exception as e:
        return {"tokens": [], "success": False, "error": str(e)}

@app.post("/parse")
async def parse_only(request: CodeRequest):
    """Perform only parser analysis"""
    try:
        parser = Parser()
        parser_result = parser.parse(request.code)
        return {"parser": parser_result, "success": True}
    except Exception as e:
        return {"parser": {}, "success": False, "error": str(e)}

@app.post("/semantic")
async def semantic_only(request: CodeRequest):
    """Build only the symbol table"""
    try:
        semantic_analyzer = SemanticAnalyzer()
        semantic_result = semantic_analyzer.analyze(request.code)
        return {"symbols": semantic_result, "success": True}
    except Exception as e:
        return {"symbols": {}, "success": False, "error": str(e)}

@app.post("/ir")
async def ir_only(request: CodeRequest):
    """Generate only intermediate representation"""
    try:
        ir_generator = IRGenerator()
        ir_result = ir_generator.generate(request.code)
        return {"ir": ir_result, "success": True}
    except Exception as e:
        return {"ir": [], "success": False, "error": str(e)}

@app.post("/optimize")
async def optimize_only(request: CodeRequest):
    """Perform only optimization"""
    try:
        optimizer = Optimizer()
        optimization_result = optimizer.optimize(request.code)
        return {"optimization": optimization_result, "success": True}
    except Exception as e:
        return {"optimization": {}, "success": False, "error": str(e)}

@app.post("/bytecode")
async def bytecode_only(request: CodeRequest):
    """Generate only bytecode"""
    try:
        bytecode_generator = BytecodeGenerator()
        bytecode_result = bytecode_generator.generate(request.code)
        return {"bytecode": bytecode_result, "success": True}
    except Exception as e:
        return {"bytecode": [], "success": False, "error": str(e)}

@app.get("/examples")
async def get_examples():
    """Get example code snippets"""
    examples = {
        "simple_assignment": {
            "name": "Simple Assignment",
            "code": "x = 10 + 20\ny = x * 2\nprint(y)"
        },
        "function": {
            "name": "Function Definition",
            "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nresult = fibonacci(10)\nprint(result)"
        },
        "loop": {
            "name": "For Loop",
            "code": "limit = 5\ntotal = 0\nfor num in limit:\n    total = total + num\nprint(total)"
        },
        "conditional": {
            "name": "Conditional Statement",
            "code": "age = 18\nif age >= 18:\n    result = age + 1\nelse:\n    result = age - 1\nprint(result)"
        },
        "while_loop": {
            "name": "While Loop",
            "code": "n = 3\nwhile n > 0:\n    n = n - 1\nprint(n)"
        },
        "nested": {
            "name": "Nested Control Flow",
            "code": "def adjust(n):\n    if n > 10:\n        return n - 1\n    else:\n        return n + 1\n\nvalue = adjust(10)\nprint(value)"
        }
    }
    return examples

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
