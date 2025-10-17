<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '$lib/Icon.svelte';
  import { getPipeline, type Pipeline } from '$lib/pipelines';
  import { getActivePipelineId } from '$lib/pipelineTracker';

  type LibraryItem = {
    id: number;
    name: string;
    kind: 'uploaded' | 'draft' | string;
    source: string;
    text: string;
    meta?: any;
    createdAt: string;
    updatedAt: string;
  };

  let items: LibraryItem[] = [];
  let loading = false;
  let error = '';
  let activePipeline: Pipeline | null = null;
  let pipelineHeaderName = '';

  async function load() {
    loading = true; error = '';
    try {
  const res = await fetch(`/api/library`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      items = await res.json();
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally { loading = false; }
  }

  function useInGenerate(item: LibraryItem) {
    try {
      // Persist selection so Generate page picks it up
      localStorage.setItem('tf_generate_selected_resume', `lib_${item.id}`);
    } catch {}
    // Navigate to Generate
    window.location.href = '/app/generate';
  }

  onMount(async () => {
    await load();
    try {
      const pid = getActivePipelineId();
      if (pid) {
        activePipeline = await getPipeline(pid);
        pipelineHeaderName = (activePipeline?.name || activePipeline?.company || '').trim();
      }
    } catch {}
  });
  function kindLabel(k: string) { return k === 'uploaded' ? 'Uploaded' : (k === 'draft' ? 'Draft' : k); }
  function previewText(t: string) {
    const lines = (t || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const head = (lines[0] || '') + (lines[1] ? ` — ${lines[1]}` : '');
    return head.replace(/\s+/g, ' ').slice(0, 120);
  }
</script>

<section class="space-y-4">
  <h1 class="text-xl font-semibold flex items-center gap-2">
    <Icon name="folder"/> Library
    {#if pipelineHeaderName}
      <span class="text-sm text-gray-500">— {pipelineHeaderName}</span>
    {/if}
  </h1>
  <p class="text-sm text-gray-600">Your saved resumes and drafts will appear here.</p>

  {#if loading}
    <div class="text-sm text-gray-500">Loading…</div>
  {:else if error}
    <div class="text-sm text-red-600">{error}</div>
  {:else if !items.length}
    <div class="text-sm text-gray-500">No items yet.</div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {#each items as it}
        <div class="border rounded-lg p-3 bg-white/80 dark:bg-slate-800/70 border-slate-200 dark:border-slate-700">
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="text-sm font-medium">{kindLabel(it.kind)} — {it.name}</div>
              <div class="text-[11px] text-gray-500">Updated {new Date(it.updatedAt).toLocaleString()}</div>
            </div>
            <button class="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-600/95" on:click={() => useInGenerate(it)}>Use in Generate</button>
          </div>
          <div class="mt-2 text-xs text-gray-700 dark:text-gray-300 border rounded px-2 py-1 bg-gray-50/70 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700">
            {previewText(it.text)}{it.text.length > 120 ? '…' : ''}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>
