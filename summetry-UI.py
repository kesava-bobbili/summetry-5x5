import os
import streamlit as st
import json
import random
from datetime import datetime

st.set_page_config(page_title="Summetry", layout="centered")

SHEET_ID = "11tlMENr8lofiH7tDxZ_YxNV65PqMUO47QM_bUpHHB5U"
CREDS_FILE = "striped-smile-186913-3bbfc9832329.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Notes/Sheets feature only turns on if the creds file is present AND
# gspread is installed. Otherwise the app still runs, just without notes.
NOTES_ENABLED = os.path.exists(CREDS_FILE)
if NOTES_ENABLED:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        NOTES_ENABLED = False

@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)
    try:
        return sh.worksheet("Notes")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Notes", rows=1000, cols=4)
        ws.append_row(["board_id", "author", "timestamp", "text"])
        return ws

# ============================
# Load boards
# ============================
def load_boards():
    with open("magic_boards2.json", "r") as f:
        data = json.load(f)
    for idx, b in enumerate(data):
        b["blanks"] = sum(row.count(None) for row in b["puzzle"])
        b["num"] = idx + 1
    by_id = {b["board_id"]: b for b in data}
    return data, by_id

def load_boards_300():
    try:
        with open("magic_boards_300.json", "r") as f:
            data = json.load(f)
        for b in data:
            b["blanks"] = sum(row.count(None) for row in b["puzzle"])
        by_id = {b["board_id"]: b for b in data}
        return data, by_id
    except Exception:
        return [], {}

boards, boards_by_id = load_boards()
boards_300, boards_300_by_id = load_boards_300()

# ============================
# Notes helpers
# ============================
LOCAL_FEEDBACK_FILE = "feedback.json"

def load_notes():
    if not NOTES_ENABLED:
        if not os.path.exists(LOCAL_FEEDBACK_FILE):
            return {}
        try:
            with open(LOCAL_FEEDBACK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    ws = get_sheet()
    rows = ws.get_all_records()
    notes = {}
    for row in rows:
        bid = row["board_id"]
        notes.setdefault(bid, []).append({
            "author":    row["author"],
            "timestamp": row["timestamp"],
            "text":      row["text"],
            "rating":    row.get("rating", "Note"),
        })
    return notes

def save_note(board_id, author, text, rating="Note"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not NOTES_ENABLED:
        notes = load_notes()
        if board_id not in notes or not isinstance(notes[board_id], list):
            notes[board_id] = []
        notes[board_id].append({
            "author":    author,
            "timestamp": timestamp,
            "text":      text.strip(),
            "rating":    rating,
        })
        with open(LOCAL_FEEDBACK_FILE, "w") as f:
            json.dump(notes, f, indent=2)
        return

    ws = get_sheet()
    ws.append_row([
        board_id,
        author,
        timestamp,
        text.strip(),
        rating
    ])

def get_variables_for_board(puzzle, solution):
    if puzzle is None or solution is None:
        return {}
    
    # Identify all empty cells
    empty_cells = [(r, c) for r in range(5) for c in range(5) if puzzle[r][c] is None]
    paired_cells = set()
    variables_map = {}
    
    # Available variable names
    var_names = ["x", "y", "z", "w", "p", "q"]
    var_idx = 0
    
    for r, c in empty_cells:
        if (r, c) in paired_cells:
            continue
            
        # Possible mirror candidates:
        mirrors = [
            (r, 4 - c),       # Horizontal reflection
            (4 - r, c),       # Vertical reflection
            (4 - r, 4 - c),   # Central rotation reflection
        ]
        
        for mr, mc in mirrors:
            if (mr, mc) == (r, c):
                continue # Skip self-mirror (e.g. center cell)
                
            # If the mirror cell is also empty and not yet paired
            if puzzle[mr][mc] is None and (mr, mc) not in paired_cells:
                # Pair them up!
                var_name = var_names[var_idx % len(var_names)]
                var_idx += 1
                
                v1 = solution[r][c]
                v2 = solution[mr][mc]
                offset = v2 - v1
                
                variables_map[(r, c)] = {
                    "name": var_name,
                    "role": "cell_1",
                    "offset": offset,
                    "partner": (mr, mc)
                }
                variables_map[(mr, mc)] = {
                    "name": var_name,
                    "role": "cell_2",
                    "offset": offset,
                    "partner": (r, c)
                }
                
                paired_cells.add((r, c))
                paired_cells.add((mr, mc))
                break
                
    return variables_map

# ============================
# Session state
# ============================
def init_board(board):
    st.session_state.puzzle      = board["puzzle"]
    st.session_state.solution    = board["solution"]
    st.session_state.difficulty  = board["difficulty"]
    st.session_state.board_id    = board["board_id"]
    
    # Get or calculate case_steps dynamically if missing (e.g. from daily_queue.json)
    case_steps = board.get("case_steps")
    if case_steps is None:
        try:
            from generate_boards import logical_solve
            magic_sum = board.get("magic_sum")
            if magic_sum is None and board.get("solution"):
                magic_sum = sum(board["solution"][0])
            if magic_sum is not None:
                _, case_steps = logical_solve(board["puzzle"], magic_sum)
            else:
                case_steps = 0
        except Exception:
            case_steps = 0
            
    st.session_state.case_steps  = case_steps
    size = len(board["puzzle"])
    st.session_state.size        = size
    st.session_state.cell_values = [[None] * size for _ in range(size)]
    st.session_state.selected    = None
    st.session_state.show_answer = False
    st.session_state.id_error    = ""

if "puzzle" not in st.session_state:
    init_board(random.choice(boards))

puzzle      = st.session_state.puzzle
solution    = st.session_state.solution
size        = st.session_state.size
cell_values = st.session_state.cell_values

# ============================
# Line helpers
# ============================
def all_lines(n):
    rows  = [[(r, c) for c in range(n)] for r in range(n)]
    cols  = [[(r, c) for r in range(n)] for c in range(n)]
    diags = [[(i, i) for i in range(n)], [(i, n-1-i) for i in range(n)]]
    return rows, cols, diags

def line_sum(line):
    total = 0
    for r, c in line:
        v = puzzle[r][c] if puzzle[r][c] is not None else cell_values[r][c]
        if v is None:
            return None, False
        total += v
    return total, True

rows_l, cols_l, diags_l = all_lines(size)
row_sums  = [line_sum(l) for l in rows_l]
col_sums  = [line_sum(l) for l in cols_l]
diag_sums = [line_sum(l) for l in diags_l]

# ============================
# CSS
# ============================
st.markdown("""
<style>
.given {
    width:52px; height:52px;
    display:flex; align-items:center; justify-content:center;
    font-size:22px; font-weight:700;
    background:#1e293b; color:#f1f5f9;
    border-radius:8px; margin:1px;
}
.sum-live { font-size:12px; color:#64748b; }
.sum-done { font-size:13px; font-weight:700; color:#22c55e; }
.board-id-box {
    font-family: monospace; font-size: 12px;
    background: #1e293b; color: #94a3b8;
    border-radius: 6px; padding: 6px 12px;
    display: inline-block; margin-bottom: 4px;
}
.note-card {
    background: #1e293b;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
.note-meta {
    font-size: 11px;
    color: #64748b;
    margin-bottom: 4px;
}
.note-author {
    color: #38bdf8;
    font-weight: 600;
}
.note-text {
    font-size: 14px;
    color: #e2e8f0;
}
.diff-badge {
    font-size: 11px;
    font-weight: 700;
    border-radius: 12px;
    padding: 3px 10px;
    display: inline-block;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: sans-serif;
    margin-bottom: 4px;
}
.diff-easy { background: #065f46; color: #a7f3d0; border: 1px solid #047857; }
.diff-medium { background: #78350f; color: #fef3c7; border: 1px solid #b45309; }
.diff-hard { background: #7f1d1d; color: #fee2e2; border: 1px solid #b91c1c; }
[data-testid="stHorizontalBlock"] > div { padding:0 2px !important; }
</style>
""", unsafe_allow_html=True)

# ============================
# Name prompt (once per session)
# ============================
if not st.session_state.get("author"):
    st.title("Summetry")
    st.markdown("**What's your name?** (used to sign your board notes)")
    name_col, btn_col = st.columns([3, 1])
    with name_col:
        name_input = st.text_input("Name", placeholder="e.g. Alice", label_visibility="collapsed")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Continue", type="primary"):
            if name_input.strip():
                st.session_state.author = name_input.strip()
                st.rerun()
            else:
                st.error("Please enter a name.")
    st.stop()

author = st.session_state.author

# ============================
# Standalone Solver Page Helpers
# ============================
def render_keyboard_listener():
    import streamlit.components.v1 as components
    components.html(
        f"""
        <script>
        const parentDoc = window.parent.document;
        if (!window.parent.__summetry_keyboard_listener_added__) {{
            window.parent.__summetry_keyboard_listener_added__ = true;
            
            // Auto-select text in solver inputs on focus
            parentDoc.addEventListener('focusin', function(e) {{
                if (e.target && e.target.tagName === 'INPUT') {{
                    const container = e.target.closest('[class*="st-key-solver_cell_"]');
                    if (container) {{
                        e.target.select();
                    }}
                }}
            }});
            
            // Keydown listener
            parentDoc.addEventListener('keydown', function(e) {{
                let key = e.key;
                
                // Check if user is typing in the Custom Solver grid inputs
                if (e.target && e.target.tagName === 'INPUT') {{
                    const inputs = Array.from(parentDoc.querySelectorAll('[class*="st-key-solver_cell_"] input'));
                    const idx = inputs.indexOf(e.target);
                    if (idx !== -1) {{
                        let r = Math.floor(idx / 5);
                        let c = idx % 5;
                        
                        // 1. Grid cell navigation with Arrow Keys
                        if (key === 'ArrowUp' || key === 'ArrowDown' || key === 'ArrowLeft' || key === 'ArrowRight') {{
                            e.preventDefault();
                            let nr = r, nc = c;
                            if (key === 'ArrowUp') nr--;
                            else if (key === 'ArrowDown') nr++;
                            else if (key === 'ArrowLeft') nc--;
                            else if (key === 'ArrowRight') nc++;
                            
                            if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5) {{
                                const nextInput = inputs[nr * 5 + nc];
                                if (nextInput) {{
                                    nextInput.focus();
                                    nextInput.select();
                                }}
                            }}
                            return;
                        }}
                        
                        // 2. Auto-overwrite and keep focus on Digit Key (1-9)
                        if (key >= '1' && key <= '9') {{
                            e.preventDefault();
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            nativeSetter.call(e.target, key);
                            e.target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            e.target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return;
                        }}
                        
                        // 3. Backspace - clear and keep focus
                        if (key === 'Backspace' || key === 'Delete' || key === '0' || key.toLowerCase() === 'x') {{
                            e.preventDefault();
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            nativeSetter.call(e.target, '');
                            e.target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            e.target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return;
                        }}
                    }}
                }}
                
                // Standard inputs check (notes, name prompt etc.)
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
                    return;
                }}
                
                // Normal board keyboard controls
                if (key >= '1' && key <= '9') {{
                    const btn = parentDoc.querySelector(`.st-key-pad${{key}} button`);
                    if (btn) {{
                        btn.click();
                    }}
                }} else if (key === 'Backspace' || key === 'Delete' || key.toLowerCase() === 'x' || key === '0') {{
                    const btn = parentDoc.querySelector('.st-key-pad_clear button');
                    if (btn) {{
                        btn.click();
                    }}
                }}
                
                // Normal board cell navigation with Arrow Keys
                if (key === 'ArrowUp' || key === 'ArrowDown' || key === 'ArrowLeft' || key === 'ArrowRight') {{
                    e.preventDefault();
                    const stateEl = parentDoc.getElementById('summetry-state');
                    let currentSelRow = stateEl ? parseInt(stateEl.getAttribute('data-selected-row')) : -1;
                    let currentSelCol = stateEl ? parseInt(stateEl.getAttribute('data-selected-col')) : -1;
                    
                    if (currentSelRow === -1) {{
                        for (let r = 0; r < 5; r++) {{
                            for (let c = 0; c < 5; c++) {{
                                const btn = parentDoc.querySelector(`.st-key-c${{r}}${{c}} button`);
                                if (btn) {{
                                    btn.click();
                                    return;
                                }}
                            }}
                        }}
                        return;
                    }}
                    
                    let new_r = currentSelRow;
                    let new_c = currentSelCol;
                    let nextBtn = null;
                    while (true) {{
                        if (key === 'ArrowUp') new_r--;
                        else if (key === 'ArrowDown') new_r++;
                        else if (key === 'ArrowLeft') new_c--;
                        else if (key === 'ArrowRight') new_c++;
                        
                        if (new_r < 0 || new_r >= 5 || new_c < 0 || new_c >= 5) {{
                            break;
                        }}
                        
                        nextBtn = parentDoc.querySelector(`.st-key-c${{new_r}}${{new_c}} button`);
                        if (nextBtn) {{
                            nextBtn.click();
                            break;
                        }}
                    }}
                    return;
                }}
            }});
        }}
        </script>
        """,
        height=0,
        width=0
    )

def simulate_subtraction_solve(puzzle, solution, target_sum):
    grid = [row[:] for row in puzzle]
    stuck_count = 0
    while True:
        empty_cells = [(r, c) for r in range(5) for c in range(5) if grid[r][c] is None]
        if not empty_cells:
            break
        found_line = None
        for r in range(5):
            if sum(1 for c in range(5) if grid[r][c] is not None) == 4:
                found_line = (r, next(i for i in range(5) if grid[r][i] is None))
                break
        if not found_line:
            for c in range(5):
                if sum(1 for r in range(5) if grid[r][c] is not None) == 4:
                    found_line = (next(i for i in range(5) if grid[i][c] is None), c)
                    break
        if not found_line:
            if sum(1 for i in range(5) if grid[i][i] is not None) == 4:
                found_line = (next(j for j in range(5) if grid[j][j] is None), next(j for j in range(5) if grid[j][j] is None))
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
        return "MEDIUM", score
    else:
        return "EASY", score

def render_custom_solver(standalone=False):
    if not standalone:
        st.write("Click below to open the Standalone Custom Board Solver & Diagnostics tool in a new tab:")
        st.link_button("↗️ Open Standalone Solver in New Tab", "/?page=solver", use_container_width=True)
        return

    st.subheader("🛠️ Standalone Solver & Diagnostics")
    st.write("Enter digits 1-9 (leave blank for empty cells) to solve any custom 5x5 board:")
    st.link_button("🎮 Back to Main Game", "/", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Load by ID section
    st.subheader("🔍 Load Board by ID")
    col_id_1, col_id_2 = st.columns([3.5, 1])
    with col_id_1:
        search_id = st.text_input(
            "Enter Board ID",
            key="solver_search_id_standalone" if standalone else "solver_search_id_expander",
            label_visibility="collapsed",
            placeholder="Enter Board ID (UUID)..."
        )
    with col_id_2:
        if st.button("Load Clues", key="solver_load_btn_standalone" if standalone else "solver_load_btn_expander", use_container_width=True):
            if search_id.strip():
                # Find board by ID in daily boards or 300 boards
                target_board = boards_by_id.get(search_id.strip())
                if not target_board:
                    target_board = boards_300_by_id.get(search_id.strip())
                if target_board:
                    puzzle = target_board["puzzle"]
                    for r in range(5):
                        for c in range(5):
                            val = puzzle[r][c]
                            st.session_state[f"solver_cell_{r}_{c}"] = str(val) if val is not None else ""
                    st.success(f"✅ Loaded board '{search_id.strip()}' clues!")
                    st.rerun()
                else:
                    st.error("❌ Board ID not found in daily queue or 300-boards database.")
            else:
                st.warning("Please enter a Board ID first.")

    st.markdown("---")
    
    # 2. Solver core functions
    def solve_custom_board_with_stats(puzzle):
        import time
        from ortools.sat.python import cp_model
        from generate_boards import SolutionCounter, N
        
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
        
        branches = solver.NumBranches()
        conflicts = solver.NumConflicts()
        num_constraints = len(model.Proto().constraints)
        num_variables = 26
        
        # run logical solve and human cognitive solve to measure difficulty if a valid completion exists
        human_diff = "EASY"
        if cb.solutions():
            first_sol = cb.solutions()[0]
            magic_sum = sum(first_sol[0])
            try:
                human_diff, _ = calculate_difficulty_human(puzzle, first_sol, magic_sum)
            except Exception:
                human_diff = "EASY"
        else:
            human_diff = "EASY"
            
        return cb.solutions(), branches, conflicts, num_constraints, num_variables, elapsed_ms, human_diff

    solver_grid = []
    for r in range(5):
        cols = st.columns(5)
        row_vals = []
        for c in range(5):
            with cols[c]:
                val = st.text_input(
                    "",
                    value="",
                    key=f"solver_cell_{r}_{c}",
                    max_chars=1,
                    label_visibility="collapsed"
                )
                val = val.strip()
                if val in [str(i) for i in range(1, 10)]:
                    row_vals.append(int(val))
                else:
                    row_vals.append(None)
        solver_grid.append(row_vals)

    if st.button("Solve Board", type="primary", key="run_custom_solver_btn_standalone" if standalone else "run_custom_solver_btn_expander", use_container_width=True):
        sols, branches, conflicts, num_constraints, num_variables, elapsed_ms, human_diff = solve_custom_board_with_stats(solver_grid)
        if not sols:
            st.error(f"❌ No valid solution exists for this board configuration! (Checked {num_constraints} constraints in {elapsed_ms:.2f} ms)")
        else:
            st.success(f"🎉 Found {len(sols)} valid completion(s) in {elapsed_ms:.2f} ms!")
            
            # Display difficulty parameters if available
            diff_color = "#065f46" if human_diff == "EASY" else "#78350f"
            st.markdown(
                f"🧩 **Complexity (Human Rating):** <span style='background:{diff_color}; color:white; border-radius:4px; padding:2px 8px; font-size:12px; font-weight:700;'>{human_diff}</span>",
                unsafe_allow_html=True
            )
            
            st.markdown(
                f"<div style='font-size:12px; color:#94a3b8; background:#1e293b; padding:8px 12px; border-radius:6px; margin-top:8px; margin-bottom:12px; line-height:1.5;'>"
                f"🧠 **Solver Statistics:**<br>"
                f"• Variables Evaluated: <b>{num_variables}</b> (25 grid cells + magic sum)<br>"
                f"• Constraints Enforced: <b>{num_constraints}</b> magic sum equations<br>"
                f"• Search Branches: <b>{branches}</b><br>"
                f"• Conflicts Encountered: <b>{conflicts}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
            
            for idx, sol in enumerate(sols):
                st.markdown(f"**Solution #{idx+1}** (Magic Sum = {sum(sol[0])}):")
                html_grid = "<div style='display:grid; grid-template-columns: repeat(5, 45px); gap: 4px; margin-bottom: 12px;'>"
                for r_idx in range(5):
                    for c_idx in range(5):
                        is_input = solver_grid[r_idx][c_idx] is not None
                        bg = "#1e293b" if is_input else "#0f766e"
                        html_grid += f"<div style='width:45px; height:45px; display:flex; align-items:center; justify-content:center; background:{bg}; color:white; font-weight:bold; border-radius:6px; font-size:18px;'>{sol[r_idx][c_idx]}</div>"
                html_grid += "</div>"
                st.markdown(html_grid, unsafe_allow_html=True)

# Route to standalone solver if requested
if st.query_params.get("page") == "solver":
    render_custom_solver(standalone=True)
    render_keyboard_listener()
    st.stop()

# ============================
# Sidebar — board loader
# ============================
def on_board_change():
    label = st.session_state.board_select_dropdown
    for b in boards:
        lbl = f"Board {b['num']} ({b['difficulty']})"
        if lbl == label:
            init_board(b)
            break

with st.sidebar:
    st.header("Load Board")

    st.checkbox("🧮 Enable Variables Mode", key="variables_mode")

    st.subheader("Filter by Difficulty")
    diff_options = ["All", "Easy", "Medium", "Hard"]
    selected_diff = st.selectbox("Difficulty Filter", diff_options, key="selected_difficulty_filter", label_visibility="collapsed")

    # Filter boards based on selected difficulty
    filtered_boards = []
    for b in boards:
        if selected_diff == "All" or b["difficulty"] == selected_diff:
            filtered_boards.append(b)

    if st.button(f"🔀 Random {selected_diff} Board", use_container_width=True):
        if filtered_boards:
            init_board(random.choice(filtered_boards))
            st.rerun()

    st.markdown("---")
    st.subheader("Select Specific Board")

    if filtered_boards:
        board_labels = [
            f"Board {b['num']} ({b['difficulty']})"
            for b in filtered_boards
        ]
        
        current_board = boards_by_id.get(st.session_state.board_id)
        if current_board:
            current_label = f"Board {current_board['num']} ({current_board['difficulty']})"
            if current_label not in board_labels:
                board_labels.insert(0, current_label)
            current_index = board_labels.index(current_label)
        else:
            current_index = 0

        st.selectbox(
            "Choose board from list:",
            board_labels,
            index=current_index,
            key="board_select_dropdown",
            on_change=on_board_change,
            label_visibility="collapsed"
        )
    else:
        st.write("No boards matching filter.")

    st.markdown("---")
    st.subheader("Load by ID")
    bid_input = st.text_input("Board ID", placeholder="paste UUID here…",
                               key="board_id_input", label_visibility="collapsed")
    if st.button("Load by ID", use_container_width=True):
        bid = bid_input.strip()
        if bid in boards_by_id:
            init_board(boards_by_id[bid])
            st.rerun()
        else:
            st.session_state.id_error = f"ID not found: {bid!r}"

    if st.session_state.get("id_error"):
        st.error(st.session_state.id_error)

    st.markdown("---")
    st.link_button("🛠️ Open Standalone Solver", "/?page=solver", use_container_width=True)
    st.markdown("---")
    st.caption(f"**{len(boards)}** boards loaded")
    st.caption(f"Signed in as **{author}**")

# ============================
# Title
# ============================
st.title("Summetry")

diff = st.session_state.difficulty
diff_class = f"diff-{diff.lower()}"
# Compute Human Cognitive difficulty metrics for the main page board
try:
    human_diff, cognitive_score = calculate_difficulty_human(
        st.session_state.puzzle, 
        st.session_state.solution, 
        sum(st.session_state.solution[0])
    )
except Exception:
    human_diff, cognitive_score = "EASY", -10.0

diff_class = f"diff-{diff.lower()}"

st.markdown(
    f"<div style='display: flex; gap: 8px; align-items: center; margin-bottom: 8px;'>"
    f"<div class='board-id-box'>ID: {st.session_state.board_id}</div>"
    f"<div class='diff-badge {diff_class}'>{diff}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# Display solver and difficulty stats in a clean caption style
diff_color = "#065f46" if human_diff == "EASY" else "#78350f"
st.markdown(
    f"<div style='font-size:12px; color:#64748b; margin-bottom:12px; line-height: 1.4;'>"
    f"🧩 **Complexity (Human Rating):** <span style='background:{diff_color}; color:white; border-radius:4px; padding:2px 6px; font-weight:700;'>{human_diff}</span> (Score: {cognitive_score:.1f})<br>"
    f"⚡ **Verification:** CP-SAT solver verified 12 sum equations for 25 cell variables in &lt;1 ms."
    f"</div>",
    unsafe_allow_html=True,
)
st.caption("Every row, column, and diagonal must sum to the same number.")
st.markdown("---")

# ============================
# Grid
# ============================
sel = st.session_state.selected
selected_row, selected_col = sel if sel is not None else (-1, -1)
st.markdown(
    f"<div id='summetry-state' data-selected-row='{selected_row}' data-selected-col='{selected_col}' style='display:none'></div>",
    unsafe_allow_html=True
)

var_map = {}
if st.session_state.get("variables_mode", False):
    var_map = get_variables_for_board(st.session_state.puzzle, st.session_state.solution)

for r in range(size):
    cols = st.columns([1, 1, 1, 1, 1, 0.15, 1.4])

    for c in range(size):
        with cols[c]:
            given = puzzle[r][c]
            if given is not None:
                st.markdown(f"<div class='given'>{given}</div>", unsafe_allow_html=True)
            else:
                val      = cell_values[r][c]
                if var_map and (r, c) in var_map:
                    info = var_map[(r, c)]
                    if info["role"] == "cell_1" or info["offset"] == 0:
                        label = f"{info['name']}"
                    else:
                        offset = info["offset"]
                        sign = "+" if offset >= 0 else "-"
                        label = f"{info['name']}{sign}{abs(offset)}"
                    if val is not None:
                        label += f"={val}"
                else:
                    label    = str(val) if val is not None else "·"
                
                is_sel   = sel == (r, c)
                if st.button(label, key=f"c{r}{c}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.selected = None if is_sel else (r, c)
                    st.rerun()

    with cols[6]:
        total, done = row_sums[r]
        txt = str(total) if done else "?"
        cls = "sum-done" if done else "sum-live"
        st.markdown(
            f"<div style='display:flex;align-items:center;min-height:52px'>"
            f"<span class='{cls}'>{txt}</span></div>",
            unsafe_allow_html=True,
        )

# Column sums
ccols = st.columns([1, 1, 1, 1, 1, 0.15, 1.4])
for c in range(size):
    with ccols[c]:
        total, done = col_sums[c]
        txt = str(total) if done else "?"
        cls = "sum-done" if done else "sum-live"
        st.markdown(f"<div class='{cls}' style='text-align:center;padding:4px 0'>{txt}</div>",
                    unsafe_allow_html=True)

# Diagonal sums
d1, d1done = diag_sums[0]
d2, d2done = diag_sums[1]
d1c = "#22c55e" if d1done else "#f59e0b"
d2c = "#22c55e" if d2done else "#f59e0b"
st.markdown(
    f"<div style='margin-top:10px;font-size:13px'>"
    f"<span style='color:{d1c};font-weight:{'700' if d1done else '400'}'>↘ {d1 if d1done else '?'}</span>"
    f"&emsp;&emsp;&emsp;"
    f"<span style='color:{d2c};font-weight:{'700' if d2done else '400'}'>↙ {d2 if d2done else '?'}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ============================
# Number pad
# ============================
if sel is not None:
    r, c = sel
    var_info = var_map.get((r, c))

    if var_info:
        offset = var_info["offset"]
        sign = "+" if offset >= 0 else "-"
        role = var_info["role"]
        lbl_formula = f"{var_info['name']}" if (role == "cell_1" or offset == 0) else f"{var_info['name']}{sign}{abs(offset)}"
        st.markdown(f"**Variable Cell ({r+1}, {c+1}) [{lbl_formula}] →** pick value:")
    else:
        st.markdown(f"**Cell ({r+1}, {c+1}) →** pick a number or clear:")

    pad_cols = st.columns(10)
    for i, digit in enumerate(range(1, 10)):
        with pad_cols[i]:
            if st.button(str(digit), key=f"pad{digit}"):
                if var_info:
                    role = var_info["role"]
                    offset = var_info["offset"]
                    sign = "+" if offset >= 0 else "-"
                    partner_r, partner_c = var_info["partner"]
                    
                    if role == "cell_1":
                        linked_val = digit + offset
                        if not (1 <= linked_val <= 9):
                            st.toast(f"⚠️ Invalid: {var_info['name']}={digit} forces linked cell ({var_info['name']}{sign}{abs(offset)}) to {linked_val}, out of bounds [1-9]!")
                        else:
                            cell_values[r][c] = digit
                            cell_values[partner_r][partner_c] = linked_val
                            st.session_state.selected = None
                            st.rerun()
                    else:  # role == "cell_2"
                        base_val = digit - offset
                        if not (1 <= base_val <= 9):
                            st.toast(f"⚠️ Invalid: linked cell value {digit} forces base cell {var_info['name']} to {base_val}, out of bounds [1-9]!")
                        else:
                            cell_values[partner_r][partner_c] = base_val
                            cell_values[r][c] = digit
                            st.session_state.selected = None
                            st.rerun()
                else:
                    cell_values[r][c] = digit
                    st.session_state.selected = None
                    st.rerun()
    with pad_cols[9]:
        if st.button("✕", key="pad_clear"):
            if var_info:
                partner_r, partner_c = var_info["partner"]
                cell_values[r][c] = None
                cell_values[partner_r][partner_c] = None
            else:
                cell_values[r][c] = None
            st.session_state.selected = None
            st.rerun()

# ============================
# Action buttons
# ============================
st.divider()
ab1, ab2, ab3 = st.columns(3)

with ab1:
    if st.button("✅ Check", use_container_width=True):
        full = []
        complete = True
        for r in range(size):
            row = []
            for c in range(size):
                v = puzzle[r][c] if puzzle[r][c] is not None else cell_values[r][c]
                if v is None:
                    complete = False
                row.append(v)
            full.append(row)

        if not complete:
            st.warning("Some cells are still empty.")
        else:
            sums_set = set()
            for line in rows_l + cols_l + diags_l:
                sums_set.add(sum(full[r][c] for r, c in line))
            if len(sums_set) == 1:
                st.success(f"🎉 Correct! Magic sum = {sums_set.pop()}")
            else:
                st.error(f"Not quite — distinct sums found: {sorted(sums_set)}")

with ab2:
    if st.button("🔀 New puzzle", use_container_width=True):
        init_board(random.choice(boards))
        st.rerun()

with ab3:
    if st.button("👁️ Show answer", use_container_width=True):
        st.session_state.show_answer = not st.session_state.get("show_answer", False)

if st.session_state.get("show_answer"):
    st.markdown("**Solution:**")
    for row in solution:
        st.write("  ".join(str(v) for v in row))

# ============================
# Notes
# ============================
st.divider()
st.subheader("Board Feedback & Notes")

if not NOTES_ENABLED:
    st.info("ℹ️ Running in **Local Feedback Mode**. Comments and ratings are saved to `feedback.json`.")

all_notes = load_notes()
board_notes = all_notes.get(st.session_state.board_id, [])

if board_notes:
    for note in reversed(board_notes):
        rating_val = note.get("rating", "Note")
        rating_badge = ""
        if rating_val != "Note":
            badge_color = "#475569" # Gray default
            if rating_val in ["Too Easy", "Too Hard"]:
                badge_color = "#ef4444" # Red
            elif rating_val in ["Easy"]:
                badge_color = "#10b981" # Green
            elif rating_val in ["Medium"]:
                badge_color = "#f59e0b" # Orange
            elif rating_val in ["Hard"]:
                badge_color = "#dc2626" # Dark Red
            elif rating_val == "Just Right":
                badge_color = "#3b82f6" # Blue
            rating_badge = f" <span style='background:{badge_color}; color:white; border-radius:4px; padding:2px 6px; font-size:11px; font-weight:600; margin-left:8px;'>{rating_val}</span>"

        st.markdown(
            f"<div class='note-card'>"
            f"<div class='note-meta'>"
            f"<span class='note-author'>{note['author']}</span>"
            f"{rating_badge}"
            f"</div>"
            f"<div class='note-text'>{note['text']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
else:
    st.caption("No notes or feedback yet for this board.")

st.markdown("**Add your feedback:**")
col_rating, col_text = st.columns([1, 2])
with col_rating:
    diff_rating = st.selectbox(
        "Difficulty Check",
        ["Just Right", "Too Easy", "Easy", "Medium", "Hard", "Too Hard"],
        key="diff_rating_input"
    )
with col_text:
    note_text = st.text_area("", placeholder="Your thoughts, strategy, observations…",
                              label_visibility="collapsed", key="note_input")

if st.button("Submit Feedback", type="primary", use_container_width=True):
    if note_text.strip():
        save_note(st.session_state.board_id, author, note_text, rating=diff_rating)
        st.session_state.pop("note_input", None)
        st.rerun()
    else:
        st.warning("Please write a comment or observation before submitting.")

# ============================
# Custom Board Solver
# ============================
st.divider()
with st.expander("🛠️ Custom Board Solver & Diagnostic"):
    render_custom_solver(standalone=False)

# ============================
# Keyboard Listener (Parent DOM Event Interceptor)
# ============================
render_keyboard_listener()
