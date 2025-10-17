<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, patchPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';

  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let loading = true;
  let error: string | null = null;
  let actions: { id: string; text: string; done?: boolean }[] = [];

  async function load() {
    if (!id) return;
    try {
      loading = true; error = null; pipe = await getPipelineV2(id);
      buildActionsFromArtifacts();
    } catch (e:any) { error = e?.message || 'Failed to load pipeline'; }
    finally { loading = false; }
  }

  function buildActionsFromArtifacts() {
    const scoring = pipe?.artifacts && (pipe.artifacts as any).scoring;
    const ats = pipe?.artifacts && (pipe.artifacts as any).ats;
    const existing = pipe?.artifacts && (pipe.artifacts as any).actions;
    const byId = new Map<string, any>();

    // Add recommendations
    if (scoring?.recommendations?.length) {
      scoring.recommendations.forEach((r:string, i:number) => byId.set(`rec_${i}`, { id: `rec_${i}`, text: r }));
    }

    // Add gaps as actions
    if (scoring?.gaps?.length) {
      scoring.gaps.forEach((g:string, i:number) => byId.set(`gap_${i}`, { id: `gap_${i}`, text: `Address gap: ${g}` }));
    }

    // Add ATS missing keywords
    if (ats?.missing?.length) {
      ats.missing.forEach((m:string, i:number) => byId.set(`ats_${i}`, { id: `ats_${i}`, text: `Include keyword: ${m}` }));
    }

    // Merge existing saved actions (preserve done state)
    const list = Array.from(byId.values()).map((a:any) => {
      const saved = existing && Array.isArray(existing) ? existing.find((s:any)=>s.id===a.id) : null;
      return { id: a.id, text: a.text, done: saved ? saved.done : false };
    });

    actions = list;
  }

  async function toggleDone(idx:number) {
    actions[idx].done = !actions[idx].done;
    await saveActions();
  }

  async function saveActions() {
    if (!pipe) return;
    const artifacts: any = { ...(pipe.artifacts || {}) };
    artifacts.actions = actions.map(a=>({ id: a.id, text: a.text, done: !!a.done }));
    try { pipe = await patchPipelineV2(pipe.id, { artifacts }); } catch (e:any) { error = e?.message || 'Save failed'; }
  }

  $: if (id) load();
</script>

{#if loading}
  <div class="p-4">
    <div class="animate-pulse space-y-3">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
      <div class="h-20 bg-slate-200 dark:bg-slate-700 rounded"></div>
    </div>
  </div>
{:else if error}
  <div class="m-4 border border-red-200 bg-red-50 dark:bg-red-900/20 rounded p-3 text-sm text-red-800">{error}</div>
{:else}
  <div class="p-4 space-y-4">
    <div class="flex items-center justify-between">
      <div class="text-sm font-semibold">Suggested Actions</div>
      <div class="text-xs text-slate-500">Quick wins and tasks to improve fit</div>
    </div>

    {#if actions.length === 0}
      <div class="border rounded p-4 bg-white dark:bg-slate-800 text-sm text-slate-600">No suggested actions found. Run analysis to generate recommendations.</div>
    {:else}
      <ul class="space-y-2">
        {#each actions as act, i}
          <li class="border rounded p-3 bg-white dark:bg-slate-800 flex items-start justify-between">
            <div class="flex-1 text-sm">
              <div class="font-medium">{act.text}</div>
            </div>
            <div class="flex items-center gap-2">
              <button class={`px-2 py-1 text-xs rounded ${act.done ? 'bg-emerald-600 text-white' : 'bg-slate-100 dark:bg-slate-700'}`} on:click={()=>toggleDone(i)}>{act.done ? 'Done' : 'Mark done'}</button>
            </div>
          </li>
        {/each}
      </ul>
      <div class="mt-3 text-xs text-slate-500">Changes are saved automatically.</div>
    {/if}
  </div>
{/if}
