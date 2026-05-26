# Compiler Visualizer

Compiler Visualizer is a full-stack web app for analyzing Python-like source code across compiler phases.

## Features

- Lexical analysis
- Symbol table generation
- Recursive descent syntax analysis with parse tree rendering
- IR (3AC) generation
- Code optimization with applied-technique reporting
- Python bytecode inspection

## Stack

### Backend

- FastAPI
- Python standard library modules including `tokenize`, `ast`, and `dis`

### Frontend

- React
- D3.js
- CodeMirror

## Project Structure

```text
compiler-visualizer/
├── backend/
│   ├── main.py
│   ├── lexer.py
│   ├── parser.py
│   ├── semantic.py
│   ├── ir_generator.py
│   ├── optimizer.py
│   ├── bytecode.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── icons/
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── DashboardStyles.css
│   │   ├── index.css
│   │   └── index.js
│   └── package.json
└── README.md
```

## Local Setup

### Backend

```bash
cd /Users/chandrakantsinghdanu/Documents/compiler-visualizer/backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd /Users/chandrakantsinghdanu/Documents/compiler-visualizer/frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`.

Backend runs on `http://localhost:8000`.

## Analysis Pipeline

The app exposes the following phases in the UI:

1. Lexical Analysis
2. Symbol Table
3. Syntax Analysis
4. IR (3AC)
5. Code Optimization
6. Bytecode

## API

### Main

- `POST /analyze`

Request body:

```json
{
  "code": "a = 10\nprint(a)"
}
```

### Individual Endpoints

- `POST /tokenize`
- `POST /parse`
- `POST /semantic`
- `POST /ir`
- `POST /optimize`
- `POST /bytecode`

### Utility Endpoints

- `GET /examples`
- `GET /health`

## Notes

- The syntax analyzer is based on the project grammar and accepts a Python-like subset.
- Symbol table generation and later phases may still produce output even when grammar validation fails, depending on the input.
- Bytecode output is generated from Python compilation and grouped by scope.

## Build

### Frontend production build

```bash
cd /Users/chandrakantsinghdanu/Documents/compiler-visualizer/frontend
npm run build
```

## Troubleshooting

- If the frontend cannot connect, make sure the backend is running on port `8000`.
- If environment values change, restart the frontend dev server.
- If dependencies fail, remove and reinstall the local virtual environment or `node_modules` as needed.
