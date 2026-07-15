#!/usr/bin/env python3
import json
import os
import sys
import argparse
from generate_boards import solve_puzzle_cp_sat, N

def find_greedy_clues(puzzle, solution):
    """
    Greedily adds clues from the known solution to make the puzzle unique.
    
    NOTE: This is a greedy heuristic (a "good fix") to find a small set of
    clues to resolve ambiguity, and is not mathematically guaranteed to be
    the global absolute minimum set of clues.
    """
    puzzle_copy = [row[:] for row in puzzle]
    added_clues = []
    
    while True:
        sols = solve_puzzle_cp_sat(puzzle_copy, limit=100) # Search up to 100 solutions
        if len(sols) <= 1:
            break
            
        # Find all blank cells
        blanks = [(r, c) for r in range(N) for c in range(N) if puzzle_copy[r][c] is None]
        if not blanks:
            break
            
        best_cell = None
        best_sol_count = float("inf")
        
        # Test filling each blank cell to see which reduces ambiguity the most
        for r, c in blanks:
            puzzle_copy[r][c] = solution[r][c]
            test_sols = solve_puzzle_cp_sat(puzzle_copy, limit=100)
            puzzle_copy[r][c] = None  # backtrack
            
            # We want the choice that minimizes solutions (ideally down to 1)
            if len(test_sols) < best_sol_count:
                best_sol_count = len(test_sols)
                best_cell = (r, c)
                
        if best_cell:
            r, c = best_cell
            val = solution[r][c]
            puzzle_copy[r][c] = val
            added_clues.append(((r, c), val))
            
    return added_clues

def diagnose_board(board_data):
    bid = board_data.get("board_id", "Unknown")
    difficulty = board_data.get("difficulty", "Unknown")
    puzzle = board_data.get("puzzle")
    solution = board_data.get("solution")
    
    # 1. Count solutions against the full [1,9] domain
    sols = solve_puzzle_cp_sat(puzzle, limit=100) # search up to 100 solutions
    num_sols = len(sols)
    
    print("=" * 60)
    print(f"DIAGNOSIS REPORT FOR BOARD: {bid}")
    print("=" * 60)
    print(f"Difficulty Category: {difficulty}")
    print(f"Solution Count (full [1-9] domain): {num_sols}")
    
    clues = []
    if num_sols == 1:
        print("Status: VALID & UNIQUE (Exactly 1 unique solution)")
    elif num_sols == 0:
        print("Status: INVALID (No valid completions found)")
    else:
        print(f"Status: MULTI-SOL (Ambiguous - {num_sols} solutions found)")
        print("\nGreedily finding necessary clues to fix uniqueness across all valid solutions...")
        
        # Find the overall minimal fix across all valid completions
        best_clues = None
        best_sol_idx = -1
        
        for idx, sol in enumerate(sols):
            candidate_clues = find_greedy_clues(puzzle, sol)
            if best_clues is None or len(candidate_clues) < len(best_clues):
                best_clues = candidate_clues
                best_sol_idx = idx
                
        clues = best_clues
        print(f"Recommended fix (locks to Solution #{best_sol_idx + 1}): Add {len(clues)} clue(s)")
        for idx, ((r, c), val) in enumerate(clues, 1):
            print(f"  {idx}. Fill Cell ({r+1}, {c+1}) with value: {val} (1-indexed: Row {r+1}, Col {c+1})")
            
        # Check if the chosen solution matches the original stored solution
        if sols[best_sol_idx] != solution:
            print("\nNOTE: This fix resolves to a different valid completion than the original stored solution.")
            
    print("=" * 60)
    return num_sols, len(clues) if num_sols > 1 else 0

def run_regression_test():
    print("Running Regression Test on board c083f4f6-32b0-4bae-a311-44b1ae4e70cd...")
    json_path = "magic_boards2.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        sys.exit(1)
        
    with open(json_path, "r") as f:
        boards = json.load(f)
        
    target_board = next((b for b in boards if b["board_id"] == "c083f4f6-32b0-4bae-a311-44b1ae4e70cd"), None)
    if not target_board:
        print("Error: Target board c083f4f6-32b0-4bae-a311-44b1ae4e70cd not found in magic_boards2.json.")
        sys.exit(1)
        
    num_sols, num_clues_needed = diagnose_board(target_board)
    
    # Assertions
    assert num_sols == 17, f"Regression Failed: Expected 17 solutions, got {num_sols}"
    assert num_clues_needed == 1, f"Regression Failed: Expected 1-clue fix, got {num_clues_needed}"
    
    print("\n✅ REGRESSION TEST PASSED SUCCESSFULLY!")

def main():
    parser = argparse.ArgumentParser(description="Summetry Board Diagnostic Tool")
    parser.add_argument("board_id", nargs="?", type=str, help="UUID of board to diagnose from magic_boards2.json")
    parser.add_argument("--file", type=str, default="magic_boards2.json", help="Path to magic boards JSON file")
    parser.add_argument("--test-regression", action="store_true", help="Run the hardcoded regression test")
    args = parser.parse_args()
    
    if args.test_regression:
        run_regression_test()
        return
        
    if not args.board_id:
        parser.print_help()
        return
        
    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found.")
        sys.exit(1)
        
    with open(args.file, "r") as f:
        boards = json.load(f)
        
    board = next((b for b in boards if b["board_id"] == args.board_id), None)
    if not board:
        print(f"Error: Board ID {args.board_id} not found in {args.file}.")
        sys.exit(1)
        
    diagnose_board(board)

if __name__ == "__main__":
    main()
