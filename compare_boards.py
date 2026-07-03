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

def calculate_difficulty(case_steps):
    if case_steps == 0:
        return "Easy"
    elif 1 <= case_steps <= 4:
        return "Medium"
    else:
        return "Hard"

def main():
    parser = argparse.ArgumentParser(description="Compare original board difficulties with calculated logical complexity.")
    parser.add_argument("json_file", nargs="?", default="magic_boards2.json", help="Path to the JSON file containing the boards (default: magic_boards2.json).")
    parser.add_argument("--write", action="store_true", help="Write comparison results (case_steps and calculated_difficulty) back to the JSON file.")
    args = parser.parse_args()

    json_path = args.json_file
    if not os.path.exists(json_path):
        print(f"Error: File '{json_path}' not found.")
        print("Please ensure the file path is correct or pass it as an argument: python3 compare_boards.py <file_name>.json")
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
    print(f"Found {total_boards} boards. Running logical solver checks...")

    results = []
    matches = 0
    mismatches = 0
    
    # Confusion Matrix: original -> calculated -> count
    categories = ["Easy", "Medium", "Hard", "Unknown"]
    confusion_matrix = {orig: {calc: 0 for calc in categories} for orig in categories}

    mismatch_details = []

    for idx, board in enumerate(boards):
        board_id = board.get("board_id", f"unknown_idx_{idx}")
        orig_diff = normalize_diff(board.get("difficulty"))
        puzzle = board.get("puzzle")
        solution = board.get("solution")
        
        # Determine target sum
        magic_sum = board.get("magic_sum")
        if magic_sum is None and solution:
            magic_sum = sum(solution[0])
            
        if not puzzle or magic_sum is None:
            print(f"Skipping board {board_id} due to missing puzzle or solution/magic_sum.")
            confusion_matrix[orig_diff]["Unknown"] += 1
            continue

        # Solve and get complexity
        try:
            _, case_steps = logical_solve(puzzle, magic_sum)
            calc_diff = calculate_difficulty(case_steps)
        except Exception as e:
            print(f"Error solving board {board_id}: {e}")
            calc_diff = "Unknown"
            case_steps = -1

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
        
        # Save calculated values for potential write-back
        results.append((board, case_steps, calc_diff))

    # Generate Markdown Report Content
    report_lines = []
    report_lines.append("# Board Difficulty Comparison Report")
    report_lines.append(f"**Source File:** `{json_path}`  ")
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
        report_lines.append("| Board ID | Original Difficulty | Calculated Difficulty | Case Steps |")
        report_lines.append("| --- | --- | --- | --- |")
        for m in mismatch_details:
            report_lines.append(f"| `{m['board_id']}` | {m['orig_diff']} | **{m['calc_diff']}** | {m['case_steps']} |")
    else:
        report_lines.append("*All board difficulties match the logical solver classifications perfectly! 🎉*")

    report_content = "\n".join(report_lines)
    
    # Write report file
    report_filename = "board_comparison_report.md"
    with open(report_filename, "w", encoding="utf-8") as rf:
        rf.write(report_content)

    # Print summary to console
    print("=" * 60)
    print("COMPARISON SUMMARY")
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

    # Write back if requested
    if args.write:
        print(f"Writing calculations back to {json_path}...")
        
        # Create backup copy first
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
