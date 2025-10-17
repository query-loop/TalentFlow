<script lang="ts">
  import { page } from '$app/stores';
  import { getPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';

  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let loading = true;

  async function loadPipeline() {
    if (!id) return;
    try {
      loading = true;
      error = null;
      pipe = await getPipelineV2(id);
    } catch (e: any) {
      error = e.message || 'Failed to load pipeline';
    } finally {
      loading = false;
    }
  }

  $: if (id) loadPipeline();
</script>

{#if loading}
  <div class="p-6">
    <div class="animate-pulse space-y-4">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
      <div class="h-28 bg-slate-200 dark:bg-slate-700 rounded"></div>
    </div>
  </div>
{:else if error}
  <div class="m-6 border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
    <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
      <Icon name="alert-circle" size={16} />
      <span class="font-medium">Error loading pipeline</span>
    </div>
    <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
  </div>
{:else if pipe}
  <div class="p-4 md:p-6 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Gaps</h1>
      <div class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
        <Icon name="x-circle" size={12} class="inline mr-1" /> Areas to improve
      </div>
    </div>

    <div class="border rounded-lg bg-white dark:bg-slate-800 p-4">
      {#if pipe.artifacts && (pipe.artifacts as any).scoring?.gaps?.length}
        <ul class="space-y-2">
          {#each (pipe.artifacts as any).scoring.gaps as gap}
            <li class="text-sm text-slate-700 dark:text-slate-300 flex items-start gap-2">
              <span class="text-red-600 dark:text-red-400 mt-0.5">•</span>
              <span>{gap}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <div class="text-sm text-slate-500 dark:text-slate-400">No gaps identified yet. Run scoring on the JD step.</div>
      {/if}
    </div>
  </div>
{/if}
