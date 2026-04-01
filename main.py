from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from ir_generator import IRGenerator
from optimizer import Optimizer
from bytecode import BytecodeGenerator

app = FastAPI(title="Python Compiler Visualizer API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str

class AnalysisResponse(BaseModel):
    tokens: list
    ast: dict
    symbols: dict
    ir: list
    optimization: dict
    bytecode: list
    success: bool
    error: str = None

@app.get("/")
async def root():
    return {"message": "Python Compiler Visualizer API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/analyze", response_model=AnalysisResponse)
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
        
        # Phase 2: Syntax Analysis (AST)
        ast_result = parser.parse(request.code)
        
        # Phase 3: Semantic Analysis
        semantic_result = semantic_analyzer.analyze(request.code)
        
        # Phase 4: Intermediate Representation (Three Address Code)
        ir_result = ir_generator.generate(request.code)
        
        # Phase 5: Optimization
        optimization_result = optimizer.optimize(request.code)
        
        # Phase 6: Code Generation (Bytecode)
        bytecode_result = bytecode_generator.generate(request.code)
        
        return AnalysisResponse(
            tokens=tokens,
            ast=ast_result,
            symbols=semantic_result,
            ir=ir_result,
            optimization=optimization_result,
            bytecode=bytecode_result,
            success=True
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
    """Perform only syntax analysis"""
    try:
        parser = Parser()
        ast_result = parser.parse(request.code)
        return {"ast": ast_result, "success": True}
    except Exception as e:
        return {"ast": {}, "success": False, "error": str(e)}

@app.post("/semantic")
async def semantic_only(request: CodeRequest):
    """Perform only semantic analysis"""
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
            "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nresult = fibonacci(10)"
        },
        "loop": {
            "name": "For Loop",
            "code": "numbers = [1, 2, 3, 4, 5]\ntotal = 0\nfor num in numbers:\n    total += num\nprint(total)"
        },
        "class": {
            "name": "Class Definition",
            "code": "class Calculator:\n    def __init__(self):\n        self.result = 0\n    \n    def add(self, x):\n        self.result += x\n        return self.result\n    \ncalc = Calculator()\ncalc.add(5)\ncalc.add(3)"
        },
        "conditional": {
            "name": "Conditional Statement",
            "code": "age = 18\nif age >= 18:\n    status = \"adult\"\nelse:\n    status = \"minor\"\nprint(status)"
        },
        "complex": {
            "name": "Complex Example",
            "code": "def process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n        else:\n            result.append(0)\n    return result\n\nnumbers = [-1, 2, -3, 4, 5]\nprocessed = process_data(numbers)\nprint(processed)"
        }
    }
    return examples

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
