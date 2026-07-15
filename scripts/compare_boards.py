#!/usr/bin/env python3
import json
import os
import sys
import argparse
import shutil
from generate_boards import logical_solve

def normalize_diff(diff_str):
    if not diff_str:
        return "Unknown"
    d = diff_str.lower().strip()
    if d in ["easy", "e"]:
        return "Easy"
    if d in ["medium", "med", "m"]:
        return "Medium"
    if d in ["hard", "h"]:
        return "Hard"
    return diff_str

def calculate_difficulty_cp(case_steps):
    if case_steps == 0:
        return "Easy"
    elif 1 <= case_steps <= 4:
        return "Medium"
    else:
        return "Hard"

def simulate_subtraction_solve(puzzle, solution, target_sum):
    grid = [row[:] for row in puzzle]
    stuck_count = 0
    while True:
        empty_cells = [(r, c) for r in range(5) for c in range(5) if grid[r][c] is None]
        if not empty_cells:
            break
        found_line = None
        # Check rows
        for r in range(5):
            if sum(1 for c in range(5) if grid[r][c] is not None) == 4:
                found_line = (r, next(i for i in range(5) if grid[r][i] is None))
                break
        # Check cols
        if not found_line:
            for c in range(5):
                if sum(1 for r in range(5) if grid[r][c] is not None) == 4:
                    found_line = (next(i for i in range(5) if grid[i][c] is None), c)
                    break
        # Check diag1
        if not found_line:
            if sum(1 for i in range(5) if grid[i][i] is not None) == 4:
                found_line = (next(j for j in range(5) if grid[j][j] is None), next(j for j in range(5) if grid[j][j] is None))
        # Check diag2
        if not found_line:
            if sum(1 for i in range(5) if grid[i][4-i] is not None) == 4:
                found_line = (next(j for j in range(5) if grid[j][4-j] is None), 4 - next(j for j in range(5) if grid[j][4-j] is None))
                
        if found_line:
            r, c = found_line
            grid[r][c] = solution[r][c]
        else:
            stuck_count += 1
            r, c = empty_cells[0]
            grid[r][c] = solution[r][c]
    return stuck_count

def calculate_difficulty_human(puzzle, solution, target_sum):
    stuck_count = simulate_subtraction_solve(puzzle, solution, target_sum)
    
    # 2. Count initial 4-clue lines
    row_clues = [sum(1 for val in row if val is not None) for row in puzzle]
    col_clues = [sum(1 for r in range(5) if puzzle[r][c] is not None) for c in range(5)]
    diag1 = sum(1 for i in range(5) if puzzle[i][i] is not None)
    diag2 = sum(1 for i in range(5) if puzzle[i][4-i] is not None)
    all_lines = row_clues + col_clues + [diag1, diag2]
    initial_4_clue_lines = sum(1 for count in all_lines if count == 4)
    
    # 3. Count diagonal clues
    diag_clues = sum(1 for i in range(5) if puzzle[i][i] is not None) + sum(1 for i in range(5) if puzzle[i][4-i] is not None)

    # 4. Cognitive load score (linear model derived from training accuracy on magic_boards_300.json)
    score = -2 * stuck_count + 2 * initial_4_clue_lines - 1 * diag_clues - 0.1 * target_sum
    
    if score >= -6.0:
        return "Medium"
    else:
        return "Easy"

def main():
    parser = argparse.ArgumentParser(description="Compare original board difficulties with calculated logical complexity.")
    parser.add_argument("json_file", nargs="?", default="magic_boards2.json", help="Path to the JSON file containing the boards (default: magic_boards2.json).")
    parser.add_argument("--mode", choices=["cp", "human"], default="human", help="Difficulty evaluation mode: 'cp' (logical solver steps) or 'human' (cognitive load solver simulation matching user playing experience). Default is 'human'.")
    parser.add_argument("--write", action="store_true", help="Write comparison results back to the JSON file.")
    args = parser.parse_args()

    json_path = args.json_file
    if not os.path.exists(json_path):
        print(f"Error: File '{json_path}' not found.")
        sys.exit(1)

    print(f"Reading boards from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            boards = json.load(f)
        except Exception as e:
            print(f"Error reading JSON: {e}")
            sys.exit(1)

    if not isinstance(boards, list):
        print("Error: JSON root must be a list of board objects.")
        sys.exit(1)

    total_boards = len(boards)
    print(f"Running difficulty checks in '{args.mode.upper()}' mode across {total_boards} boards...")

    results = []
    matches = 0
    mismatches = 0
    
    categories = ["Easy", "Medium", "Hard", "Unknown"]
    confusion_matrix = {orig: {calc: 0 for calc in categories} for orig in categories}
    mismatch_details = []

    for idx, board in enumerate(boards):
        board_id = board.get("board_id", f"unknown_idx_{idx}")
        orig_diff = normalize_diff(board.get("difficulty"))
        puzzle = board.get("puzzle")
        solution = board.get("solution")
        
        magic_sum = board.get("magic_sum")
        if magic_sum is None and solution:
            magic_sum = sum(solution[0])
            
        if not puzzle or magic_sum is None:
            print(f"Skipping board {board_id} due to missing puzzle or solution/magic_sum.")
            confusion_matrix[orig_diff]["Unknown"] += 1
            continue

        try:
            _, case_steps = logical_solve(puzzle, magic_sum)
        except Exception:
            case_steps = -1

        if args.mode == "human":
            # Use Human Cognitive model
            calc_diff = calculate_difficulty_human(puzzle, solution, magic_sum)
        else:
            # Use original CP steps mode
            calc_diff = calculate_difficulty_cp(case_steps)

        is_match = (orig_diff == calc_diff)
        if is_match:
            matches += 1
        else:
            mismatches += 1
            mismatch_details.append({
                "board_id": board_id,
                "orig_diff": orig_diff,
                "calc_diff": calc_diff,
                "case_steps": case_steps
            })

        confusion_matrix[orig_diff][calc_diff] += 1
        results.append((board, case_steps, calc_diff))

    # Generate Markdown Report Content
    report_lines = []
    report_lines.append("# Board Difficulty Comparison Report")
    report_lines.append(f"**Source File:** `{json_path}`  ")
    report_lines.append(f"**Evaluation Mode:** `{args.mode.upper()}`  ")
    report_lines.append(f"**Total Boards Evaluated:** {total_boards}  ")
    report_lines.append(f"**Matches:** {matches} ({matches/total_boards*100:.2f}%)  ")
    report_lines.append(f"**Mismatches:** {mismatches} ({mismatches/total_boards*100:.2f}%)  \n")

    report_lines.append("## 📊 Confusion Matrix")
    report_lines.append("| Original \\ Calculated | Easy | Medium | Hard | Unknown |")
    report_lines.append("| --- | --- | --- | --- | --- |")
    for orig in ["Easy", "Medium", "Hard"]:
        row_str = f"| **{orig}** | " + " | ".join(str(confusion_matrix[orig][calc]) for calc in categories) + " |"
        report_lines.append(row_str)
    report_lines.append("\n")

    report_lines.append("## ❌ Mismatch Details")
    if mismatch_details:
        report_lines.append("| Board ID | Original Difficulty | Calculated Difficulty |")
        report_lines.append("| --- | --- | --- |")
        for m in mismatch_details:
            report_lines.append(f"| `{m['board_id']}` | {m['orig_diff']} | **{m['calc_diff']}** |")
    else:
        report_lines.append("*All board difficulties match the solver classifications perfectly! 🎉*")

    report_content = "\n".join(report_lines)
    report_filename = "board_comparison_report.md"
    with open(report_filename, "w", encoding="utf-8") as rf:
        rf.write(report_content)

    # Print summary to console
    print("=" * 60)
    print(f"COMPARISON SUMMARY (MODE: {args.mode.upper()})")
    print("=" * 60)
    print(f"Total Boards: {total_boards}")
    print(f"Matches:      {matches} ({matches/total_boards*100:.2f}%)")
    print(f"Mismatches:   {mismatches} ({mismatches/total_boards*100:.2f}%)")
    print("-" * 60)
    print("Confusion Matrix:")
    print("  Original \\ Calc  |  Easy  |  Medium  |  Hard  ")
    print("  " + "-" * 45)
    for orig in ["Easy", "Medium", "Hard"]:
        print(f"  {orig:<15} |  {confusion_matrix[orig]['Easy']:<5} |  {confusion_matrix[orig]['Medium']:<7} |  {confusion_matrix[orig]['Hard']:<5}")
    print("=" * 60)
    print(f"Detailed Markdown report generated: {report_filename}")

    if args.write:
        print(f"Writing calculations back to {json_path}...")
        backup_path = json_path + ".bak"
        shutil.copyfile(json_path, backup_path)
        print(f"Backup saved to {backup_path}")

        updated_boards = []
        for board, case_steps, calc_diff in results:
            board["case_steps"] = case_steps
            board["calculated_difficulty"] = calc_diff
            updated_boards.append(board)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_boards, f, indent=2)
        print("Write back complete.")

if __name__ == "__main__":
    main()
