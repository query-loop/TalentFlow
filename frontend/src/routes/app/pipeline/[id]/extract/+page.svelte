<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/app/pipelines-v2', { replaceState: true });
  });
</script>

<section class="space-y-3">
  <div class="text-sm text-slate-600 dark:text-slate-300">Legacy v1 pipeline steps are disabled. Use Pipelines v2.</div>
  <a class="text-sm text-blue-600 hover:underline" href="/app/pipelines-v2">Go to Pipelines v2</a>
</section>
