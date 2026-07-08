<script lang="ts">
  import { onMount } from 'svelte';
  import boards from '$lib/data/magic_boards2.json';
  import boards_300 from '$lib/data/magic_boards_300.json';

  let solverGrid = $state<(string)[][]>(Array(5).fill(null).map(() => Array(5).fill('')));
  let searchId = $state('');
  let loadStatus = $state('');
  
  // Solver Statistics
  let isSolving = $state(false);
  let solutions = $state<number[][][]>([]);
  let elapsedMs = $state(0);
  let variablesCount = $state(26);
  let constraintsCount = $state(12);
  let branchesCount = $state(0);
  let humanDiffRating = $state('');

  function handleCellInput(r: number, c: number, val: string) {
    const cleanVal = val.replace(/[^1-9]/g, '');
    solverGrid[r][c] = cleanVal.slice(0, 1);
  }

  function loadBoardById() {
    loadStatus = '';
    const cleanId = searchId.trim();
    if (!cleanId) {
      loadStatus = '⚠️ Please enter a Board ID.';
      return;
    }

    // Search main queue (supports full UUID or 8-character prefix)
    let found = boards.find((b: any) => b.board_id === cleanId || b.board_id.startsWith(cleanId));
    if (!found) {
      // Search 300 database
      found = boards_300.find((b: any) => b.board_id === cleanId || b.board_id.startsWith(cleanId));
    }

    if (found) {
      const puzzle = found.puzzle;
      for (let r = 0; r < 5; r++) {
        for (let c = 0; c < 5; c++) {
          solverGrid[r][c] = puzzle[r][c] !== null ? String(puzzle[r][c]) : '';
        }
      }
      loadStatus = '✅ Loaded board clues successfully!';
    } else {
      loadStatus = '❌ Board ID not found in daily queue or 300-boards database.';
    }
  }

  // ---------------------------------------------------------------------------
  // Backtracking Solver Algorithm
  // ---------------------------------------------------------------------------
  function runSolver() {
    isSolving = true;
    solutions = [];
    branchesCount = 0;
    humanDiffRating = '';
    
    const startTime = performance.now();
    const puzzle = solverGrid.map(row => row.map(v => v !== '' ? parseInt(v) : null));

    // Determine target sum M if possible, otherwise we will test candidates
    let targetM: number | null = null;
    
    // Check if any full row/col/diag exists to pin M
    for (let r = 0; r < 5; r++) {
      if (puzzle[r].every(v => v !== null)) {
        targetM = puzzle[r].reduce((a, b) => a! + b!, 0);
        break;
      }
    }
    if (targetM === null) {
      for (let c = 0; c < 5; c++) {
        const col = [0, 1, 2, 3, 4].map(r => puzzle[r][c]);
        if (col.every(v => v !== null)) {
          targetM = col.reduce((a, b) => a! + b!, 0);
          break;
        }
      }
    }

    const mCandidates = targetM !== null ? [targetM] : Array.from({ length: 41 }, (_, i) => i + 5); // 5 to 45
    const workingGrid = puzzle.map(row => [...row]);

    outer: for (const M of mCandidates) {
      const results: number[][][] = [];
      backtrack(0, 0, M, workingGrid, puzzle, results);
      if (results.length > 0) {
        solutions.push(...results);
        if (solutions.length >= 5) break outer;
      }
    }

    elapsedMs = Math.round(performance.now() - startTime);
    isSolving = false;

    if (solutions.length > 0) {
      // Calculate human difficulty of the custom layout using the first solution
      const firstSol = solutions[0];
      const magicSum = firstSol[0].reduce((a, b) => a + b, 0);
      humanDiffRating = calculateDifficultyHuman(puzzle, firstSol, magicSum);
    }
  }

  function backtrack(r: number, c: number, M: number, grid: (number | null)[][], puzzle: (number | null)[][], results: number[][][]) {
    if (results.length >= 5) return;
    branchesCount++;

    if (r === 5) {
      // Validate diagonals
      const d1 = [0, 1, 2, 3, 4].reduce((a, i) => a + grid[i][i]!, 0);
      const d2 = [0, 1, 2, 3, 4].reduce((a, i) => a + grid[i][4 - i]!, 0);
      if (d1 === M && d2 === M) {
        results.push(grid.map(row => row.map(v => v!)));
      }
      return;
    }

    const nextR = c === 4 ? r + 1 : r;
    const nextC = c === 4 ? 0 : c + 1;

    if (puzzle[r][c] !== null) {
      // Pre-filled clue, validate pruning
      if (c === 4) {
        const rowSum = grid[r].reduce((a, b) => a! + b!, 0);
        if (rowSum !== M) return;
      }
      if (r === 4) {
        const colSum = [0, 1, 2, 3, 4].reduce((a, ri) => a + grid[ri][c]!, 0);
        if (colSum !== M) return;
      }
      backtrack(nextR, nextC, M, grid, puzzle, results);
    } else {
      // Try digits 1-9
      for (let val = 1; val <= 9; val++) {
        grid[r][c] = val;

        // Pruning validation: Row check
        if (c === 4) {
          const rowSum = grid[r].reduce((a, b) => a! + b!, 0);
          if (rowSum !== M) continue;
        } else {
          const partialRowSum = grid[r].slice(0, c + 1).reduce((a, b) => a! + b!, 0)!;
          const remainingCells = 4 - c;
          if (partialRowSum + remainingCells * 1 > M || partialRowSum + remainingCells * 9 < M) {
            continue;
          }
        }

        // Pruning validation: Column check
        if (r === 4) {
          const colSum = [0, 1, 2, 3, 4].reduce((a, ri) => a + grid[ri][c]!, 0);
          if (colSum !== M) continue;
        } else {
          const partialColSum = [0, 1, 2, 3, 4].slice(0, r + 1).reduce((a, ri) => a + grid[ri][c]!, 0);
          const remainingCells = 4 - r;
          if (partialColSum + remainingCells * 1 > M || partialColSum + remainingCells * 9 < M) {
            continue;
          }
        }

        backtrack(nextR, nextC, M, grid, puzzle, results);
      }
      grid[r][c] = null; // reset
    }
  }

  // ---------------------------------------------------------------------------
  // Human Solver Heuristics
  // ---------------------------------------------------------------------------
  function simulateSubtractionSolve(puzzle: (number | null)[][], solution: number[][]): number {
    const grid = puzzle.map(row => [...row]);
    let stuckCount = 0;
    while (true) {
      const emptyCells: { r: number; c: number }[] = [];
      for (let r = 0; r < 5; r++) {
        for (let c = 0; c < 5; c++) {
          if (grid[r][c] === null) emptyCells.push({ r, c });
        }
      }
      if (emptyCells.length === 0) break;
      
      let foundLine = null;
      for (let r = 0; r < 5; r++) {
        if (grid[r].filter(v => v !== null).length === 4) {
          foundLine = { r, c: grid[r].indexOf(null) };
          break;
        }
      }
      if (!foundLine) {
        for (let c = 0; c < 5; c++) {
          const colVals = [0, 1, 2, 3, 4].map(r => grid[r][c]);
          if (colVals.filter(v => v !== null).length === 4) {
            foundLine = { r: colVals.indexOf(null), c };
            break;
          }
        }
      }
      if (!foundLine) {
        const d1Vals = [0, 1, 2, 3, 4].map(i => grid[i][i]);
        if (d1Vals.filter(v => v !== null).length === 4) {
          foundLine = { r: d1Vals.indexOf(null), c: d1Vals.indexOf(null) };
        }
      }
      if (!foundLine) {
        const d2Vals = [0, 1, 2, 3, 4].map(i => grid[i][4 - i]);
        if (d2Vals.filter(v => v !== null).length === 4) {
          const missingIdx = d2Vals.indexOf(null);
          foundLine = { r: missingIdx, c: 4 - missingIdx };
        }
      }
      
      if (foundLine) {
        grid[foundLine.r][foundLine.c] = solution[foundLine.r][foundLine.c];
      } else {
        stuckCount++;
        const target = emptyCells[0];
        grid[target.r][target.c] = solution[target.r][target.c];
      }
    }
    return stuckCount;
  }

  function calculateDifficultyHuman(puzzle: (number | null)[][], solution: number[][], targetSum: number): string {
    const stuck = simulateSubtractionSolve(puzzle, solution);
    
    let clueLines = 0;
    for (let r = 0; r < 5; r++) {
      if (puzzle[r].filter(v => v !== null).length === 4) clueLines++;
    }
    for (let c = 0; c < 5; c++) {
      const colVals = [0, 1, 2, 3, 4].map(r => puzzle[r][c]);
      if (colVals.filter(v => v !== null).length === 4) clueLines++;
    }
    const d1 = [0, 1, 2, 3, 4].map(i => puzzle[i][i]);
    if (d1.filter(v => v !== null).length === 4) clueLines++;
    const d2 = [0, 1, 2, 3, 4].map(i => puzzle[i][4 - i]);
    if (d2.filter(v => v !== null).length === 4) clueLines++;

    let diagClues = 0;
    for (let i = 0; i < 5; i++) {
      if (puzzle[i][i] !== null) diagClues++;
      if (puzzle[i][4 - i] !== null) diagClues++;
    }

    const score = -2 * stuck + 2 * clueLines - 1 * diagClues - 0.1 * targetSum;
    return score >= -6.0 ? 'MEDIUM' : 'EASY';
  }

  function clearSolverGrid() {
    solverGrid = Array(5).fill(null).map(() => Array(5).fill(''));
    solutions = [];
    humanDiffRating = '';
  }

  onMount(() => {
    // Arrow keys listener for cell input grid
    const handleArrowNavigation = (e: KeyboardEvent) => {
      const active = document.activeElement;
      if (active && active.tagName === 'INPUT' && active.classList.contains('solver-input')) {
        const r = parseInt(active.getAttribute('data-row') || '0');
        const c = parseInt(active.getAttribute('data-col') || '0');
        let nextEl: HTMLInputElement | null = null;
        if (e.key === 'ArrowUp') {
          nextEl = document.querySelector(`input[data-row="${r-1}"][data-col="${c}"]`);
        } else if (e.key === 'ArrowDown') {
          nextEl = document.querySelector(`input[data-row="${r+1}"][data-col="${c}"]`);
        } else if (e.key === 'ArrowLeft') {
          nextEl = document.querySelector(`input[data-row="${r}"][data-col="${c-1}"]`);
        } else if (e.key === 'ArrowRight') {
          nextEl = document.querySelector(`input[data-row="${r}"][data-col="${c+1}"]`);
        }
        if (nextEl) {
          e.preventDefault();
          nextEl.focus();
          nextEl.select();
        }
      }
    };
    window.addEventListener('keydown', handleArrowNavigation);
    return () => window.removeEventListener('keydown', handleArrowNavigation);
  });
</script>

<div class="solver-container">
  <header class="header">
    <h1>🛠️ Standalone Solver & Diagnostics</h1>
    <a href="/" class="back-link">🎮 Back to Main Game</a>
  </header>

  <section class="load-by-id-section">
    <h3>🔍 Load Board by ID</h3>
    <div class="search-bar">
      <input 
        type="text" 
        placeholder="Enter Board ID (UUID)..." 
        bind:value={searchId}
      />
      <button class="search-btn" on:click={loadBoardById}>Load Clues</button>
    </div>
    {#if loadStatus}
      <p class="status-msg">{loadStatus}</p>
    {/if}
  </section>

  <section class="grid-section">
    <h3>🎛️ Input Grid & Controls</h3>
    <div class="grid-box">
      {#each solverGrid as row, r}
        <div class="grid-row">
          {#each row as val, c}
            <input 
              type="text" 
              class="solver-input"
              data-row={r}
              data-col={c}
              value={val}
              maxlength="1"
              on:input={(e) => handleCellInput(r, c, e.currentTarget.value)}
              on:focus={(e) => e.currentTarget.select()}
            />
          {/each}
        </div>
      {/each}
    </div>

    <div class="action-row">
      <button class="solve-btn" on:click={runSolver} disabled={isSolving}>
        {isSolving ? '⚡ Solving...' : '✅ Solve Board'}
      </button>
      <button class="clear-btn" on:click={clearSolverGrid}>🧹 Clear Grid</button>
    </div>
  </section>

  {#if solutions.length > 0}
    <section class="results-section">
      <div class="results-header">
        <h2>🎉 Found {solutions.length} valid completion(s) in {elapsedMs} ms!</h2>
        {#if humanDiffRating}
          <div class="diff-rating">
            Complexity (Human Rating): 
            <span class="badge {humanDiffRating.toLowerCase()}">{humanDiffRating}</span>
          </div>
        {/if}
      </div>

      <div class="stats-box">
        <h3>🧠 Solver Statistics:</h3>
        <ul>
          <li>Variables Evaluated: <strong>{variablesCount}</strong> (25 grid cells + magic sum)</li>
          <li>Constraints Enforced: <strong>{constraintsCount}</strong> magic sum equations</li>
          <li>Search Branches Evaluated: <strong>{branchesCount}</strong></li>
        </ul>
      </div>

      <div class="solutions-grid">
        {#each solutions as sol, idx}
          <div class="solution-card">
            <h4>Solution #{idx + 1} (Magic Sum = {sol[0].reduce((a, b) => a + b, 0)}):</h4>
            <div class="matrix">
              {#each sol as solRow, rIdx}
                <div class="matrix-row">
                  {#each solRow as val, cIdx}
                    <span class="matrix-cell" class:given={solverGrid[rIdx][cIdx] !== ''}>{val}</span>
                  {/each}
                </div>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </section>
  {:else if elapsedMs > 0 && !isSolving}
    <p class="no-solution">❌ No valid solution exists for this board configuration!</p>
  {/if}
</div>

<style>
  .solver-container {
    max-width: 600px;
    margin: 0 auto;
    padding: 24px 16px;
    color: #f1f5f9;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #334155;
    padding-bottom: 16px;
    margin-bottom: 24px;
  }

  .header h1 {
    font-size: 1.6rem;
    font-weight: 800;
    margin: 0;
  }

  .back-link {
    background: #1e293b;
    border: 1px solid #475569;
    color: #f1f5f9;
    padding: 8px 16px;
    border-radius: 8px;
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .back-link:hover {
    background: #334155;
  }

  h3 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #38bdf8;
    margin-top: 0;
    margin-bottom: 12px;
  }

  .load-by-id-section {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
  }

  .search-bar {
    display: flex;
    gap: 8px;
  }

  .search-bar input {
    flex: 1;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 14px;
    color: #f1f5f9;
    outline: none;
  }

  .search-bar input:focus {
    border-color: #3b82f6;
  }

  .search-btn {
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    cursor: pointer;
  }

  .search-btn:hover {
    background: #2563eb;
  }

  .status-msg {
    margin: 8px 0 0 0;
    font-size: 0.85rem;
    font-weight: 500;
  }

  .grid-section {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }

  .grid-box {
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: center;
    margin-bottom: 20px;
  }

  .grid-row {
    display: flex;
    gap: 6px;
  }

  .solver-input {
    width: 50px;
    height: 50px;
    background: #1e293b;
    border: 1px solid #475569;
    color: #f1f5f9;
    border-radius: 8px;
    text-align: center;
    font-size: 1.4rem;
    font-weight: 700;
    outline: none;
  }

  .solver-input:focus {
    border-color: #3b82f6;
    background: #1e293b;
  }

  .action-row {
    display: flex;
    gap: 12px;
    justify-content: center;
  }

  .solve-btn {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 32px;
    font-weight: 700;
    cursor: pointer;
    font-size: 1rem;
  }

  .solve-btn:hover {
    background: #1d4ed8;
  }

  .solve-btn:disabled {
    background: #4b5563;
    cursor: not-allowed;
  }

  .clear-btn {
    background: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 600;
    cursor: pointer;
  }

  .clear-btn:hover {
    background: #334155;
  }

  .results-section {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
  }

  .results-header h2 {
    font-size: 1.25rem;
    color: #22c55e;
    margin-top: 0;
    margin-bottom: 8px;
  }

  .diff-rating {
    font-size: 0.9rem;
    color: #94a3b8;
    margin-bottom: 16px;
  }

  .badge {
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 0.8rem;
    color: white;
  }

  .badge.easy {
    background: #065f46;
  }

  .badge.medium {
    background: #78350f;
  }

  .stats-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;
  }

  .stats-box h3 {
    margin: 0 0 8px 0;
    font-size: 0.95rem;
    color: #38bdf8;
  }

  .stats-box ul {
    margin: 0;
    padding-left: 20px;
    font-size: 0.9rem;
    color: #cbd5e1;
  }

  .stats-box li {
    margin-bottom: 4px;
  }

  .solutions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
  }

  .solution-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 16px;
  }

  .solution-card h4 {
    margin-top: 0;
    margin-bottom: 12px;
    font-size: 0.9rem;
    color: #e2e8f0;
  }

  .matrix {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
  }

  .matrix-row {
    display: flex;
    gap: 4px;
  }

  .matrix-cell {
    width: 32px;
    height: 32px;
    background: #0f172a;
    border: 1px solid #1e293b;
    color: #22c55e;
    font-weight: 700;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
  }

  .matrix-cell.given {
    background: #2563eb;
    border-color: #1d4ed8;
    color: white;
  }

  .no-solution {
    text-align: center;
    color: #ef4444;
    font-weight: 700;
    font-size: 1.1rem;
    margin-top: 16px;
  }
</style>
