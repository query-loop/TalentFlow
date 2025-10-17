<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import StepFooter from '$lib/components/StepFooter.svelte';
  import { getPipeline, patchPipeline, type Pipeline } from '$lib/pipelines';
  import StepNav from '$lib/components/StepNav.svelte';

  // Local generate inputs
  let job = '';
  let result: any = null;
  let loading = false;
  let error = '';

  let pipeline: Pipeline | null = null;
  $: pid = $page.params.id;

  async function load() {
    try { pipeline = await getPipeline(pid); }
    catch (e:any) { error = e?.message || 'Failed to load pipeline'; pipeline = null; }
  }

  onMount(async () => { await load(); });

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
      <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="sparkles"/> Generate — <span class="text-sm text-gray-600">{pipeline.name}</span></h1>
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

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900 space-y-3">
      <div class="text-sm text-gray-600 dark:text-gray-300">Generate a resume for this pipeline.</div>
      <label class="text-sm text-gray-700 dark:text-gray-200">Job focus</label>
      <textarea class="border rounded p-2 min-h-[140px] w-full bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-100" bind:value={job} placeholder="Summarize target role..." />
      <div>
        <button class="px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50" disabled={loading || !job.trim()} on:click={() => { loading=true; setTimeout(()=>{ result={ summary: 'Draft summary…', skills:['Leadership','Python'], experience:['Did X','Did Y'] }; loading=false; }, 400); }}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>
      {#if result}
        <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 divide-y divide-slate-200 dark:divide-slate-700">
          <div class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">Preview</div>
          <div class="p-4 space-y-2">
            <div class="text-sm"><span class="font-medium">Summary:</span> {result.summary}</div>
            <div class="text-sm"><span class="font-medium">Skills:</span> {(result.skills || []).join(', ')}</div>
            <div class="text-sm"><span class="font-medium">Experience:</span>
              <ul class="list-disc pl-5">
                {#each (result.experience || []) as e}
                  <li>{e}</li>
                {/each}
              </ul>
            </div>
          </div>
        </div>
      {/if}
    </div>

    <StepFooter current="generate" pipelineId={pipeline.id} />
  </div>
{/if}
