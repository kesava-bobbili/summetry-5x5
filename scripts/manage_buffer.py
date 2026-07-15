#!/usr/bin/env python3
import json
import os
import argparse
import hashlib
from datetime import datetime, timedelta
from generate_boards import generate_board_for_seed

QUEUE_FILE = "daily_queue.json"

def get_today_string():
    return datetime.now().strftime("%Y-%m-%d")

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)

def check_buffer_health():
    queue = load_queue()
    today_str = get_today_string()
    
    # Count future and today's boards in queue
    active_boards = [b for b in queue if b["date"] >= today_str]
    count = len(active_boards)
    
    print("=" * 60)
    print("SUMMETRY BUFFER HEALTH STATUS")
    print("=" * 60)
    print(f"Current Date: {today_str}")
    print(f"Total Daily Boards in Queue: {len(queue)}")
    print(f"Active/Future Boards: {count}")
    
    if count < 7:
        print("\n🚨 BUFFER_HEALTH_ALERT: The board buffer is running critically low!")
        print(f"Only {count} day(s) of boards remaining. Please run '--fill' to replenish the buffer.")
    else:
        print(f"\n✅ Buffer is healthy ({count} days remaining).")
    print("=" * 60)
    return count

def fill_buffer(days=30):
    queue = load_queue()
    today = datetime.now()
    
    # Identify existing dates in queue
    existing_dates = {b["date"] for b in queue}
    
    generated_count = 0
    start_date = today
    failed_dates = []
    
    print(f"Filing buffer for next {days} days...")
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        if date_str in existing_dates:
            continue
            
        print(f"Generating deterministic board for {date_str}...")
        # Hash date to get seed
        hash_val = hashlib.sha256(date_str.encode("utf-8")).hexdigest()
        date_seed = int(hash_val, 16) % (2**32)
        
        try:
            board = generate_board_for_seed(date_seed)
            board["date"] = date_str  # add the target publish date
            queue.append(board)
            generated_count += 1
        except RuntimeError as e:
            # Catch failure, print warning, and continue
            print(f"⚠️  WARNING: Failed to generate board for {date_str}! Error: {e}")
            failed_dates.append((date_str, str(e)))
            
    # Sort queue by date
    queue.sort(key=lambda x: x["date"])
    save_queue(queue)
    print(f"\nSuccessfully populated buffer. Added {generated_count} new boards.")
    
    if failed_dates:
        print("\n" + "=" * 60)
        print("🚨 BATCH GENERATION FAILURE SUMMARY:")
        print("=" * 60)
        for d, err in failed_dates:
            print(f"  - {d}: {err}")
        print("=" * 60)

def get_today_board():
    queue = load_queue()
    today_str = get_today_string()
    board = next((b for b in queue if b["date"] == today_str), None)
    if not board:
        print(f"Error: Today's board ({today_str}) is not in the queue. Fill buffer using '--fill'.")
        return None
    print(json.dumps(board, indent=2))
    return board

def main():
    parser = argparse.ArgumentParser(description="Summetry Daily Board Buffer Manager")
    parser.add_argument("--status", action="store_true", help="Check buffer health status")
    parser.add_argument("--fill", type=int, nargs="?", const=30, help="Generate and fill queue for N days (default 30)")
    parser.add_argument("--get-today", action="store_true", help="Retrieve today's board info")
    args = parser.parse_args()
    
    if args.status:
        check_buffer_health()
    elif args.fill is not None:
        fill_buffer(args.fill)
    elif args.get-today or (not args.status and args.fill is None):
        get_today_board()

if __name__ == "__main__":
    main()
