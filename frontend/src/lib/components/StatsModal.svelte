<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  const dispatch = createEventDispatcher();

  interface Stats {
    played: number;
    won: number;
    currentStreak: number;
    maxStreak: number;
    solveTimes: number[]; // in seconds
  }

  let stats = $state<Stats>({
    played: 0,
    won: 0,
    currentStreak: 0,
    maxStreak: 0,
    solveTimes: []
  });

  onMount(() => {
    try {
      const stored = localStorage.getItem('summetry-stats');
      if (stored) {
        stats = JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  });

  let avgTime = $derived(stats.solveTimes.length > 0
    ? Math.round(stats.solveTimes.reduce((a, b) => a + b, 0) / stats.solveTimes.length)
    : 0);

  function formatTime(sec: number) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }
</script>

<div class="modal-backdrop" onclick={() => dispatch('close')} onkeydown={(e) => { if (e.target === e.currentTarget && e.key === 'Escape') dispatch('close'); }} tabindex="0" role="button">
  <div class="modal-content" onclick={(e) => e.stopPropagation()} role="presentation">
    <header class="modal-header">
      <h2>📊 Your Statistics</h2>
      <button class="close-btn" onclick={() => dispatch('close')}>&times;</button>
    </header>
    <main class="modal-body">
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-val">{stats.played}</div>
          <div class="stat-lbl">Played</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{stats.played > 0 ? Math.round((stats.won / stats.played) * 100) : 0}%</div>
          <div class="stat-lbl">Win Rate</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{stats.currentStreak}</div>
          <div class="stat-lbl">Current Streak</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{stats.maxStreak}</div>
          <div class="stat-lbl">Max Streak</div>
        </div>
      </div>

      {#if stats.solveTimes.length > 0}
        <section class="details-section">
          <h3>⏱️ Solve Time Analytics:</h3>
          <p>Average Solve Time: <strong>{formatTime(avgTime)}</strong></p>
          <p>Best Solve Time: <strong>{formatTime(Math.min(...stats.solveTimes))}</strong></p>
        </section>
      {/if}
    </main>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 16px;
    width: 90%;
    max-width: 450px;
    padding: 24px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    color: #f1f5f9;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
  }

  .close-btn {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 1.8rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
  }

  .close-btn:hover {
    color: #f1f5f9;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }

  .stat-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 6px;
    text-align: center;
  }

  .stat-val {
    font-size: 1.6rem;
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 4px;
  }

  .stat-lbl {
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .details-section {
    border-top: 1px solid #1e293b;
    padding-top: 16px;
    font-size: 0.95rem;
    color: #e2e8f0;
  }

  .details-section h3 {
    margin: 0 0 10px 0;
    font-size: 1rem;
    color: #38bdf8;
  }

  .details-section p {
    margin: 6px 0;
  }

  strong {
    color: #f1f5f9;
  }
</style>
