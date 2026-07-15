# Summetry - 5x5 Magic Sum Logic Puzzle

Summetry is a premium 5x5 grid logic puzzle game where players arrange digits from 1 to 9 to satisfy mathematical symmetry across rows, columns, and diagonals. It is built as a self-contained, highly secure application with a Python FastAPI backend and a Svelte 5 frontend client.

---

## 🎮 What It Does
* **Gameplay:** Fill in the blank cells in the 5x5 grid so that all **5 rows**, **5 columns**, and **2 main diagonals** sum up to the exact same target **Magic Sum** (typically 34 or date-derived values).
* **Variables Mode:** Identifies grid deadlocks using a cognitive subtraction solver and links matching cells with algebraic variables (e.g. `x`, `x+2`, `y-1`). Changing one cell automatically updates and validates its mirrored counterpart in real-time.
* **Anti-Cheat:** Puzzle solutions are kept strictly on the backend. Grid answers are validated securely via server requests, preventing client-side inspecting cheats.

---

## 📂 Project Structure

```text
summetry-5x5/
├── README.md                 # Project documentation (The Front Door)
├── requirements.txt         # Python backend dependencies
├── package.json             # Root-level proxy scripts config
├── .env.example             # Local ports environment template
├── data/                    # JSON puzzle databases
│   ├── magic_boards2.json   # Base puzzle boards
│   ├── magic_boards_300.json# 300 daily puzzle queue
│   └── feedback.json        # Player feedback storage
├── backend/                 # FastAPI server & Streamlit UI
│   ├── app.py               # FastAPI entry point
│   └── summetry-UI.py       # Streamlit UI version
├── frontend/                # Svelte 5 & SvelteKit client
│   ├── src/                 # Client pages & components
│   ├── static/              # Global icons & styles
│   ├── package.json         # Svelte dependencies & scripts
│   └── vite.config.ts       # Vite configuration with proxy settings
└── scripts/                 # Solver tools & generator scripts
    ├── generate_boards.py   # Magic square puzzle generator
    └── validate_boards.py   # Heuristic checkers
```

---

## ⚡ How to Run It

### 1. Run the FastAPI Backend
Ensure Python 3.9+ is installed, then run:
```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server on port 8000
cd backend
uvicorn app:app --reload --port 8000
```
*Backend interactive docs will be available at `http://127.0.0.1:8000/docs`.*

### 2. Run the Svelte Frontend
Ensure Node.js 18+ is installed, then run:
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev -- --open
```
*Svelte frontend will open automatically at `http://localhost:5173/`.*

---

## 📡 API Endpoints

### 1. Get Daily Clues
* **Endpoint:** `GET /api/board/daily`
* **Response (Clues Only - secure):**
  ```json
  {
    "board_id": "e6a8b51b-0c08-1a1a-c4b1-ba2af8c1b352",
    "difficulty": "Easy",
    "puzzle": [
      [null, 1, 1, null, 2],
      [1, null, 1, 3, 4],
      [null, 2, 5, 1, 3],
      [7, 1, 1, 1, null],
      [null, null, null, 1, null]
    ],
    "variables": {}
  }
  ```

### 2. Verify Solution
* **Endpoint:** `POST /api/board/check`
* **Request Payload:**
  ```json
  {
    "board_id": "e6a8b51b-0c08-1a1a-c4b1-ba2af8c1b352",
    "grid": [...]
  }
  ```
* **Response:**
  ```json
  {
    "correct": true,
    "magic_sum": 25
  }
  ```

### 3. CP-SAT Solver (Diagnostics)
* **Endpoint:** `POST /api/solver/solve`
* **Request Payload (User's custom grid layout):**
  ```json
  {
    "puzzle": [...]
  }
  ```
* **Response:**
  ```json
  {
    "solutions_count": 1,
    "solutions": [...],
    "branches": 5,
    "conflicts": 0,
    "elapsed_ms": 0.5,
    "human_difficulty": "EASY"
  }
  ```

---

## 🧠 Board & Model Logic

### 1. CP-SAT Constraint Programming Solver
The backend uses **Google OR-Tools (CP-SAT)** in Python to solve grid constraints. It translates the puzzle grid into integer variables (domain 1-9) and enforces 12 sum equations:
* 5 Row sums == Magic Sum
* 5 Column sums == Magic Sum
* 2 Diagonal sums == Magic Sum

### 2. Human Cognitive Heuristic
The difficulty rating is computed using a **subtraction simulation**:
* The algorithm looks for any row/col/diagonal with exactly 4 clues (only 1 cell missing) and fills it.
* If it gets "stuck" (all lines have 2+ missing cells), the deadlock counter increment.
* Complexity Score = `-2 * stuck_count + 2 * initial_4_clue_lines - 1 * diag_clues - 0.1 * target_sum`.
* Score $\ge -6.0$ is rated as **MEDIUM**, otherwise **EASY**.

---

## 🔮 Future Improvements
* **Progress Syncing:** Connect to Google Sheets or an SQLite database to sync player statistics across devices.
* **Symmetry Check Visualizer:** Highlight cells when selected to show exactly which mirror cell they are algebraically linked to.
