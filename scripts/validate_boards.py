#!/usr/bin/env python3
import json
import os

N = 5
VALUE_POOL = (3, 7, 8, 9)

# ----------------------------------------------------------------------
# Line helpers
# ----------------------------------------------------------------------
def line_indices(n):
    rows = [[(r, c) for c in range(n)] for r in range(n)]
    cols = [[(r, c) for r in range(n)] for c in range(n)]
    diags = [[(i, i) for i in range(n)], [(i, n - 1 - i) for i in range(n)]]
    return rows + cols + diags

LINES = line_indices(N)
LINES_FOR_CELL = {}
for line in LINES:
    for cell in line:
        LINES_FOR_CELL.setdefault(cell, []).append(line)

def check_magic_square(grid):
    """Verify that all rows, columns, and diagonals sum to the same number."""
    sums = set()
    for line in LINES:
        s = 0
        for r, c in line:
            if grid[r][c] is None:
                return False, None
            s += grid[r][c]
        sums.add(s)
    if len(sums) == 1:
        return True, sums.pop()
    return False, list(sums)

# ----------------------------------------------------------------------
# Backtracking solver to check for uniqueness
# ----------------------------------------------------------------------
def count_solutions(givens, domain, limit=2):
    grid = [row[:] for row in givens]
    blanks = [(r, c) for r in range(N) for c in range(N) if grid[r][c] is None]
    count = [0]
    solutions = []

    target0 = None
    for line in LINES:
        vals = [grid[r][c] for r, c in line]
        if all(v is not None for v in vals):
            s = sum(vals)
            if target0 is None:
                target0 = s
            elif s != target0:
                return 0, []  # contradictory givens

    def backtrack(idx, target):
        if count[0] >= limit:
            return
        if idx == len(blanks):
            count[0] += 1
            solutions.append([row[:] for row in grid])
            return
        r, c = blanks[idx]
        for v in domain:
            grid[r][c] = v
            new_target = target
            valid = True
            for line in LINES_FOR_CELL[(r, c)]:
                vals = [grid[rr][cc] for rr, cc in line]
                if all(x is not None for x in vals):
                    s = sum(vals)
                    if new_target is None:
                        new_target = s
                    elif s != new_target:
                        valid = False
                        break
            if valid:
                backtrack(idx + 1, new_target)
            grid[r][c] = None
            if count[0] >= limit:
                return

    backtrack(0, target0)
    return count[0], solutions

def main():
    json_path = "magic_boards2.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, "r") as f:
        try:
            boards = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return

    print(f"Validating {len(boards)} boards from {json_path}...\n")
    print(f"{'Board ID':38s} | {'Diff':6s} | {'Givens':6s} | {'Sum':3s} | {'Sols':4s} | {'Status':8s}")
    print("-" * 80)

    stats = {"Total": len(boards), "Unique": 0, "Invalid": 0, "Non-Unique": 0}
    diff_stats = {"Easy": 0, "Medium": 0, "Hard": 0}

    for b in boards:
        bid = b.get("board_id", "Unknown")
        difficulty = b.get("difficulty", "Unknown")
        puzzle = b.get("puzzle")
        solution = b.get("solution")
        expected_sum = b.get("magic_sum", 0)

        # Count givens
        givens_count = sum(1 for r in range(N) for c in range(N) if puzzle[r][c] is not None)

        # Check if stored solution is valid
        sol_valid, sol_sum = check_magic_square(solution)
        if not sol_valid:
            print(f"{bid:38s} | {difficulty:6s} | {givens_count:2d}/{N*N}  | {expected_sum:3d} | -    | INVALID_SOL")
            stats["Invalid"] += 1
            continue

        # Extract domain from solution or default to VALUE_POOL
        domain = sorted(set(v for row in solution for v in row))
        
        # Count solutions using solver
        num_sols, sols = count_solutions(puzzle, domain, limit=2)

        if num_sols == 1:
            status = "VALID"
            stats["Unique"] += 1
            diff_stats[difficulty] = diff_stats.get(difficulty, 0) + 1
        elif num_sols == 0:
            status = "NO_SOL"
            stats["Invalid"] += 1
        else:
            status = "MULTI_SOL"
            stats["Non-Unique"] += 1

        print(f"{bid:38s} | {difficulty:6s} | {givens_count:2d}/{N*N}  | {sol_sum:3d} | {num_sols:4d} | {status:8s}")

    print("\n" + "=" * 40)
    print("VALIDATION SUMMARY")
    print("=" * 40)
    print(f"Total Boards Checked:  {stats['Total']}")
    print(f"Unique Solutions:      {stats['Unique']} (Passed)")
    print(f"Non-Unique Solutions:  {stats['Non-Unique']} (Failed - multiple solutions possible)")
    print(f"Invalid/Unsolvable:    {stats['Invalid']} (Failed - no valid solution)")
    print("\nDifficulty Distribution of Unique Boards:")
    for diff, count in diff_stats.items():
        print(f"  - {diff:6s}: {count}")
    print("=" * 40)

if __name__ == "__main__":
    main()
