<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  type StepStatus = 'pending' | 'active' | 'complete';
  type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
  type PipelineInstance = { id: string; name: string; createdAt: number; statuses: Record<StepKey, StepStatus> };
  type Step = { id: StepKey; title: string; status: StepStatus; description?: string };

  const pipelineSteps = [
    { key: 'extract' as const,  label: 'Extract JD', desc: 'Paste or upload job description' },
    { key: 'generate' as const, label: 'Generate',   desc: 'Create a theme-aware draft' },
    { key: 'keywords' as const, label: 'Keywords',   desc: 'Analyze terms and gaps' },
    { key: 'ats' as const,      label: 'ATS',        desc: 'Score and get tips' },
    { key: 'export' as const,   label: 'Export',     desc: 'Export to PDF/DOCX' },
    { key: 'save' as const,     label: 'Save',       desc: 'Store in your Library' }
  ];

  let base: PipelineInstance | null = null;
  let steps: Step[] = [];
  $: id = $page.params.id;

  function loadPipelines(): PipelineInstance[] {
    try {
      const raw = localStorage.getItem('tf_pipelines');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveActive(id: string) {
    localStorage.setItem('tf_active_pipeline', id);
  }

  function deriveSteps(p: PipelineInstance | null): Step[] {
    if (!p) return [];
    return pipelineSteps.map(s => ({
      id: s.key,
      title: s.label,
      status: (p.statuses?.[s.key] as StepStatus) || 'pending',
      description: s.desc
    }));
  }

  onMount(() => {
    const list = loadPipelines();
    base = list.find(p => p.id === id) || null;
    if (base) saveActive(base.id);
    steps = deriveSteps(base);
  });

  function percent(p: PipelineInstance | null) {
    if (!p) return 0;
    const total = pipelineSteps.length;
    const done = (Object.values(p.statuses || {}) as StepStatus[]).filter(s => s === 'complete').length;
    return Math.round((done / Math.max(total, 1)) * 100);
  }
</script>

{#if !base}
  <div class="p-6">
    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-6 bg-white dark:bg-gray-900">
      <p class="text-gray-600 dark:text-gray-300">Pipeline not found.</p>
    </div>
  </div>
{:else}
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{base.name}</h1>
      <a href="/app/pipelines" class="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline">
        <Icon name="arrow-right" class="w-4 h-4 rotate-180" />
        Back to all pipelines
      </a>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900">
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm text-gray-600 dark:text-gray-300">Progress</div>
        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{percent(base)}%</div>
      </div>
      <div class="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div class="h-full bg-blue-600" style={`width: ${percent(base)}%`}></div>
      </div>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div class="p-4 border-b border-gray-200 dark:border-gray-800 text-sm font-medium text-gray-700 dark:text-gray-200">Steps</div>
      <div class="divide-y divide-gray-200 dark:divide-gray-800">
        {#each steps as step, i}
          <div class="p-4 flex items-start gap-4">
            <div class="mt-0.5">
              {#if step.status === 'complete'}
                <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-100 text-green-700 text-xs font-semibold">{i + 1}</span>
              {:else if step.status === 'active'}
                <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">{i + 1}</span>
              {:else}
                <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">{i + 1}</span>
              {/if}
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <div class="font-medium text-gray-900 dark:text-gray-100">{step.title}</div>
                {#if step.status === 'complete'}
                  <span class="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 dark:bg-green-900/20 px-2 py-0.5 rounded-full">
                    <Icon name="check" class="w-3.5 h-3.5" /> Done
                  </span>
                {:else if step.status === 'active'}
                  <span class="inline-flex items-center gap-1 text-xs text-blue-700 bg-blue-50 dark:bg-blue-900/20 px-2 py-0.5 rounded-full">In progress</span>
                {:else}
                  <span class="inline-flex items-center gap-1 text-xs text-gray-600 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-full">Pending</span>
                {/if}
              </div>
              {#if step.description}
                <div class="text-sm text-gray-600 dark:text-gray-300 mt-1">{step.description}</div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}
