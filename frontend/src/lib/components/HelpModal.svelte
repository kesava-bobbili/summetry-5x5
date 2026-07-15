<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
</script>

<div class="modal-backdrop" onclick={() => dispatch('close')} onkeydown={(e) => { if (e.target === e.currentTarget && e.key === 'Escape') dispatch('close'); }} tabindex="0" role="button">
  <div class="modal-content" onclick={(e) => e.stopPropagation()} role="presentation">
    <header class="modal-header">
      <h2>🧩 How to Play Summetry</h2>
      <button class="close-btn" onclick={() => dispatch('close')}>&times;</button>
    </header>
    <main class="modal-body">
      <p><strong>Summetry</strong> is a 5x5 logic grid puzzle where you fill the cells with digits from <strong>1 to 9</strong> to establish mathematical symmetry.</p>
      
      <section class="rules-section">
        <h3>📜 The Core Rule:</h3>
        <p>Every single one of the following 12 lines must sum to the exact same <strong>Magic Number</strong>:</p>
        <ul>
          <li>All <strong>5 rows</strong></li>
          <li>All <strong>5 columns</strong></li>
          <li>The <strong>2 main diagonals</strong></li>
        </ul>
      </section>

      <section class="tips-section">
        <h3>💡 Quick Tips:</h3>
        <ul>
          <li><strong>Given Clues:</strong> Dark blue cells are pre-filled clues and cannot be modified.</li>
          <li><strong>Sum Indicators:</strong> Check the row, column, and diagonal indicators. They will dynamically show the current sum and highlight green when the target sum is satisfied!</li>
          <li><strong>Keyboard Navigation:</strong> Use the arrow keys on your keyboard to navigate between empty cells. Press backspace to clear a cell.</li>
        </ul>
      </section>
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
    max-width: 500px;
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
    margin-bottom: 16px;
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

  .modal-body {
    line-height: 1.6;
    font-size: 0.95rem;
  }

  h3 {
    color: #38bdf8;
    font-size: 1.1rem;
    margin-top: 20px;
    margin-bottom: 8px;
    font-weight: 600;
  }

  ul {
    margin: 8px 0;
    padding-left: 20px;
  }

  li {
    margin-bottom: 6px;
  }

  strong {
    color: #38bdf8;
  }
</style>
