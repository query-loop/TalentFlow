<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/app/pipelines-v2', { replaceState: true });
  });
</script>

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Keywords</h1>
  <div class="text-sm text-slate-600 dark:text-slate-300">This flow is now driven by Pipelines v2.</div>
  <a class="text-sm text-blue-600 hover:underline" href="/app/pipelines-v2">Go to Pipelines v2</a>
</section>
