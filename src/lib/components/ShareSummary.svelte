<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  let { puzzle, boardId, solveTime, magicSum, difficulty } = $props();

  let copied = $state(false);

  function formatTime(sec: number) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function getEmojiGrid() {
    let gridString = '';
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        if (puzzle[r][c] !== null) {
          gridString += '🟩'; // Prefilled Clue cell
        } else {
          gridString += '🟦'; // User solved cell
        }
      }
      gridString += '\n';
    }
    return gridString;
  }

  function handleShare() {
    const timeStr = formatTime(solveTime);
    const shareText = `Summetry Magic Grid - ID: ${boardId.slice(0, 8)}\nDifficulty: ${difficulty.toUpperCase()}\nSolve Time: ${timeStr} | Magic Sum: ${magicSum}\n\n${getEmojiGrid()}\nPlay Summetry live!`;
    
    try {
      navigator.clipboard.writeText(shareText);
      copied = true;
      setTimeout(() => copied = false, 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  }
</script>

<div class="share-card">
  <h2>🎉 Congratulations!</h2>
  <p class="congrats-text">You successfully aligned all 12 lines to the Magic Number <strong>{magicSum}</strong>!</p>
  
  <div class="results-meta">
    <div class="meta-item">
      <span class="label">Time</span>
      <span class="value">{formatTime(solveTime)}</span>
    </div>
    <div class="meta-item">
      <span class="label">Difficulty</span>
      <span class="value uppercase">{difficulty}</span>
    </div>
    <div class="meta-item">
      <span class="label">Magic Sum</span>
      <span class="value">{magicSum}</span>
    </div>
  </div>

  <div class="emoji-preview">
    <pre>{getEmojiGrid()}</pre>
  </div>

  <button class="share-btn" class:copied on:click={handleShare}>
    {copied ? '✅ Copied to Clipboard!' : '🔗 Share Result'}
  </button>
</div>

<style>
  .share-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    max-width: 400px;
    margin: 20px auto;
    color: #f1f5f9;
  }

  h2 {
    color: #22c55e;
    margin-top: 0;
    margin-bottom: 8px;
    font-size: 1.6rem;
    font-weight: 700;
  }

  .congrats-text {
    font-size: 0.95rem;
    color: #cbd5e1;
    margin-bottom: 20px;
  }

  .results-meta {
    display: flex;
    justify-content: space-around;
    background: #0f172a;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 20px;
    border: 1px solid #1e293b;
  }

  .meta-item {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .meta-item .label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .meta-item .value {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9;
  }

  .uppercase {
    text-transform: uppercase;
  }

  .emoji-preview {
    font-size: 1.2rem;
    line-height: 1.2;
    background: #0f172a;
    border-radius: 8px;
    padding: 16px;
    width: fit-content;
    margin: 0 auto 20px auto;
    border: 1px solid #1e293b;
  }

  .emoji-preview pre {
    margin: 0;
    font-family: inherit;
  }

  .share-btn {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 600;
    width: 100%;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
  }

  .share-btn:hover {
    background: #1d4ed8;
  }

  .share-btn:active {
    transform: scale(0.98);
  }

  .share-btn.copied {
    background: #16a34a;
  }
</style>
