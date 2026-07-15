#!/usr/bin/env python3
import json
import os
import random
import uuid
import hashlib
import argparse
from ortools.sat.python import cp_model

N = 5

# ----------------------------------------------------------------------
# Line helpers
# ----------------------------------------------------------------------
def line_indices():
    rows = [[(r, c) for c in range(N)] for r in range(N)]
    cols = [[(r, c) for r in range(N)] for c in range(N)]
    diags = [[(i, i) for i in range(N)], [(i, N - 1 - i) for i in range(N)]]
    return rows + cols + diags

LINES = line_indices()
LINES_FOR_CELL = {}
for line in LINES:
    for cell in line:
        LINES_FOR_CELL.setdefault(cell, []).append(line)

# ----------------------------------------------------------------------
# CP-SAT Solver Interface
# ----------------------------------------------------------------------
class SolutionCounter(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, limit=2):
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


def solve_puzzle_cp_sat(puzzle, limit=2):
    """Solve the puzzle using CP-SAT, returning the list of solutions."""
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
    
    cb = SolutionCounter(grid, limit)
    solver.Solve(model, cb)
    return cb.solutions()


def generate_solved_grid(rng):
    """Generate a valid 5x5 magic sum solved grid using CP-SAT."""
    for attempt in range(100):
        model = cp_model.CpModel()
        grid = [[model.NewIntVar(1, 9, f"cell_{r}_{c}") for c in range(N)] for r in range(N)]
        M = model.NewIntVar(5, 45, "M")

        # Sum constraints
        for r in range(N):
            model.Add(sum(grid[r][c] for c in range(N)) == M)
        for c in range(N):
            model.Add(sum(grid[r][c] for r in range(N)) == M)
        model.Add(sum(grid[i][i] for i in range(N)) == M)
        model.Add(sum(grid[i][N - 1 - i] for i in range(N)) == M)

        # Prefill 5 random cells to ensure variety
        cells = [(r, c) for r in range(N) for c in range(N)]
        prefill_cells = rng.sample(cells, 5)
        for r, c in prefill_cells:
            model.Add(grid[r][c] == rng.randint(1, 9))

        solver = cp_model.CpSolver()
        solver.parameters.random_seed = rng.randint(0, 1000000)
        solver.parameters.num_search_workers = 1
        status = solver.Solve(model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return [[solver.Value(grid[r][c]) for c in range(N)] for r in range(N)], solver.Value(M)
            
    raise RuntimeError("Failed to generate a solved grid after 100 attempts")

# ----------------------------------------------------------------------
# Logical Forced-Deduction Solver
# ----------------------------------------------------------------------
def logical_solve(puzzle, target_sum):
    """
    Attempt to logically solve the board using candidate propagation.
    Returns:
      (solved_grid, case_steps) where case_steps is the number of logical contradictions
      discovered during case analysis (0 for Easy, 1-4 for Medium, >=5 for Hard).
    """
    # 1. Initialize candidate sets
    candidates = {}
    for r in range(N):
        for c in range(N):
            if puzzle[r][c] is not None:
                candidates[(r, c)] = {puzzle[r][c]}
            else:
                candidates[(r, c)] = set(range(1, 10))

    def propagate(cands):
        changed = True
        while changed:
            changed = False
            for line in LINES:
                unsolved = [cell for cell in line if len(cands[cell]) > 1]
                solved_sum = sum(list(cands[cell])[0] for cell in line if len(cands[cell]) == 1)
                rem_sum = target_sum - solved_sum

                if not unsolved:
                    if solved_sum != target_sum:
                        return False  # contradiction
                    continue

                for cell in unsolved:
                    other_unsolved = [x for x in unsolved if x != cell]
                    min_others = sum(min(cands[x]) for x in other_unsolved)
                    max_others = sum(max(cands[x]) for x in other_unsolved)

                    min_possible = rem_sum - max_others
                    max_possible = rem_sum - min_others

                    valid_vals = {v for v in cands[cell] if min_possible <= v <= max_possible}
                    if not valid_vals:
                        return False  # contradiction
                    if len(valid_vals) < len(cands[cell]):
                        cands[cell] = valid_vals
                        changed = True
        return True

    # Run initial propagation
    if not propagate(candidates):
        return None, 999

    # Check if solved
    if all(len(candidates[cell]) == 1 for cell in candidates):
        grid = [[list(candidates[(r, c)])[0] for c in range(N)] for r in range(N)]
        return grid, 0

    # 2. Case analysis (depth 1)
    case_steps = 0
    changed = True
    while changed:
        changed = False
        unsolved_cells = [cell for cell, cands in candidates.items() if len(cands) > 1]
        for cell in unsolved_cells:
            surviving_vals = set()
            for val in list(candidates[cell]):
                # Test propagation with this value
                test_cands = {k: v.copy() for k, v in candidates.items()}
                test_cands[cell] = {val}
                if propagate(test_cands):
                    surviving_vals.add(val)
                else:
                    # Contradiction found! This is a case-analysis deduction step.
                    case_steps += 1
            
            if not surviving_vals:
                return None, 999  # contradiction
            if len(surviving_vals) < len(candidates[cell]):
                candidates[cell] = surviving_vals
                changed = True
                if not propagate(candidates):
                    return None, 999

    # Check if fully solved
    if all(len(candidates[cell]) == 1 for cell in candidates):
        grid = [[list(candidates[(r, c)])[0] for c in range(N)] for r in range(N)]
        return grid, case_steps

    return None, 999  # Needs deeper backtracking search (Hard, > depth 1)

# ----------------------------------------------------------------------
# Core Generator Loop (Dig-and-Verify)
# ----------------------------------------------------------------------
def ensure_no_filled_lines(puzzle, solved, rng):
    """
    Ensure every row, col, and diag has at least one blank.
    If a line is fully filled, try to carve a cell in it.
    Returns (success, puzzle).
    """
    lines = []
    for r in range(N):
        lines.append([(r, c) for c in range(N)])
    for c in range(N):
        lines.append([(r, c) for r in range(N)])
    lines.append([(i, i) for i in range(N)])
    lines.append([(i, N - 1 - i) for i in range(N)])

    for attempt in range(20):
        filled_lines = []
        for line in lines:
            if all(puzzle[r][c] is not None for r, c in line):
                filled_lines.append(line)
        
        if not filled_lines:
            return True, puzzle
            
        line = filled_lines[0]
        cells_to_try = list(line)
        rng.shuffle(cells_to_try)
        
        carved_successfully = False
        for r, c in cells_to_try:
            if puzzle[r][c] is not None:
                val = puzzle[r][c]
                puzzle[r][c] = None
                
                sols = solve_puzzle_cp_sat(puzzle, limit=2)
                if len(sols) == 1:
                    carved_successfully = True
                    break
                else:
                    puzzle[r][c] = val
                    
        if not carved_successfully:
            return False, puzzle
            
    for line in lines:
        if all(puzzle[r][c] is not None for r, c in line):
            return False, puzzle
            
    return True, puzzle


def make_board(solved, target_blanks, rng):
    """Carve cells from a solved grid while verifying uniqueness of solution."""
    puzzle = [row[:] for row in solved]
    cells = [(r, c) for r in range(N) for c in range(N)]
    rng.shuffle(cells)

    blanks_count = 0
    for r, c in cells:
        if blanks_count >= target_blanks:
            break
        val = puzzle[r][c]
        puzzle[r][c] = None

        # Verify uniqueness using CP-SAT under full [1-9] domain
        sols = solve_puzzle_cp_sat(puzzle, limit=2)
        if len(sols) == 1:
            blanks_count += 1
        else:
            puzzle[r][c] = val  # Restore if multiple solutions possible
            
    success, puzzle = ensure_no_filled_lines(puzzle, solved, rng)
    if not success:
        return None, 0
        
    final_blanks = sum(row.count(None) for row in puzzle)
    return puzzle, final_blanks


def generate_board_for_seed(date_seed, max_attempts=50, target_difficulty=None):
    """Generate and classify a board deterministically for a date seed."""
    rng = random.Random(date_seed)
    
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            solved, target_sum = generate_solved_grid(rng)
        except RuntimeError:
            continue

        # Choose target blanks based on target difficulty if specified
        if target_difficulty == "Easy":
            target_blanks = rng.randint(6, 8)
        elif target_difficulty == "Medium":
            target_blanks = rng.randint(9, 11)
        elif target_difficulty == "Hard":
            target_blanks = rng.randint(12, 14)
        else:
            target_blanks = rng.randint(6, 14)

        res = make_board(solved, target_blanks, rng)
        if res[0] is None:
            continue
        puzzle, blank_count = res
        
        # Verify solution uniqueness
        sols = solve_puzzle_cp_sat(puzzle, limit=2)
        if len(sols) != 1:
            continue  # retry if not unique

        # Classify difficulty by logical case steps
        _, case_steps = logical_solve(puzzle, target_sum)
        if case_steps == 0:
            difficulty = "Easy"
        elif case_steps in [1, 2, 3, 4]:
            difficulty = "Medium"
        else:
            difficulty = "Hard"

        # If a specific target difficulty is requested, reject mismatching difficulty
        if target_difficulty and difficulty != target_difficulty:
            continue

        # Success!
        return {
            "board_id": str(uuid.UUID(int=rng.getrandbits(128))), # Deterministic UUID based on seed
            "difficulty": difficulty,
            "puzzle": puzzle,
            "solution": solved,
            "magic_sum": target_sum,
            "attempts": attempts
        }

    raise RuntimeError(f"CRITICAL: Failed to generate a valid {target_difficulty or ''} board after {max_attempts} attempts for seed {date_seed}!")


def run_calibration_distribution():
    print("Running batch calibration (generating 100 unique boards)...")
    
    counts = {}
    total = 100
    
    for i in range(total):
        seed = random.randint(0, 2**32 - 1)
        board = generate_board_for_seed(seed)
        blanks = sum(1 for r in range(N) for c in range(N) if board["puzzle"][r][c] is None)
        _, case_steps = logical_solve(board["puzzle"], board["magic_sum"])
        
        counts[(blanks, case_steps)] = counts.get((blanks, case_steps), 0) + 1
        print(f"Board {i+1:3d}/100: seed={seed:10d} -> blanks={blanks}, case_steps={case_steps}")
        
    all_blanks = sorted(list({k[0] for k in counts.keys()}))
    all_steps = sorted(list({k[1] for k in counts.keys()}))
    all_steps = sorted(list(set(all_steps + [0, 1, 2, 3, 4, 5])))

    print("\n" + "=" * 60)
    print("DIFFICULTY CLASSIFICATION CROSS-TABULATION REPORT")
    print("=" * 60)
    print("Columns: Case Analysis Contradiction Steps (0 = Easy, 1-4 = Medium, 5+ = Hard)")
    print("Rows: Blank Cell Count")
    print("-" * 60)
    
    header = f"{'Blanks':6s} | " + " | ".join(f"Steps {s:1d}" for s in all_steps) + " | Total"
    print(header)
    print("-" * len(header))
    
    grand_total = 0
    step_totals = {s: 0 for s in all_steps}
    
    for b in all_blanks:
        row_cells = []
        row_total = 0
        for s in all_steps:
            c = counts.get((b, s), 0)
            row_cells.append(f"{c:7d}")
            row_total += c
            step_totals[s] += c
        grand_total += row_total
        print(f"{b:6d} | " + " | ".join(row_cells) + f" | {row_total:5d}")
        
    print("-" * len(header))
    footer_cells = [f"{step_totals[s]:7d}" for s in all_steps]
    print(f"{'Total':6s} | " + " | ".join(footer_cells) + f" | {grand_total:5d}")
    print("=" * 60)
    
    print("\nSUMMARY OF DIFFICULTY TIER DISTRIBUTION:")
    easy_count = step_totals.get(0, 0)
    med_count = sum(step_totals.get(s, 0) for s in all_steps if s in [1, 2, 3, 4])
    hard_count = sum(step_totals.get(s, 0) for s in all_steps if s >= 5 or s == 999)
    
    easy_pct = (easy_count / grand_total) * 100
    med_pct = (med_count / grand_total) * 100
    hard_pct = (hard_count / grand_total) * 100
    print(f"  - Easy   (0 steps):    {easy_pct:5.1f}% ({easy_count} boards)")
    print(f"  - Medium (1-4 steps):  {med_pct:5.1f}% ({med_count} boards)")
    print(f"  - Hard   (>=5 steps):  {hard_pct:5.1f}% ({hard_count} boards)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Summetry Board Generator")
    parser.add_argument("--date", type=str, help="Generate deterministic board for a date (YYYY-MM-DD)")
    parser.add_argument("--count", type=int, default=1, help="Number of boards to generate (random seeds)")
    parser.add_argument("--output", type=str, default="magic_boards2.json", help="Output JSON file to append to")
    parser.add_argument("--difficulty", type=str, choices=["Easy", "Medium", "Hard"], help="Target difficulty tier")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration step on 100 boards and print cross-tab distribution report")
    args = parser.parse_args()

    if args.calibrate:
        run_calibration_distribution()
        return

    new_boards = []

    if args.date:
        # Seed derived from date string hash
        hash_val = hashlib.sha256(args.date.encode("utf-8")).hexdigest()
        date_seed = int(hash_val, 16) % (2**32)
        print(f"Generating deterministic board for date: {args.date} (seed: {date_seed}) target: {args.difficulty or 'Any'}...")
        board = generate_board_for_seed(date_seed, target_difficulty=args.difficulty)
        new_boards.append(board)
    else:
        print(f"Generating {args.count} random board(s) target: {args.difficulty or 'Any'}...")
        for i in range(args.count):
            seed = random.randint(0, 2**32 - 1)
            board = generate_board_for_seed(seed, target_difficulty=args.difficulty)
            new_boards.append(board)

    # Append to output JSON
    if os.path.exists(args.output):
        with open(args.output, "r") as f:
            try:
                boards = json.load(f)
            except Exception:
                boards = []
    else:
        boards = []

    boards.extend(new_boards)

    with open(args.output, "w") as f:
        json.dump(boards, f, indent=2)

    for b in new_boards:
        blanks = sum(1 for r in range(N) for c in range(N) if b["puzzle"][r][c] is None)
        print(f"Generated {b['difficulty']:6s} board (ID: {b['board_id'][:8]}...) in {b['attempts']} attempts. Blanks: {blanks}/25, Magic Sum: {b['magic_sum']}")


if __name__ == "__main__":
    main()
