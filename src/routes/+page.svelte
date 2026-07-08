<script lang="ts">
  import SummetryGame from '$lib/components/SummetryGame.svelte';
</script>

<main class="main-layout">
  <SummetryGame />
  
  <footer class="footer-navigation">
    <a href="/solver" class="solver-link">🛠️ Open Standalone Solver & Diagnostics</a>
  </footer>
</main>

<style>
  .main-layout {
    min-height: 100vh;
    background: #090d16;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-bottom: 40px;
  }

  .footer-navigation {
    margin-top: 24px;
    text-align: center;
  }

  .solver-link {
    color: #38bdf8;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    transition: color 0.2s;
  }

  .solver-link:hover {
    color: #7dd3fc;
    text-decoration: underline;
  }
</style>
