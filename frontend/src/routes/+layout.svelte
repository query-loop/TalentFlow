<script lang="ts">
  import "../app.css";
  import { onMount } from 'svelte';
  import { token, user, isAuthenticated } from '../stores/auth';

  onMount(() => {
    // Load token from localStorage
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
      token.set(savedToken);
      isAuthenticated.set(true);
    }
  });
</script>

<slot />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
  }
</style>
