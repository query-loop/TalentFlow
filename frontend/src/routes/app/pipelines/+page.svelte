<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';
  import { listPipelines, createPipeline, deletePipeline, type Pipeline } from '$lib/pipelines';

  type StepStatus = 'pending' | 'active' | 'complete' | 'failed';
  type StepKey = 'extract' | 'generate' | 'keywords' | 'ats' | 'export' | 'save';

  const steps = [
    { key: 'extract' as const,  label: 'Extract JD' },
    { key: 'generate' as const, label: 'Generate' },
    { key: 'keywords' as const, label: 'Keywords' },
    { key: 'ats' as const,      label: 'ATS' },
    { key: 'export' as const,   label: 'Export' },
    { key: 'save' as const,     label: 'Save' }
  ];

  let pipelines: Pipeline[] = [];
  let loading = true;
  let error: string | null = null;
  let creating = false;
  let showModal = false;
  let form: { name: string; company?: string; jdId: string; resumeId: string } = { name: '', company: '', jdId: '', resumeId: '' };

  async function load() {
    loading = true; error = null;
    try {
      pipelines = await listPipelines();
    } catch (e: any) {
      error = e?.message || 'Failed to load pipelines';
    } finally {
      loading = false;
    }
  }

  onMount(() => { load(); });

  function percent(p: Pipeline) {
    const total = steps.length;
    const done = steps.filter(s => p.statuses[s.key] === 'complete').length;
    return Math.round((done / Math.max(total, 1)) * 100);
  }
</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
  <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="layers" /> All pipelines</h1>
    <button
      on:click={() => { showModal = true; form = { name: '', company: '', jdId: '', resumeId: '' }; }}
      class="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition disabled:opacity-60"
      disabled={creating}
    >
      <Icon name="plus" size={16} /> New pipeline
    </button>
  </div>

  {#if error}
    <div class="text-sm text-red-600">{error}</div>
  {/if}

  {#if loading}
    <div>Loading…</div>
  {:else if !pipelines.length}
    <div class="text-gray-600 dark:text-gray-400">No pipelines yet.</div>
  {:else}
    <ul class="grid gap-3">
      {#each pipelines as p}
        <li class="relative border rounded-lg p-3 bg-white/80 backdrop-blur-sm dark:bg-slate-800/70 border-slate-200 dark:border-slate-700">
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
              <a
                href={`/app/pipeline/${p.id}`}
                class="inline-flex items-center text-sm px-3 py-1.5 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-gray-800 dark:text-gray-100 shadow-sm hover:bg-white/60 dark:hover:bg-white/20 transition"
              >View</a>
              <button
                class="inline-flex items-center justify-center w-8 h-8 rounded-md backdrop-blur-sm bg-white/40 dark:bg-white/10 border border-white/50 dark:border-white/10 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-white/60 dark:hover:bg-white/20"
                on:click={async ()=>{ if (confirm('Delete this pipeline?')) { await deletePipeline(p.id); await load(); } }}
                title="Delete"
              >
                <Icon name="trash" size={16} />
              </button>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}

  {#if showModal}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" on:click={() => showModal=false}>
      <div class="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-md p-5" on:click|stopPropagation>
        <div class="text-lg font-semibold mb-4">Create pipeline</div>
        <form on:submit|preventDefault={async () => {
          creating = true; error = null;
          try {
            const payload: any = { name: form.name.trim() };
            if (form.jdId.trim()) payload.jdId = form.jdId.trim();
            if (form.resumeId.trim()) payload.resumeId = form.resumeId.trim();
            const created = await createPipeline(payload);
            showModal = false;
            window.location.href = `/app/pipeline/${created.id}`;
          } catch (e: any) {
            error = e?.message || 'Failed to create pipeline';
          } finally {
            creating = false;
          }
        }} class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">Name <span class="text-red-600">*</span></label>
            <input bind:value={form.name} required class="w-full border rounded px-3 py-2 bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700" placeholder="e.g. Backend Engineer at Acme" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium mb-1">JD ID</label>
              <input bind:value={form.jdId} class="w-full border rounded px-3 py-2 bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700" placeholder="Optional" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Resume ID</label>
              <input bind:value={form.resumeId} class="w-full border rounded px-3 py-2 bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700" placeholder="Optional" />
            </div>
          </div>
          <div class="flex items-center justify-end gap-2 pt-2">
            <button type="button" class="px-3 py-1.5 border rounded" on:click={() => showModal=false}>Cancel</button>
            <button type="submit" class="px-3 py-1.5 bg-blue-600 text-white rounded disabled:opacity-60" disabled={creating || !form.name.trim()}>Create</button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</section>
