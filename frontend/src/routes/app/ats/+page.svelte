<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/app/pipeline-v2/stats', { replaceState: true });
  });
</script>

<section class="space-y-3">
  <h1 class="text-xl font-semibold">ATS Score</h1>
  <div class="text-sm text-slate-600 dark:text-slate-300">This page has moved to the ATS dashboard.</div>
  <a class="text-sm text-blue-600 hover:underline" href="/app/pipeline-v2/stats">Go to ATS dashboard</a>
</section>
