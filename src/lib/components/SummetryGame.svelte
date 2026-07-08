<script lang="ts">
  import { onMount } from 'svelte';
  import HelpModal from './HelpModal.svelte';
  import StatsModal from './StatsModal.svelte';
  import ShareSummary from './ShareSummary.svelte';
  import boards from '$lib/data/magic_boards2.json';

  // ---------------------------------------------------------------------------
  // Types & Interfaces
  // ---------------------------------------------------------------------------
  type GameMode = 'daily' | 'practice';
  type GameStatus = 'starting' | 'typing' | 'checking' | 'revealing' | 'won' | 'lost';

  interface Cell {
    val: number | null;
    isClue: boolean;
  }

  interface GameSession {
    seed: number;
    startSeed: number;
    sessionToken: string;
    status: GameStatus;
    grid: Cell[][];
    boardId: string;
    difficulty: string;
    magicSum: number;
    solveTime: number; // elapsed time in seconds
    showAnswer: boolean;
    solution: number[][];
  }

  // ---------------------------------------------------------------------------
  // Config & Props
  // ---------------------------------------------------------------------------
  let { defaultMode = 'daily' } = $props();

  // ---------------------------------------------------------------------------
  // Core Game State
  // ---------------------------------------------------------------------------
  let mode = $state<GameMode>(defaultMode);
  let session = $state<GameSession | null>(null);
  let selectedCell = $state<{ r: number; c: number } | null>(null);
  let timerInterval: any = null;

  // Modals visibility state
  let showHelp = $state(false);
  let showStats = $state(false);

  // ---------------------------------------------------------------------------
  // Math & Solver Helpers
  // ---------------------------------------------------------------------------
  function getTodayIndex(total: number): number {
    const today = new Date();
    const dayOfYear = Math.floor((today.getTime() - new Date(today.getFullYear(), 0, 0).getTime()) / 86400000);
    return dayOfYear % total;
  }

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
      // Check rows
      for (let r = 0; r < 5; r++) {
        if (grid[r].filter(v => v !== null).length === 4) {
          foundLine = { r, c: grid[r].indexOf(null) };
          break;
        }
      }
      // Check cols
      if (!foundLine) {
        for (let c = 0; c < 5; c++) {
          const colVals = [0, 1, 2, 3, 4].map(r => grid[r][c]);
          if (colVals.filter(v => v !== null).length === 4) {
            foundLine = { r: colVals.indexOf(null), c };
            break;
          }
        }
      }
      // Check diag1
      if (!foundLine) {
        const d1Vals = [0, 1, 2, 3, 4].map(i => grid[i][i]);
        if (d1Vals.filter(v => v !== null).length === 4) {
          foundLine = { r: d1Vals.indexOf(null), c: d1Vals.indexOf(null) };
        }
      }
      // Check diag2
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

  function calculateDifficultyHuman(puzzle: (number | null)[][], solution: number[][], targetSum: number): { rating: string; score: number } {
    const stuck = simulateSubtractionSolve(puzzle, solution);
    
    // Initial 4-clue lines
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

    // Diagonal clues
    let diagClues = 0;
    for (let i = 0; i < 5; i++) {
      if (puzzle[i][i] !== null) diagClues++;
      if (puzzle[i][4 - i] !== null) diagClues++;
    }

    const score = -2 * stuck + 2 * clueLines - 1 * diagClues - 0.1 * targetSum;
    return {
      rating: score >= -6.0 ? 'MEDIUM' : 'EASY',
      score
    };
  }

  // ---------------------------------------------------------------------------
  // Stats & LocalStorage Helpers
  // ---------------------------------------------------------------------------
  function saveSession(s: GameSession) {
    const key = mode === 'daily' ? `summetry-daily-${new Date().toDateString()}` : 'summetry-practice';
    localStorage.setItem(key, JSON.stringify(s));
  }

  function loadSession(): GameSession | null {
    const key = mode === 'daily' ? `summetry-daily-${new Date().toDateString()}` : 'summetry-practice';
    try {
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  function updateGlobalStats(won: boolean, solveTime: number) {
    try {
      const stored = localStorage.getItem('summetry-stats');
      let stats = stored ? JSON.parse(stored) : { played: 0, won: 0, currentStreak: 0, maxStreak: 0, solveTimes: [] };
      stats.played += 1;
      if (won) {
        stats.won += 1;
        stats.currentStreak += 1;
        stats.maxStreak = Math.max(stats.currentStreak, stats.maxStreak);
        stats.solveTimes.push(solveTime);
      } else {
        stats.currentStreak = 0;
      }
      localStorage.setItem('summetry-stats', JSON.stringify(stats));
    } catch (e) {
      console.error(e);
    }
  }

  // ---------------------------------------------------------------------------
  // Game Flow
  // ---------------------------------------------------------------------------
  function startNewGame(boardData: any) {
    if (timerInterval) clearInterval(timerInterval);

    const puzzle = boardData.puzzle;
    const solution = boardData.solution;
    const magicSum = solution ? sumRow(solution[0]) : 34;

    const sessionGrid: Cell[][] = [];
    for (let r = 0; r < 5; r++) {
      const row: Cell[] = [];
      for (let c = 0; c < 5; c++) {
        row.push({
          val: puzzle[r][c],
          isClue: puzzle[r][c] !== null
        });
      }
      sessionGrid.push(row);
    }

    const seed = Math.floor(Math.random() * 1000000);
    session = {
      seed,
      startSeed: seed,
      sessionToken: Math.random().toString(36).substring(2),
      status: 'typing',
      grid: sessionGrid,
      boardId: boardData.board_id || String(seed),
      difficulty: boardData.difficulty || 'Easy',
      magicSum,
      solveTime: 0,
      showAnswer: false,
      solution
    };

    selectedCell = null;
    saveSession(session);

    timerInterval = setInterval(() => {
      if (session && session.status === 'typing') {
        session.solveTime += 1;
        saveSession(session);
      }
    }, 1000);
  }

  function sumRow(row: (number | null)[]): number {
    return row.reduce((a, b) => (a || 0) + (b || 0), 0) || 0;
  }

  function getRowSum(rIdx: number): { sum: number; complete: boolean } {
    if (!session) return { sum: 0, complete: false };
    const rowVals = session.grid[rIdx].map(c => c.val);
    const complete = rowVals.every(v => v !== null);
    const sum = rowVals.reduce((a, b) => (a || 0) + (b || 0), 0) || 0;
    return { sum, complete };
  }

  function getColSum(cIdx: number): { sum: number; complete: boolean } {
    if (!session) return { sum: 0, complete: false };
    const colVals = [0, 1, 2, 3, 4].map(r => session!.grid[r][cIdx].val);
    const complete = colVals.every(v => v !== null);
    const sum = colVals.reduce((a, b) => (a || 0) + (b || 0), 0) || 0;
    return { sum, complete };
  }

  function getDiag1Sum(): { sum: number; complete: boolean } {
    if (!session) return { sum: 0, complete: false };
    const dVals = [0, 1, 2, 3, 4].map(i => session!.grid[i][i].val);
    const complete = dVals.every(v => v !== null);
    const sum = dVals.reduce((a, b) => (a || 0) + (b || 0), 0) || 0;
    return { sum, complete };
  }

  function getDiag2Sum(): { sum: number; complete: boolean } {
    if (!session) return { sum: 0, complete: false };
    const dVals = [0, 1, 2, 3, 4].map(i => session!.grid[i][4 - i].val);
    const complete = dVals.every(v => v !== null);
    const sum = dVals.reduce((a, b) => (a || 0) + (b || 0), 0) || 0;
    return { sum, complete };
  }

  function handleCheck() {
    if (!session) return;
    
    // Ensure session integrity
    if (session.seed !== session.startSeed) {
      alert("Session corruption detected. Restarting cleanly.");
      loadActiveBoard();
      return;
    }

    let allFilled = true;
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        if (session.grid[r][c].val === null) {
          allFilled = false;
        }
      }
    }

    if (!allFilled) {
      alert("⚠️ Some cells are still empty!");
      return;
    }

    const sums = new Set<number>();
    for (let r = 0; r < 5; r++) sums.add(getRowSum(r).sum);
    for (let c = 0; c < 5; c++) sums.add(getColSum(c).sum);
    sums.add(getDiag1Sum().sum);
    sums.add(getDiag2Sum().sum);

    if (sums.size === 1) {
      session.status = 'won';
      if (timerInterval) clearInterval(timerInterval);
      saveSession(session);
      updateGlobalStats(true, session.solveTime);
    } else {
      alert("❌ The sums do not match on all rows, columns, and diagonals!");
    }
  }

  function handleInputDigit(val: number) {
    if (!session || session.status !== 'typing' || !selectedCell) return;
    const { r, c } = selectedCell;
    if (session.grid[r][c].isClue) return;

    session.grid[r][c].val = val;
    saveSession(session);
  }

  function handleClear() {
    if (!session || session.status !== 'typing' || !selectedCell) return;
    const { r, c } = selectedCell;
    if (session.grid[r][c].isClue) return;

    session.grid[r][c].val = null;
    saveSession(session);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!session || session.status !== 'typing') return;
    
    if (e.key >= '1' && e.key <= '9') {
      handleInputDigit(parseInt(e.key));
    } else if (e.key === 'Backspace' || e.key === 'Delete') {
      handleClear();
    } else if (e.key.startsWith('Arrow') && selectedCell) {
      e.preventDefault();
      let { r, c } = selectedCell;
      if (e.key === 'ArrowUp') r = Math.max(0, r - 1);
      else if (e.key === 'ArrowDown') r = Math.min(4, r + 1);
      else if (e.key === 'ArrowLeft') c = Math.max(0, c - 1);
      else if (e.key === 'ArrowRight') c = Math.min(4, c + 1);
      selectedCell = { r, c };
    }
  }

  function handleCellClick(r: number, c: number) {
    if (!session || session.status !== 'typing') return;
    selectedCell = { r, c };
  }

  function toggleMode(newMode: GameMode) {
    mode = newMode;
    loadActiveBoard();
  }

  function loadActiveBoard() {
    const saved = loadSession();
    if (saved) {
      session = saved;
      if (timerInterval) clearInterval(timerInterval);
      if (session.status === 'typing') {
        timerInterval = setInterval(() => {
          if (session) {
            session.solveTime += 1;
            saveSession(session);
          }
        }, 1000);
      }
    } else {
      if (mode === 'daily') {
        const boardIdx = getTodayIndex(boards.length);
        startNewGame(boards[boardIdx]);
      } else {
        const randomBoard = boards[Math.floor(Math.random() * boards.length)];
        startNewGame(randomBoard);
      }
    }
  }

  onMount(() => {
    loadActiveBoard();
    window.addEventListener('keydown', handleKeydown);

    return () => {
      window.removeEventListener('keydown', handleKeydown);
      if (timerInterval) clearInterval(timerInterval);
    };
  });
</script>

<div class="game-container">
  <header class="header">
    <div class="header-left">
      <h1>Summetry</h1>
      <div class="mode-toggle">
        <button class:active={mode === 'daily'} on:click={() => toggleMode('daily')}>📅 Daily</button>
        <button class:active={mode === 'practice'} on:click={() => toggleMode('practice')}>🔀 Practice</button>
      </div>
    </div>
    <div class="header-right">
      <button class="icon-btn" on:click={() => showHelp = true}>❓ Help</button>
      <button class="icon-btn" on:click={() => showStats = true}>📊 Stats</button>
    </div>
  </header>

  {#if session}
    <div class="puzzle-info">
      <div class="badge-row">
        <span class="info-badge">ID: {session.boardId.slice(0, 8)}</span>
        <span class="info-badge uppercase {session.difficulty.toLowerCase()}">{session.difficulty}</span>
        {#if session.solveTime > 0}
          <span class="info-badge timer">⏱️ {Math.floor(session.solveTime / 60)}:{(session.solveTime % 60) < 10 ? '0' : ''}{session.solveTime % 60}</span>
        {/if}
      </div>
    </div>

    <!-- The 5x5 Grid Layout with live sum guides -->
    <div class="board-wrapper">
      <div class="diag-guide top-left" class:match={getDiag1Sum().sum === session.magicSum && getDiag1Sum().complete}>
        {getDiag1Sum().sum}
      </div>
      <div class="diag-guide top-right" class:match={getDiag2Sum().sum === session.magicSum && getDiag2Sum().complete}>
        {getDiag2Sum().sum}
      </div>

      <div class="grid-layout">
        {#each session.grid as row, rIdx}
          <div class="grid-row">
            {#each row as cell, cIdx}
              <button 
                class="grid-cell"
                class:clue={cell.isClue}
                class:selected={selectedCell?.r === rIdx && selectedCell?.c === cIdx}
                on:click={() => handleCellClick(rIdx, cIdx)}
              >
                {cell.val || ''}
              </button>
            {/each}
            
            <!-- Row Sum Guide -->
            <div class="sum-guide row-guide" class:match={getRowSum(rIdx).sum === session!.magicSum && getRowSum(rIdx).complete}>
              {getRowSum(rIdx).sum}
            </div>
          </div>
        {/each}

        <!-- Column Sum Guides -->
        <div class="grid-row col-sums-row">
          {#each [0, 1, 2, 3, 4] as cIdx}
            <div class="sum-guide col-guide" class:match={getColSum(cIdx).sum === session!.magicSum && getColSum(cIdx).complete}>
              {getColSum(cIdx).sum}
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Control Buttons -->
    <div class="controls-panel">
      {#if session.status === 'typing'}
        <button class="primary-btn check-btn" on:click={handleCheck}>✅ Check Solution</button>
        <button class="secondary-btn" on:click={() => session!.showAnswer = !session!.showAnswer}>
          {session.showAnswer ? '👁️ Hide Answer' : '👁️ Show Answer'}
        </button>
      {/if}

      {#if mode === 'practice'}
        <button class="secondary-btn" on:click={() => startNewGame(boards[Math.floor(Math.random() * boards.length)])}>
          🔀 New Practice Game
        </button>
      {/if}
    </div>

    {#if session.showAnswer}
      <div class="solution-box">
        <h3>💡 Solution Matrix:</h3>
        <div class="solution-grid">
          {#each session.solution as solRow}
            <div class="solution-row">
              {#each solRow as num}
                <span class="solution-cell">{num}</span>
              {/each}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#if session.status === 'won'}
      <ShareSummary 
        puzzle={session.grid.map(r => r.map(c => c.val))}
        boardId={session.boardId}
        solveTime={session.solveTime}
        magicSum={session.magicSum}
        difficulty={session.difficulty}
      />
    {/if}
  {/if}

  <!-- Modals -->
  {#if showHelp}
    <HelpModal on:close={() => showHelp = false} />
  {/if}
  {#if showStats}
    <StatsModal on:close={() => showStats = false} />
  {/if}
</div>

<style>
  .game-container {
    max-width: 500px;
    margin: 0 auto;
    padding: 16px;
    color: #f1f5f9;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .header h1 {
    margin: 0 0 8px 0;
    font-size: 1.8rem;
    font-weight: 800;
    color: #f1f5f9;
  }

  .mode-toggle {
    display: flex;
    background: #1e293b;
    border-radius: 8px;
    padding: 2px;
    width: fit-content;
  }

  .mode-toggle button {
    background: none;
    border: none;
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }

  .mode-toggle button.active {
    background: #3b82f6;
    color: white;
  }

  .icon-btn {
    background: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    margin-left: 8px;
  }

  .icon-btn:hover {
    background: #334155;
  }

  .puzzle-info {
    margin-bottom: 16px;
  }

  .badge-row {
    display: flex;
    gap: 8px;
  }

  .info-badge {
    background: #1e293b;
    color: #94a3b8;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 600;
    font-family: monospace;
  }

  .info-badge.uppercase {
    text-transform: uppercase;
  }

  .info-badge.easy {
    background: #065f46;
    color: #a7f3d0;
  }

  .info-badge.medium {
    background: #78350f;
    color: #fef3c7;
  }

  .info-badge.hard {
    background: #7f1d1d;
    color: #fee2e2;
  }

  .board-wrapper {
    position: relative;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  }

  .grid-layout {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .grid-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .grid-cell {
    width: 54px;
    height: 54px;
    background: #1e293b;
    border: 1px solid #475569;
    color: #f1f5f9;
    border-radius: 8px;
    font-size: 1.4rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    outline: none;
    transition: all 0.1s;
  }

  .grid-cell.clue {
    background: #0f172a;
    border-color: #1e293b;
    color: #64748b;
    cursor: not-allowed;
  }

  .grid-cell.selected {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.5);
    background: #1e293b;
  }

  .sum-guide {
    width: 32px;
    height: 54px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 700;
  }

  .col-sums-row {
    margin-top: 6px;
  }

  .col-guide {
    width: 54px;
    height: 32px;
  }

  .sum-guide.match {
    color: #22c55e;
    font-size: 1rem;
  }

  .diag-guide {
    position: absolute;
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748b;
  }

  .diag-guide.top-left {
    top: 4px;
    left: 4px;
  }

  .diag-guide.top-right {
    top: 4px;
    right: 4px;
  }

  .diag-guide.match {
    color: #22c55e;
  }

  .controls-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 20px;
  }

  button.primary-btn {
    background: #2563eb;
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 12px;
    cursor: pointer;
    font-size: 1rem;
  }

  button.primary-btn:hover {
    background: #1d4ed8;
  }

  button.secondary-btn {
    background: #1e293b;
    color: #f1f5f9;
    font-weight: 600;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px;
    cursor: pointer;
    font-size: 0.9rem;
  }

  button.secondary-btn:hover {
    background: #334155;
  }

  .solution-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
    margin-top: 16px;
  }

  .solution-box h3 {
    margin: 0 0 12px 0;
    font-size: 1rem;
    color: #38bdf8;
  }

  .solution-grid {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
  }

  .solution-row {
    display: flex;
    gap: 4px;
  }

  .solution-cell {
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
  }
</style>
