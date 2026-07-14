import json
import os
import random
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from ortools.sat.python import cp_model

app = FastAPI(title="Summetry Game API", description="Secure Backend API for Summetry Puzzle Verification and Diagnostics")

# Enable CORS for local cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

N = 5

# ==========================================
# Database Loader
# ==========================================
def load_boards(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    for idx, b in enumerate(data):
        b["num"] = idx + 1
    return data

# Load datasets on startup
boards = load_boards("magic_boards2.json")
boards_300 = load_boards("magic_boards_300.json")

# Build unified fast-lookup dictionary
boards_by_id = {b["board_id"]: b for b in boards}
boards_300_by_id = {b["board_id"]: b for b in boards_300}

# ==========================================
# Schema Definitions
# ==========================================
class CheckRequest(BaseModel):
    board_id: str
    grid: List[List[Optional[int]]]

class SolveRequest(BaseModel):
    puzzle: List[List[Optional[int]]]

# ==========================================
# Human Cognitive Rating Heuristics
# ==========================================
def simulate_subtraction_solve(puzzle, solution):
    grid = [row[:] for row in puzzle]
    stuck_count = 0
    while True:
        empty_cells = [(r, c) for r in range(N) for c in range(N) if grid[r][c] is None]
        if not empty_cells:
            break
        found_line = None
        for r in range(N):
            if sum(1 for c in range(N) if grid[r][c] is not None) == 4:
                found_line = (r, next(i for i in range(N) if grid[r][i] is None))
                break
        if not found_line:
            for c in range(N):
                if sum(1 for r in range(N) if grid[r][c] is not None) == 4:
                    found_line = (next(i for i in range(N) if grid[i][c] is None), c)
                    break
        if not found_line:
            if sum(1 for i in range(N) if grid[i][i] is not None) == 4:
                found_line = (next(j for j in range(N) if grid[j][j] is None), next(j for j in range(N) if grid[j][j] is None))
        if not found_line:
            if sum(1 for i in range(N) if grid[i][4-i] is not None) == 4:
                found_line = (next(j for j in range(N) if grid[j][4-j] is None), 4 - next(j for j in range(N) if grid[j][4-j] is None))
                
        if found_line:
            r, c = found_line
            grid[r][c] = solution[r][c]
        else:
            stuck_count += 1
            r, c = empty_cells[0]
            grid[r][c] = solution[r][c]
    return stuck_count

def calculate_difficulty_human(puzzle, solution, target_sum):
    stuck_count = simulate_subtraction_solve(puzzle, solution)
    
    # 2. Count initial 4-clue lines
    row_clues = [sum(1 for val in row if val is not None) for row in puzzle]
    col_clues = [sum(1 for r in range(N) if puzzle[r][c] is not None) for c in range(N)]
    diag1 = sum(1 for i in range(N) if puzzle[i][i] is not None)
    diag2 = sum(1 for i in range(N) if puzzle[i][4-i] is not None)
    all_lines = row_clues + col_clues + [diag1, diag2]
    initial_4_clue_lines = sum(1 for count in all_lines if count == 4)
    
    # 3. Count diagonal clues
    diag_clues = sum(1 for i in range(N) if puzzle[i][i] is not None) + sum(1 for i in range(N) if puzzle[i][4-i] is not None)

    # 4. Cognitive load score (linear model derived from training accuracy on magic_boards_300.json)
    score = -2 * stuck_count + 2 * initial_4_clue_lines - 1 * diag_clues - 0.1 * target_sum
    return "MEDIUM" if score >= -6.0 else "EASY"

# ==========================================
# CP-SAT Solver Implementation
# ==========================================
class SolutionCounter(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, limit=5):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__limit = limit
        self.__solutions = []

    def on_solution_callback(self):
        sol = []
        for r in range(N):
            sol.append([self.Value(self.__variables[r][c]) for c in range(N)])
        self.__solutions.append(sol)
        if len(self.__solutions) >= self.__limit:
            self.StopSearch()

    def solutions(self):
        return self.__solutions

def get_variables_for_board(puzzle, solution):
    if puzzle is None or solution is None:
        return {}
    
    empty_cells = [(r, c) for r in range(5) for c in range(5) if puzzle[r][c] is None]
    paired_cells = set()
    variables = {}
    
    var_names = ["x", "y", "z", "w", "p", "q"]
    var_idx = 0
    
    for r, c in empty_cells:
        if (r, c) in paired_cells:
            continue
            
        mirrors = [
            (r, 4 - c),
            (4 - r, c),
            (4 - r, 4 - c)
        ]
        
        for mr, mc in mirrors:
            if (mr, mc) == (r, c):
                continue
                
            if puzzle[mr][mc] is None and (mr, mc) not in paired_cells:
                var_name = var_names[var_idx % len(var_names)]
                var_idx += 1
                
                v1 = solution[r][c]
                v2 = solution[mr][mc]
                offset = v2 - v1
                
                variables[var_name] = {
                    "cell_1": [r, c],
                    "cell_2": [mr, mc],
                    "offset": offset
                }
                
                paired_cells.add((r, c))
                paired_cells.add((mr, mc))
                break
                
    return variables

# ==========================================
# API Routes
# ==========================================
@app.get("/api/board/daily")
def get_daily_board():
    if not boards:
        raise HTTPException(status_code=500, detail="Daily boards database is empty or missing")
    day_of_year = datetime.now().timetuple().tm_yday
    board = boards[day_of_year % len(boards)]
    return {
        "board_id": board["board_id"],
        "difficulty": board["difficulty"],
        "puzzle": board["puzzle"],
        "variables": get_variables_for_board(board["puzzle"], board["solution"])
    }

@app.get("/api/board/random")
def get_random_board():
    if not boards:
        raise HTTPException(status_code=500, detail="Daily boards database is empty or missing")
    board = random.choice(boards)
    return {
        "board_id": board["board_id"],
        "difficulty": board["difficulty"],
        "puzzle": board["puzzle"],
        "variables": get_variables_for_board(board["puzzle"], board["solution"])
    }

@app.get("/api/board/{board_id}")
def get_board_by_id(board_id: str):
    board = boards_by_id.get(board_id) or boards_300_by_id.get(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board ID not found")
    return {
        "board_id": board["board_id"],
        "difficulty": board["difficulty"],
        "puzzle": board["puzzle"],
        "variables": get_variables_for_board(board["puzzle"], board["solution"])
    }

@app.get("/api/board/{board_id}/solution")
def get_solution_by_id(board_id: str):
    board = boards_by_id.get(board_id) or boards_300_by_id.get(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board ID not found")
    return {
        "solution": board["solution"]
    }

@app.post("/api/board/check")
def check_solution(req: CheckRequest):
    board = boards_by_id.get(req.board_id) or boards_300_by_id.get(req.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board ID not found")

    solution = board["solution"]
    user_grid = req.grid

    # Validate row lengths and contents
    if len(user_grid) != N or any(len(row) != N for row in user_grid):
        return {"correct": False, "message": "Grid must be exactly 5x5"}

    # 1. Compare values directly against the server-side solution keys
    for r in range(N):
        for c in range(N):
            if user_grid[r][c] is None:
                return {"correct": False, "message": "Grid has empty cells"}
            if user_grid[r][c] != solution[r][c]:
                return {"correct": False, "message": "Values do not match solution"}

    # 2. Extract magic sum
    magic_sum = sum(solution[0])
    return {"correct": True, "magic_sum": magic_sum}

@app.post("/api/solver/solve")
def run_solver(req: SolveRequest):
    puzzle = req.puzzle
    if len(puzzle) != N or any(len(row) != N for row in puzzle):
         raise HTTPException(status_code=400, detail="Puzzle must be exactly 5x5")

    start_time = time.time()
    model = cp_model.CpModel()
    grid = [[model.NewIntVar(1, 9, f"cell_{r}_{c}") for c in range(N)] for r in range(N)]
    M = model.NewIntVar(5, 45, "M")

    # Connect clues
    for r in range(N):
        for c in range(N):
            if puzzle[r][c] is not None:
                model.Add(grid[r][c] == puzzle[r][c])

    # Sum constraints
    for r in range(N):
        model.Add(sum(grid[r][c] for c in range(N)) == M)
    for c in range(N):
        model.Add(sum(grid[r][c] for r in range(N)) == M)
    model.Add(sum(grid[i][i] for i in range(N)) == M)
    model.Add(sum(grid[i][N - 1 - i] for i in range(N)) == M)

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.num_search_workers = 1

    cb = SolutionCounter(grid, limit=5)
    solver.Solve(model, cb)

    elapsed_ms = (time.time() - start_time) * 1000
    sols = cb.solutions()

    human_diff = "EASY"
    if sols:
        magic_sum = sum(sols[0][0])
        try:
            human_diff = calculate_difficulty_human(puzzle, sols[0], magic_sum)
        except Exception:
            human_diff = "EASY"

    return {
        "solutions_count": len(sols),
        "solutions": sols,
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "elapsed_ms": round(elapsed_ms, 2),
        "human_difficulty": human_diff
    }
