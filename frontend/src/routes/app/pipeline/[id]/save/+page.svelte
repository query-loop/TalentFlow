<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import StepFooter from '$lib/components/StepFooter.svelte';
  import { getPipeline, type Pipeline } from '$lib/pipelines';
  import StepNav from '$lib/components/StepNav.svelte';

  let pipeline: Pipeline | null = null;
  let error = '';
  $: pid = $page.params.id;

  async function load() {
    try { pipeline = await getPipeline(pid); }
    catch (e:any) { error = e?.message || 'Failed to load pipeline'; pipeline = null; }
  }

  onMount(load);

  function percent(p: Pipeline | null) {
    if (!p) return 0;
    const order: Array<'extract'|'generate'|'keywords'|'ats'|'export'|'save'> = ['extract','generate','keywords','ats','export','save'];
    const done = order.filter(k => (p.statuses as any)[k] === 'complete').length;
    return Math.round((done / order.length) * 100);
  }
</script>

{#if error}
  <div class="p-6">
    <div class="rounded-lg border border-red-200 dark:border-red-800 p-6 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200">{error}</div>
  </div>
{:else if !pipeline}
  <div class="p-6">
    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-6 bg-white dark:bg-gray-900">Pipeline not found.</div>
  </div>
{:else}
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="folder"/> Save — <span class="text-sm text-gray-600">{pipeline.name}</span></h1>
      <a href={`/app/pipeline/${pipeline.id}`} class="text-sm text-blue-600 hover:underline">Back to pipeline</a>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900">
      <div class="mb-3 flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
        <div class="flex items-center gap-2">
          <span class="text-gray-500">Pipeline</span>
          <span class="text-gray-400">•</span>
          <span class="truncate" title={pipeline.name}>{pipeline.name}</span>
        </div>
        <div class="text-[11px] text-gray-500">Created {new Date(pipeline.createdAt).toLocaleString()}</div>
      </div>
      <div class="mb-3">
        <StepNav statuses={pipeline.statuses as any} pipelineId={pipeline.id} />
      </div>
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm text-gray-600 dark:text-gray-300">Progress</div>
        <div class="flex items-center gap-3">
          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{percent(pipeline)}%</div>
        </div>
      </div>
      <div class="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div class="h-full bg-blue-600" style={`width: ${percent(pipeline)}%`}></div>
      </div>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900 space-y-2">
      <div class="text-sm text-gray-600 dark:text-gray-300">This is a placeholder for the pipeline-scoped Save/Library page. Use the global Library page for now.</div>
      <a class="text-sm text-blue-600 hover:underline" href="/app/library">Go to global Library</a>
    </div>

    <StepFooter current="save" pipelineId={pipeline.id} />
  </div>
{/if}
