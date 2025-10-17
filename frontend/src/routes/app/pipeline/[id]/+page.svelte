<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getPipeline, patchPipeline, runPipeline, type Pipeline } from '$lib/pipelines';
  import StepNav from '$lib/components/StepNav.svelte';
  import { setActivePipelineId } from '$lib/pipelineTracker';

  type StepStatus = 'pending' | 'active' | 'complete' | 'failed';
  type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';
  type Step = { id: StepKey; title: string; status: StepStatus; description?: string };

  const pipelineSteps = [
    { key: 'extract' as const,  label: 'Extract JD', desc: 'Paste or upload job description' },
    { key: 'profile' as const,  label: 'Profile',    desc: 'Build candidate profile' },
    { key: 'generate' as const, label: 'Generate',   desc: 'Create a theme-aware draft' },
    { key: 'keywords' as const, label: 'Keywords',   desc: 'Analyze terms and gaps' },
    { key: 'ats' as const,      label: 'ATS',        desc: 'Score and get tips' },
    { key: 'export' as const,   label: 'Export',     desc: 'Export to PDF/DOCX' },
    { key: 'save' as const,     label: 'Save',       desc: 'Store in your Library' }
  ];

  let base: Pipeline | null = null;
  let steps: Step[] = [];
  let error: string | null = null;
  let saving = false;
  let running = false;
  let runLog: string[] = [];
  $: id = $page.params.id;

  let editingName = false;
  let nameDraft = '';

  function deriveSteps(p: Pipeline | null): Step[] {
    if (!p) return [];
    return pipelineSteps.map(s => ({
      id: s.key,
      title: s.label,
      status: (p.statuses?.[s.key] as StepStatus) || 'pending',
      description: s.desc
    }));
  }

  function ensureSingleActive(statuses: Record<StepKey, StepStatus>): Record<StepKey, StepStatus> {
    const order: StepKey[] = ['extract','profile','generate','keywords','ats','export','save'];
    const firstPending = order.find(k => statuses[k] !== 'complete');
    const out: Record<StepKey, StepStatus> = { ...statuses } as any;
    for (const k of order) {
      out[k] = out[k] === 'complete' ? 'complete' : 'pending';
    }
    if (firstPending) out[firstPending] = 'active';
    return out;
  }

  async function load() {
    error = null;
    try {
      base = await getPipeline(id);
      // Auto-ensure one active step if none set
      if (base) {
        const hasActive = Object.values(base.statuses || {}).includes('active');
        if (!hasActive) {
          const updated = ensureSingleActive(base.statuses as any);
          try {
            base = await patchPipeline(base.id, { statuses: updated as any });
          } catch {}
        }
      }
      steps = deriveSteps(base);
    } catch (e: any) {
      base = null; steps = []; error = e?.message || 'Failed to load pipeline';
    }
  }

  onMount(async () => {
    await load(); nameDraft = base?.name || '';
    if (base?.id) setActivePipelineId(base.id);
  });

  function percent(p: Pipeline | null) {
    if (!p) return 0;
    const total = pipelineSteps.length;
    const done = (Object.values(p.statuses || {}) as StepStatus[]).filter(s => s === 'complete').length;
    return Math.round((done / Math.max(total, 1)) * 100);
  }

  // Manual step controls removed; status progresses automatically based on app actions

  async function runAll() {
    if (!id) return;
    running = true; error = null; runLog = [];
    try {
      const res = await runPipeline(id);
      runLog = res.log;
      base = res.pipeline;
      steps = deriveSteps(base);
    } catch (e:any) {
      error = e?.message || 'Failed to run pipeline';
    } finally { running = false; }
  }
</script>

{#if error}
  <div class="p-6">
    <div class="rounded-lg border border-red-200 dark:border-red-800 p-6 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200">
      {error}
    </div>
  </div>
{:else if !base}
  <div class="p-6">
    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-6 bg-white dark:bg-gray-900">
      <p class="text-gray-600 dark:text-gray-300">Pipeline not found.</p>
    </div>
  </div>
{:else}
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        {#if editingName}
          <input
            bind:value={nameDraft}
            class="text-xl font-semibold bg-transparent border-b border-blue-500 focus:outline-none text-gray-900 dark:text-gray-100"
            on:keydown={(e: KeyboardEvent) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                (async () => {
                  if (!base) return;
                  saving = true;
                  try { base = await patchPipeline(base.id, { name: nameDraft.trim() }); steps = deriveSteps(base); editingName = false; }
                  catch (err:any) { error = err?.message || 'Failed to rename'; }
                  finally { saving = false; }
                })();
              } else if (e.key === 'Escape') {
                nameDraft = base?.name || '';
                editingName = false;
              }
            }}
            on:blur={async () => {
              if (!base) return;
              if (nameDraft.trim() === base.name) { editingName = false; return; }
              saving = true;
              try { base = await patchPipeline(base.id, { name: nameDraft.trim() }); steps = deriveSteps(base); }
              catch (err:any) { error = err?.message || 'Failed to rename'; }
              finally { saving = false; editingName = false; }
            }}
          />
        {:else}
          <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{base.name}</h1>
        {/if}
        <button
          class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-700 dark:text-gray-200 hover:bg-white/60 dark:hover:bg-white/20"
          on:click={() => { nameDraft = base?.name || ''; editingName = true; }}
          title="Edit name"
        >
          <Icon name="pencil" size={16} />
        </button>
      </div>
      <a href="/app/pipelines" class="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline">
        <Icon name="arrow-right" class="w-4 h-4 rotate-180" />
        Back to all pipelines
      </a>
    </div>

    <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-5 bg-white dark:bg-gray-900">
      <div class="mb-3 flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
        <div class="flex items-center gap-2">
          <span class="text-gray-500">Pipeline</span>
          <span class="text-gray-400">•</span>
          <span class="truncate" title={base.name}>{base.name}</span>
        </div>
        <div class="text-[11px] text-gray-500">Created {new Date(base.createdAt).toLocaleString()}</div>
      </div>
      <div class="mb-3">
        <StepNav statuses={base.statuses as any} pipelineId={base.id} />
      </div>
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm text-gray-600 dark:text-gray-300">Progress</div>
        <div class="flex items-center gap-3">
          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{percent(base)}%</div>
          <!-- Removed manual Run button to encourage guided step navigation -->
        </div>
      </div>
      <div class="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div class="h-full bg-blue-600" style={`width: ${percent(base)}%`}></div>
      </div>
    </div>

    

    <!-- Run log removed to reduce noise; guided navigation preferred -->

    <!-- Inline editing replaces the bottom edit form -->
  </div>
{/if}
