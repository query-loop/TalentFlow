<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';
  import { getPipeline, patchPipeline, type Pipeline } from '$lib/pipelines';
  import { stepOrder, stepPaths, type StepKey, getActivePipelineId, markStepProgress, pathForStep, markStepProgressFor } from '$lib/pipelineTracker';
  export let current: StepKey;
  export let canComplete: (() => boolean) | null = null;
  // Optional: when provided, StepFooter operates in scoped (nested) mode for this pipeline id
  export let pipelineId: string | undefined = undefined;

  let pipeline: Pipeline | null = null;
  let percent = 0;
  let loading = true;
  let error: string | null = null;
  let nextKey: StepKey | null = null;

  function computePercent() {
    if (!pipeline) { percent = 0; return; }
    const total = stepOrder.length;
    const done = stepOrder.filter(k => pipeline?.statuses?.[k] === 'complete').length;
    percent = Math.round((done / Math.max(1,total)) * 100);
  }

  function calcNext(): StepKey | null {
    const idx = stepOrder.indexOf(current);
    if (idx === -1) return null;
    return idx < stepOrder.length - 1 ? stepOrder[idx + 1] : null;
  }

  async function load() {
    loading = true; error = null;
    try {
      const id = pipelineId || getActivePipelineId();
      if (!id) { pipeline = null; return; }
      pipeline = await getPipeline(id);
      computePercent();
      nextKey = calcNext();
    } catch (e:any) { error = e?.message || 'Failed to load pipeline'; pipeline = null; }
    finally { loading = false; }
  }

  onMount(async () => {
    if (pipelineId) {
      await markStepProgressFor(pipelineId, current);
    } else {
      await markStepProgress(current);
    }
    await load();
  });

  async function completeAndNext() {
    if (!pipeline) return;
    const idx = stepOrder.indexOf(current);
    const patch: any = { statuses: {} };
    patch.statuses[current] = 'complete';
    if (idx < stepOrder.length - 1) {
      patch.statuses[stepOrder[idx+1]] = 'active';
    }
    try {
      pipeline = await patchPipeline(pipeline.id, patch);
      computePercent();
      nextKey = calcNext();
      if (idx < stepOrder.length - 1) {
        const next = stepOrder[idx+1];
        location.href = pathForStep(next, pipelineId);
      }
    } catch {}
  }
</script>

<div class="fixed bottom-4 right-4 z-40">
  <div class="border rounded-lg shadow-lg bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border-slate-200 dark:border-slate-700 p-3 min-w-[280px]">
    <div class="flex items-center justify-between mb-2">
      <div class="text-xs text-gray-600 dark:text-gray-300 flex items-center gap-1"><Icon name="layers" size={14}/> Pipeline progress</div>
      <div class="text-xs font-medium text-gray-900 dark:text-gray-100">{percent}%</div>
    </div>
    <div class="w-full h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden mb-2">
      <div class="h-full bg-indigo-600" style={`width:${percent}%`}></div>
    </div>

    {#if !pipeline}
      <div class="text-xs text-gray-600 dark:text-gray-300">{pipelineId ? 'Pipeline not found.' : 'No active pipeline.'} <a href="/app/pipelines" class="text-blue-600 hover:underline">Choose one</a>.</div>
    {:else}
      <div class="flex items-center gap-2 flex-wrap mb-2">
        {#each stepOrder as key, i}
          <a href={pathForStep(key, pipelineId)}
             class={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] ${pipeline.statuses[key] === 'complete' ? 'border-emerald-300 text-emerald-700 bg-emerald-50' : pipeline.statuses[key] === 'active' ? 'border-indigo-300 text-indigo-700 bg-indigo-50' : 'border-slate-200 text-gray-700'}`}
             title={`Go to ${key}`}>
            <span class={`inline-flex items-center justify-center w-4 h-4 rounded-full ${pipeline.statuses[key] === 'complete' ? 'bg-emerald-600 text-white' : pipeline.statuses[key] === 'active' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'}`}>{i+1}</span>
            <span class="capitalize">{key}</span>
          </a>
        {/each}
      </div>
      <div class="flex items-center justify-between gap-2">
        <div class="text-xs text-gray-600 dark:text-gray-300 truncate">Current: <span class="capitalize">{current}</span></div>
        {#if nextKey}
          <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50"
                  disabled={canComplete ? !canComplete() : false}
                  on:click={completeAndNext}>
            Next: <span class="capitalize">{nextKey}</span>
          </button>
        {:else}
          <div class="text-xs text-emerald-700 dark:text-emerald-300">All steps complete</div>
        {/if}
      </div>
    {/if}
  </div>
</div>
