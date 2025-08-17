<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';

  type StepStatus = 'pending' | 'active' | 'complete';
  type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
  type PipelineInstance = { id: string; name: string; createdAt: number; statuses: Record<StepKey, StepStatus> };

  const steps = [
    { key: 'extract' as const,  label: 'Extract JD' },
    { key: 'generate' as const, label: 'Generate' },
    { key: 'keywords' as const, label: 'Keywords' },
    { key: 'ats' as const,      label: 'ATS' },
    { key: 'export' as const,   label: 'Export' },
    { key: 'save' as const,     label: 'Save' }
  ];

  let pipelines: PipelineInstance[] = [];
  let loading = true;

  onMount(() => {
    try {
      const raw = localStorage.getItem('tf_pipelines');
      pipelines = raw ? JSON.parse(raw) : [];
      pipelines.sort((a,b) => b.createdAt - a.createdAt);
    } catch { pipelines = []; }
    loading = false;
  });

  function percent(p: PipelineInstance) {
    const total = steps.length;
    const done = steps.filter(s => p.statuses[s.key] === 'complete').length;
    return Math.round((done / Math.max(total, 1)) * 100);
  }
</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="layers" /> All pipelines</h1>
    <a href="/app" class="text-sm text-blue-600 hover:underline">Back to dashboard</a>
  </div>

  {#if loading}
    <div>Loading…</div>
  {:else if !pipelines.length}
    <div class="text-gray-600 dark:text-gray-400">No pipelines yet.</div>
  {:else}
    <ul class="grid gap-3">
      {#each pipelines as p}
        <li class="border rounded-lg p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <div class="font-medium truncate">{p.name}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{new Date(p.createdAt).toLocaleString()}</div>
          </div>
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 flex-1 flex-nowrap overflow-x-auto whitespace-nowrap pr-1">
              {#each steps as s, i}
                {@const st = p.statuses[s.key]}
                <div class={`whitespace-nowrap inline-flex items-center gap-2 px-2.5 py-1.5 rounded-full border text-xs ${st === 'complete' ? 'border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-300 bg-emerald-50/40 dark:bg-emerald-900/20' : st === 'active' ? 'border-indigo-300 text-indigo-700 dark:border-indigo-700 dark:text-indigo-300 bg-indigo-50/40 dark:bg-indigo-900/20' : 'border-slate-200 text-gray-700 dark:border-slate-700 dark:text-gray-200'}`}>
                  <span class={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] ${st === 'complete' ? 'bg-emerald-600 text-white' : st === 'active' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300'}`}>{i+1}</span>
                  <span class="font-medium">{s.label}</span>
                </div>
                {#if i < steps.length - 1}
                  <span class="text-gray-400 dark:text-gray-500"><Icon name="arrow-right" size={14}/></span>
                {/if}
              {/each}
            </div>
            <div class="flex items-center gap-3">
              <div class="text-xs text-gray-500 dark:text-gray-400">{percent(p)}%</div>
              <a href={`/app/pipeline/${p.id}`} class="inline-flex items-center text-sm px-3 py-1.5 rounded-none bg-blue-600 text-white hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 font-medium shadow-sm transition">View</a>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
