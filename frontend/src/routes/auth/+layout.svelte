<script lang="ts">
  import { isAuthenticated } from '../../stores/auth';
  import { goto } from '$app/navigation';

  // Redirect to dashboard if already authenticated
  $: if ($isAuthenticated) {
    goto('/app/dashboard');
  }
</script>

<slot />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
  }
</style>
