<script lang="ts">
  /*
    Game Component Template - Summetry implementation

    Use this structure for Svelte game components.
    Keep each section focused. If a function starts doing work from several
    sections, split it or move the logic to the section that owns it.
  */

  // ---------------------------------------------------------------------------
  // Imports & Setup
  // Purpose: Bring in framework tools, UI components, stores, helpers, and events.
  // Contains: onMount, createEventDispatcher, icons, child components, utilities.
  // Guideline: Group imports by source: Svelte, third-party packages, local app code.
  // ---------------------------------------------------------------------------
  import { onMount } from 'svelte';
  import HelpModal from './HelpModal.svelte';
  import StatsModal from './StatsModal.svelte';
  import ShareSummary from './ShareSummary.svelte';

  // ---------------------------------------------------------------------------
  // Config & Props
  // Purpose: Define parent inputs and fixed values that shape the game.
  // Contains: grid size, max attempts, mode, API base URL, exported props.
  // Guideline: Put values here when they configure the whole game.
  // ---------------------------------------------------------------------------
  let { defaultMode = 'daily' } = $props();

  // ---------------------------------------------------------------------------
  // Types & Interfaces
  // Purpose: Describe the shape of game data.
  // Contains: GameMode, CellState, Cell, Stats, API response types.
  // Guideline: Use types for repeated structures and limited valid states.
  // ---------------------------------------------------------------------------
  type GameMode = 'daily' | 'practice';
  type GameStatus =
    | 'starting'
    | 'typing'
    | 'checking'
    | 'revealing'
    | 'rowComplete'
    | 'won'
    | 'lost';

  interface Cell {
    val: number | null;
    isClue: boolean;
    userVar?: 'x' | 'y' | 'z' | null;
    userOffset?: number;
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
    solveTime: number; 
    showAnswer: boolean;
    solution: number[][] | null;
    varValues?: Record<'x' | 'y' | 'z', number | null>;
  }

  interface Stats {
    played: number;
    won: number;
    currentStreak: number;
    maxStreak: number;
    solveTimes: number[];
  }

  // ---------------------------------------------------------------------------
  // Persistent Storage Helpers
  // Purpose: Safely read and write browser storage.
  // Contains: storage keys, safe localStorage wrappers, date helpers.
  // Guideline: Keep raw localStorage access inside helpers.
  // ---------------------------------------------------------------------------
  const PRACTICE_STATE_KEY = 'summetry-practice';
  const DAILY_STATE_KEY = (date: string) => `summetry-daily-${date}`;

  const storage = {
    get: (key: string) => {
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set: (key: string, value: string) => {
      try {
        localStorage.setItem(key, value);
      } catch {}
    },
    remove: (key: string) => {
      try {
        localStorage.removeItem(key);
      } catch {}
    }
  };

  function todayKey() {
    return DAILY_STATE_KEY(new Date().toDateString());
  }

  // ---------------------------------------------------------------------------
  // Stats System
  // Purpose: Track long-term player performance.
  // Contains: loadStats, saveStats, updateStats, streaks, win percentage.
  // Guideline: Only update stats when a real game ends.
  // ---------------------------------------------------------------------------
  function loadStats(): Stats {
    try {
      const data = storage.get('summetry-stats');
      return data ? JSON.parse(data) : { played: 0, won: 0, currentStreak: 0, maxStreak: 0, solveTimes: [] };
    } catch {
      return { played: 0, won: 0, currentStreak: 0, maxStreak: 0, solveTimes: [] };
    }
  }

  function saveStats(stats: Stats) {
    storage.set('summetry-stats', JSON.stringify(stats));
  }

  function updateStats(won: boolean, solveTime: number) {
    const stats = loadStats();
    stats.played += 1;
    if (won) {
      stats.won += 1;
      stats.currentStreak += 1;
      stats.maxStreak = Math.max(stats.currentStreak, stats.maxStreak);
      stats.solveTimes.push(solveTime);
    } else {
      stats.currentStreak = 0;
    }
    saveStats(stats);
  }

  // ---------------------------------------------------------------------------
  // Share System
  // Purpose: Build and share the final result.
  // Contains: buildShareSummary, shareResult, clipboard fallback.
  // Guideline: Sharing should read final state, not mutate game state.
  // ---------------------------------------------------------------------------
  // Handled cleanly inside ShareSummary helper component

  // ---------------------------------------------------------------------------
  // Core Game State
  // Purpose: Store reactive values for the current session and UI.
  // Contains: active session, animation task, loading flags, UI flags.
  // Guideline: Keep state names explicit and avoid duplicate sources of truth.
  // ---------------------------------------------------------------------------
  let session = $state<GameSession | null>(null);
  let activeAnimation = $state<{ type: string; payload?: unknown } | null>(null);
  let mounted = $state(false);
  let isOnline = $state(true);

  let mode = $state<GameMode>(defaultMode);
  let selectedCell = $state<{ r: number; c: number } | null>(null);
  let showHelp = $state(false);
  let showStats = $state(false);
  let timerInterval: any = null;
  let variablesMode = $state(false);

  // ---------------------------------------------------------------------------
  // Derived Helpers
  // Purpose: Small calculations used by multiple sections.
  // Contains: gameId, gameInProgress, sleep, format helpers.
  // Guideline: Keep helpers small and mostly side-effect-free.
  // ---------------------------------------------------------------------------
  function getCellVariableLabel(r: number, c: number, cellVal: number | null): string {
    if (!session) return cellVal !== null ? String(cellVal) : '';
    const cell = session.grid[r][c];
    
    if (variablesMode && cell.userVar) {
      const varVal = session.varValues?.[cell.userVar];
      if (varVal !== undefined && varVal !== null) {
        // Variable has a numeric value assigned!
        const resolvedVal = varVal + (cell.userOffset || 0);
        return String(resolvedVal);
      } else {
        // Variable is NOT resolved yet, show the algebraic label (e.g., x, x+3)
        const offset = cell.userOffset || 0;
        if (offset === 0) {
          return cell.userVar;
        }
        const sign = offset >= 0 ? '+' : '-';
        const absOffset = Math.abs(offset);
        return `${cell.userVar}${sign}${absOffset}`;
      }
    }
    
    return cellVal !== null ? String(cellVal) : '';
  }
  function inputAllowed() {
    return session?.status === 'typing';
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

  // ---------------------------------------------------------------------------
  // API Layer
  // Purpose: Handle backend communication and request errors.
  // Contains: apiRequest, start request, submit/check request, answer request.
  // Guideline: Keep fetch/error handling here so gameplay logic stays readable.
  // ---------------------------------------------------------------------------
  async function apiRequest(path: string, options = {}) {
    const response = await fetch(path, options);
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
  }

  async function requestStartGame(selectedMode: GameMode) {
    const url = selectedMode === 'daily' ? '/api/board/daily' : '/api/board/random';
    return apiRequest(url);
  }

  async function requestSubmitGuess(boardId: string, gridValues: (number | null)[][]) {
    return apiRequest('/api/board/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board_id: boardId, grid: gridValues })
    });
  }

  async function requestSolution(boardId: string) {
    return apiRequest(`/api/board/${boardId}/solution`);
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // Purpose: Initialize and clean up the component.
  // Contains: onMount, restore/start logic, event listeners, cleanup.
  // Guideline: Lifecycle should coordinate setup, not hold detailed game rules.
  // ---------------------------------------------------------------------------
  onMount(() => {
    restoreGameState();
    window.addEventListener('keydown', handlePhysicalKey);
    mounted = true;

    return () => {
      window.removeEventListener('keydown', handlePhysicalKey);
      if (timerInterval) clearInterval(timerInterval);
    };
  });

  // ---------------------------------------------------------------------------
  // Mode & Reset
  // Purpose: Switch modes and return the game to a clean state.
  // Contains: toggleMode, handleModeChange, resetState, startNewPracticeGame.
  // Guideline: Reset all session-specific state together.
  // ---------------------------------------------------------------------------
  function toggleMode(newMode: GameMode) {
    if (timerInterval) clearInterval(timerInterval);
    mode = newMode;
    restoreGameState();
  }

  function resetState() {
    session = null;
    selectedCell = null;
    if (timerInterval) clearInterval(timerInterval);
  }

  async function handleNewPracticeGame() {
    resetState();
    try {
      const boardData = await requestStartGame('practice');
      initSession(boardData);
    } catch (err) {
      console.error(err);
    }
  }

  // ---------------------------------------------------------------------------
  // Game Flow
  // Purpose: Control start -> input -> submit -> reveal -> win/loss.
  // Contains: startGame, submitGuess, handleWin, handleLoss, endGame.
  // Guideline: Keep this section in the order the player experiences the game.
  // ---------------------------------------------------------------------------
  async function startGame(selectedMode: GameMode) {
    resetState();
    try {
      const boardData = await requestStartGame(selectedMode);
      initSession(boardData);
    } catch (err) {
      console.error(err);
    }
  }

  function initSession(boardData: any) {
    const puzzle = boardData.puzzle;
    const sessionGrid: Cell[][] = [];
    for (let r = 0; r < 5; r++) {
      const row: Cell[] = [];
      for (let c = 0; c < 5; c++) {
        row.push({
          val: puzzle[r][c],
          isClue: puzzle[r][c] !== null,
          userVar: null,
          userOffset: 0
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
      magicSum: 34,
      solveTime: 0,
      showAnswer: false,
      solution: null,
      varValues: { x: null, y: null, z: null }
    };

    saveGameState();

    timerInterval = setInterval(() => {
      if (session && session.status === 'typing') {
        session.solveTime += 1;
        saveGameState();
      }
    }, 1000);
  }

  async function submitGuess() {
    if (!session) return;
    if (!ensureSessionIntegrity()) {
      alert("Session integrity check failed. Restarting game.");
      startGame(mode);
      return;
    }

    let allFilled = true;
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        if (session.grid[r][c].val === null) allFilled = false;
      }
    }

    if (!allFilled) {
      alert("⚠️ Some cells are still empty!");
      return;
    }

    session.status = 'checking';
    const gridValues = session.grid.map(row => row.map(cell => cell.val));
    try {
      const data = await requestSubmitGuess(session.boardId, gridValues);
      if (data.correct) {
        handleWin(data.magic_sum);
      } else {
        session.status = 'typing';
        alert("❌ Check failed: " + (data.message || "Line sums mismatch. Try again!"));
      }
    } catch (err) {
      session.status = 'typing';
      console.error(err);
      alert("⚠️ Server error verifying solution.");
    }
  }

  function handleWin(magicSum: number) {
    if (!session) return;
    session.status = 'won';
    session.magicSum = magicSum;
    if (timerInterval) clearInterval(timerInterval);
    saveGameState();
    updateStats(true, session.solveTime);
  }

  async function toggleShowAnswer() {
    if (!session) return;
    if (!session.showAnswer) {
      if (!session.solution) {
        try {
          const data = await requestSolution(session.boardId);
          session.solution = data.solution;
        } catch (err) {
          console.error(err);
          alert("Failed to load solution from server.");
          return;
        }
      }
      session.showAnswer = true;
    } else {
      session.showAnswer = false;
    }
    saveGameState();
  }

  // ---------------------------------------------------------------------------
  // Persistence
  // Purpose: Save and restore unfinished games.
  // Contains: saveGameState, restoreGameState, applySavedState, consistency guards.
  // Guideline: Persist only what is needed to rebuild the game accurately.
  // ---------------------------------------------------------------------------
  function saveGameState() {
    if (!session) return;
    const key = mode === 'daily' ? todayKey() : PRACTICE_STATE_KEY;
    storage.set(key, JSON.stringify(session));
  }

  async function restoreGameState() {
    const key = mode === 'daily' ? todayKey() : PRACTICE_STATE_KEY;
    const savedData = storage.get(key);
    let loadedSession = null;
    if (savedData) {
      try {
        loadedSession = JSON.parse(savedData);
      } catch (e) {
        console.error("Failed to parse saved session:", e);
      }
    }

    if (loadedSession) {
      session = loadedSession;
      
      // Auto-migrate old saves to support user variables:
      if (session) {
        if (!session.varValues) {
          session.varValues = { x: null, y: null, z: null };
        }
        for (let r = 0; r < 5; r++) {
          for (let c = 0; c < 5; c++) {
            const cell = session.grid[r][c];
            if (cell.userVar === undefined) cell.userVar = null;
            if (cell.userOffset === undefined) cell.userOffset = 0;
          }
        }
      }

      if (timerInterval) clearInterval(timerInterval);
      if (session && session.status === 'typing') {
        timerInterval = setInterval(() => {
          if (session) {
            session.solveTime += 1;
            saveGameState();
          }
        }, 1000);
      }
    } else {
      startGame(mode);
    }
  }

  function ensureSessionIntegrity() {
    return session?.seed === session?.startSeed;
  }

  // ---------------------------------------------------------------------------
  // Input
  // Purpose: Handle virtual and physical player input.
  // Contains: handleKey, backspace, handlePhysicalKey, submit button behavior.
  // Guideline: Validate whether an action is allowed before changing state.
  // ---------------------------------------------------------------------------
  function handleKey(key: string) {
    if (!session || !inputAllowed() || !selectedCell) return;
    const { r, c } = selectedCell;
    if (session.grid[r][c].isClue) return;

    const val = parseInt(key);
    if (val >= 1 && val <= 9) {
      if (variablesMode && cell.userVar) {
        const cellOffset = cell.userOffset || 0;
        const varName = cell.userVar;
        const varVal = val - cellOffset;
        
        if (!session.varValues) {
          session.varValues = { x: null, y: null, z: null };
        }
        
        // Validate all other cells using this variable
        for (let ri = 0; ri < 5; ri++) {
          for (let ci = 0; ci < 5; ci++) {
            const other = session.grid[ri][ci];
            if (other.userVar === varName) {
              const linkedVal = varVal + (other.userOffset || 0);
              if (linkedVal < 1 || linkedVal > 9) {
                const sign = (other.userOffset || 0) >= 0 ? '+' : '-';
                const absO = Math.abs(other.userOffset || 0);
                const label = other.userOffset === 0 ? varName : `${varName}${sign}${absO}`;
                alert(`⚠️ Invalid: Setting this cell to ${val} forces cell (${ri+1}, ${ci+1}) [${label}] to ${linkedVal}, out of bounds [1-9]!`);
                return;
              }
            }
          }
        }
        
        // Apply values to all matching variable cells
        session.varValues[varName] = varVal;
        for (let ri = 0; ri < 5; ri++) {
          for (let ci = 0; ci < 5; ci++) {
            const other = session.grid[ri][ci];
            if (other.userVar === varName) {
              other.val = varVal + (other.userOffset || 0);
            }
          }
        }
        saveGameState();
        return;
      }

      cell.val = val;
      saveGameState();
    }
  }

  function backspace() {
    if (!session || !inputAllowed() || !selectedCell) return;
    const { r, c } = selectedCell;
    const cell = session.grid[r][c];
    if (cell.isClue) return;

    if (variablesMode && cell.userVar) {
      const varName = cell.userVar;
      if (session.varValues) {
        session.varValues[varName] = null;
      }
      for (let ri = 0; ri < 5; ri++) {
        for (let ci = 0; ci < 5; ci++) {
          const other = session.grid[ri][ci];
          if (other.userVar === varName) {
            other.val = null;
          }
        }
      }
      saveGameState();
      return;
    }

    cell.val = null;
    saveGameState();
  }

  function assignCellVariable(vName: 'x' | 'y' | 'z') {
    if (!session || !selectedCell) return;
    const { r, c } = selectedCell;
    if (session.grid[r][c].isClue) return;
    
    session.grid[r][c].userVar = vName;
    session.grid[r][c].userOffset = 0;
    
    if (!session.varValues) {
      session.varValues = { x: null, y: null, z: null };
    }
    
    // If the variable already has a value, sync it!
    const varVal = session.varValues[vName];
    if (varVal !== null) {
      session.grid[r][c].val = varVal;
    } else {
      session.grid[r][c].val = null;
    }
    
    saveGameState();
  }

  function clearCellVariable() {
    if (!session || !selectedCell) return;
    const { r, c } = selectedCell;
    if (session.grid[r][c].isClue) return;
    
    session.grid[r][c].userVar = null;
    session.grid[r][c].userOffset = 0;
    session.grid[r][c].val = null;
    
    saveGameState();
  }

  function assignCellOffset(offsetVal: number) {
    if (!session || !selectedCell) return;
    const { r, c } = selectedCell;
    const cell = session.grid[r][c];
    if (cell.isClue || !cell.userVar) return;
    
    cell.userOffset = offsetVal;
    
    if (!session.varValues) {
      session.varValues = { x: null, y: null, z: null };
    }
    
    // If the variable has a value, sync it!
    const varVal = session.varValues[cell.userVar];
    if (varVal !== null) {
      cell.val = varVal + offsetVal;
    } else {
      cell.val = null;
    }
    
    saveGameState();
  }

  function setVariableValue(vName: 'x' | 'y' | 'z', valueStr: string) {
    if (!session) return;
    if (!session.varValues) {
      session.varValues = { x: null, y: null, z: null };
    }
    
    if (valueStr === "") {
      session.varValues[vName] = null;
      // Clear all cells that are bound to this variable
      for (let r = 0; r < 5; r++) {
        for (let c = 0; c < 5; c++) {
          const cell = session.grid[r][c];
          if (cell.userVar === vName) {
            cell.val = null;
          }
        }
      }
      saveGameState();
      return;
    }
    
    const val = parseInt(valueStr);
    
    // Validate all cells containing this variable stay in bounds [1, 9]
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        const cell = session.grid[r][c];
        if (cell.userVar === vName) {
          const linkedVal = val + (cell.userOffset || 0);
          if (linkedVal < 1 || linkedVal > 9) {
            const sign = (cell.userOffset || 0) >= 0 ? '+' : '-';
            const absO = Math.abs(cell.userOffset || 0);
            const label = cell.userOffset === 0 ? vName : `${vName}${sign}${absO}`;
            alert(`⚠️ Invalid: Setting ${vName}=${val} forces cell (${r+1}, ${c+1}) [${label}] to {linkedVal}, out of bounds [1-9]!`);
            return;
          }
        }
      }
    }
    
    // Apply the values
    session.varValues[vName] = val;
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        const cell = session.grid[r][c];
        if (cell.userVar === vName) {
          cell.val = val + (cell.userOffset || 0);
        }
      }
    }
    saveGameState();
  }

  function handlePhysicalKey(event: KeyboardEvent) {
    if (!session || !inputAllowed()) return;
    
    if (event.key >= '1' && event.key <= '9') {
      handleKey(event.key);
    } else if (event.key === 'Backspace' || event.key === 'Delete') {
      backspace();
    } else if (event.key.startsWith('Arrow') && selectedCell) {
      event.preventDefault();
      let { r, c } = selectedCell;
      if (event.key === 'ArrowUp') r = Math.max(0, r - 1);
      else if (event.key === 'ArrowDown') r = Math.min(4, r + 1);
      else if (event.key === 'ArrowLeft') c = Math.max(0, c - 1);
      else if (event.key === 'ArrowRight') c = Math.min(4, c + 1);
      selectedCell = { r, c };
    }
  }

  function handleCellClick(r: number, c: number) {
    if (!session || !inputAllowed()) return;
    selectedCell = { r, c };
  }
</script>

<!--
  ---------------------------------------------------------------------------
  UI Markup
  Purpose: Render the visible game experience.
  Contains: loading state, menu, board/grid, messages, actions, keyboard.
  Guideline: Keep complex business logic out of the markup.
  ---------------------------------------------------------------------------
-->
{#if !mounted}
  <div class="game-loading">
    Loading...
  </div>
{:else}
  <div class="game-container">
    <header class="header">
      <div class="header-left">
        <h1>Summetry</h1>
        <div class="mode-toggle">
          <button class:active={mode === 'daily'} onclick={() => toggleMode('daily')}>📅 Daily</button>
          <button class:active={mode === 'practice'} onclick={() => toggleMode('practice')}>🔀 Practice</button>
        </div>
      </div>
      <div class="header-right">
        <button class="icon-btn" onclick={() => showHelp = true}>❓ Help</button>
        <button class="icon-btn" onclick={() => showStats = true}>📊 Stats</button>
      </div>
    </header>

    {#if session}
      <div class="puzzle-info">
        <div class="badge-row">
          <span class="info-badge">ID: {(session.boardId || '').slice(0, 8)}</span>
          <span class="info-badge uppercase {(session.difficulty || 'Easy').toLowerCase()}">{session.difficulty || 'Easy'}</span>
          {#if session.solveTime > 0}
            <span class="info-badge timer">⏱️ {Math.floor(session.solveTime / 60)}:{(session.solveTime % 60) < 10 ? '0' : ''}{session.solveTime % 60}</span>
          {/if}
        </div>
        <label class="variables-toggle-lbl" style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; font-weight: 600; color: #94a3b8; cursor: pointer; margin-top: 10px;">
          <input type="checkbox" bind:checked={variablesMode} style="cursor: pointer;" />
          🧮 Enable Variables Mode
        </label>
        
        {#if variablesMode}
          <div class="variable-values-panel" style="display: flex; gap: 12px; margin-top: 12px; background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #1e293b; align-items: center; justify-content: center; flex-wrap: wrap;">
            <span style="font-size: 0.85rem; font-weight: 600; color: #94a3b8;">Set Variable Values:</span>
            {#each ['x', 'y', 'z'] as vName}
              <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: 700; color: #60a5fa; font-size: 0.9rem; text-transform: uppercase;">{vName} =</span>
                <select 
                  value={session.varValues?.[vName as 'x'|'y'|'z'] || ''} 
                  style="background: #1e293b; color: white; border: 1px solid #334155; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 0.9rem; cursor: pointer;"
                  onchange={(e) => setVariableValue(vName as 'x'|'y'|'z', (e.target as HTMLSelectElement).value)}
                >
                  <option value="">?</option>
                  {#each [1, 2, 3, 4, 5, 6, 7, 8, 9] as num}
                    <option value={num}>{num}</option>
                  {/each}
                </select>
              </div>
            {/each}
          </div>
        {/if}
      </div>

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
                  class:variable={variablesMode && cell.userVar}
                  onclick={() => handleCellClick(rIdx, cIdx)}
                >
                  <span class="cell-main-text">
                    {cell.isClue ? cell.val : getCellVariableLabel(rIdx, cIdx, cell.val)}
                  </span>
                  {#if variablesMode && cell.userVar}
                    <span class="cell-sub-text">
                      {cell.userVar}{cell.userOffset !== 0 ? (cell.userOffset > 0 ? '+' + cell.userOffset : cell.userOffset) : ''}
                    </span>
                  {/if}
                </button>
              {/each}
              
              <div class="sum-guide row-guide" class:match={getRowSum(rIdx).sum === session!.magicSum && getRowSum(rIdx).complete}>
                {getRowSum(rIdx).sum}
              </div>
            </div>
          {/each}

          <div class="grid-row col-sums-row">
            {#each [0, 1, 2, 3, 4] as cIdx}
              <div class="sum-guide col-guide" class:match={getColSum(cIdx).sum === session!.magicSum && getColSum(cIdx).complete}>
                {getColSum(cIdx).sum}
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Virtual Number Pad -->
      {#if selectedCell && session && session.status === 'typing'}
        <div class="virtual-keyboard">
          {#each [1, 2, 3, 4, 5, 6, 7, 8, 9] as digit}
            <button class="key-btn" onclick={() => handleKey(String(digit))}>{digit}</button>
          {/each}
          <button class="key-btn clear-btn" onclick={backspace}>✕</button>
        </div>
      {/if}

      <!-- Variable Assignment Panel -->
      {#if selectedCell && session && session.status === 'typing' && variablesMode && !session.grid[selectedCell.r][selectedCell.c].isClue}
        <div class="variable-assign-panel" style="display: flex; flex-direction: column; gap: 8px; background: #1e293b; border: 1px solid #334155; padding: 12px; border-radius: 8px; margin-top: 10px; margin-bottom: 15px;">
          <div style="font-size: 0.85rem; font-weight: 600; color: #94a3b8; text-align: center;">🧮 Assign Variable to Cell ({selectedCell.r+1}, {selectedCell.c+1})</div>
          <div class="var-btn-row" style="display: flex; gap: 6px; justify-content: center;">
            {#each ['x', 'y', 'z'] as vName}
              <button 
                class="var-assign-btn" 
                class:active={session.grid[selectedCell!.r][selectedCell!.c].userVar === vName}
                style="flex: 1; padding: 8px; font-weight: 700; background: {session.grid[selectedCell!.r][selectedCell!.c].userVar === vName ? '#2563eb' : '#0f172a'}; border: 1px solid #334155; color: #f1f5f9; border-radius: 6px; cursor: pointer;"
                onclick={() => assignCellVariable(vName as 'x'|'y'|'z')}
              >
                Assign {vName}
              </button>
            {/each}
            {#if session.grid[selectedCell.r][selectedCell.c].userVar}
              <button 
                class="var-assign-btn clear-var-btn" 
                style="flex: 1; padding: 8px; font-weight: 700; background: #ef4444; border: 1px solid #ef4444; color: white; border-radius: 6px; cursor: pointer;"
                onclick={clearCellVariable}
              >
                Remove
              </button>
            {/if}
          </div>
          
          {#if session.grid[selectedCell.r][selectedCell.c].userVar}
            <div style="font-size: 0.8rem; font-weight: 600; color: #64748b; text-align: center; margin-top: 4px;">Adjust Offset for {session.grid[selectedCell.r][selectedCell.c].userVar}:</div>
            <div class="offset-btn-row" style="display: flex; gap: 4px; justify-content: center; flex-wrap: wrap;">
              {#each [-4, -3, -2, -1, 0, 1, 2, 3, 4] as offsetVal}
                <button 
                  class="offset-btn"
                  class:active={session.grid[selectedCell!.r][selectedCell!.c].userOffset === offsetVal}
                  style="padding: 6px 10px; font-size: 0.8rem; font-weight: 700; background: {session.grid[selectedCell!.r][selectedCell!.c].userOffset === offsetVal ? '#10b981' : '#0f172a'}; border: 1px solid #334155; color: #f1f5f9; border-radius: 4px; cursor: pointer;"
                  onclick={() => assignCellOffset(offsetVal)}
                >
                  {offsetVal >= 0 ? '+' : ''}{offsetVal}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <div class="controls-panel">
        {#if session.status === 'typing'}
          <button class="primary-btn check-btn" onclick={submitGuess}>✅ Check Solution</button>
          <button class="secondary-btn" onclick={toggleShowAnswer}>
            {session.showAnswer ? '👁️ Hide Answer' : '👁️ Show Answer'}
          </button>
        {/if}

        {#if mode === 'practice'}
          <button class="secondary-btn" onclick={handleNewPracticeGame}>
            🔀 New Practice Game
          </button>
        {/if}
      </div>

      {#if session.showAnswer && session.solution}
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

    {#if showHelp}
      <HelpModal onclick={() => showHelp = false} on:close={() => showHelp = false} />
    {/if}
    {#if showStats}
      <StatsModal onclick={() => showStats = false} on:close={() => showStats = false} />
    {/if}
  </div>
{/if}

<style>
  /*
    ---------------------------------------------------------------------------
    Styling
    Purpose: Define layout, colors, animations, responsive behavior, and states.
    Contains: scoped classes, CSS variables, dark mode, grid, keyboard, buttons.
    Guideline: Use semantic class names and shared tokens for repeated values.
    ---------------------------------------------------------------------------
  */
  .game-loading {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 50vh;
    color: #94a3b8;
    font-size: 1.2rem;
  }

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
  .virtual-keyboard {
    display: flex;
    gap: 6px;
    justify-content: center;
    margin-top: 15px;
    background: #1e293b;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #334155;
    margin-bottom: 15px;
  }

  .key-btn {
    flex: 1;
    height: 40px;
    background: #0f172a;
    border: 1px solid #334155;
    color: #f1f5f9;
    font-weight: 700;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.1s;
  }

  .key-btn:hover {
    background: #1e293b;
  }

  .key-btn.clear-btn {
    background: #ef4444;
    border-color: #ef4444;
  }

  .key-btn.clear-btn:hover {
    background: #dc2626;
  }

  /* Interactive Variables Styling */
  .grid-cell.variable {
    background: #1e3a8a !important; /* Elegant dark blue for variables */
    border-color: #3b82f6 !important;
  }

  .grid-cell.variable.selected {
    background: #2563eb !important;
  }

  .grid-cell {
    position: relative;
  }

  .cell-sub-text {
    position: absolute;
    bottom: 2px;
    right: 4px;
    font-size: 0.65rem;
    color: #93c5fd;
    font-weight: 600;
    pointer-events: none;
  }
</style>
