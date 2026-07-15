<script lang="ts">
  import favicon from '$lib/assets/favicon.svg';

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background-color: #090d16;
    color: #f1f5f9;
    font-family: system-ui, -apple-system, sans-serif;
  }
</style>

{@render children()}
