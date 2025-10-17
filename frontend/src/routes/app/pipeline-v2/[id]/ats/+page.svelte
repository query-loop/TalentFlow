<script lang="ts">
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, patchPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';

  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let loading = true;
  let error: string | null = null;
  let coverage: number | null = null;
  let matched: string[] = [];
  let missing: string[] = [];

  async function load() {
    if (!id) return;
    try {
      loading = true; error = null; pipe = await getPipelineV2(id);
      computeCoverage();
    } catch (e:any) { error = e?.message || 'Failed to load pipeline'; }
    finally { loading = false; }
  }

  function tokenize(text: string): string[] {
    return (text || '')
      .toLowerCase()
      .replace(/[\W_]+/g, ' ')
      .split(/\s+/)
      .filter(Boolean);
  }

  function computeCoverage() {
    const jd = pipe?.artifacts && (pipe.artifacts as any).jd;
    const resume = pipe?.artifacts && (pipe.artifacts as any).resume;
    const keys: string[] = jd?.key_requirements || [];
    if (!keys.length || !resume?.text) {
      coverage = null; matched = []; missing = [];
      return;
    }
    const words = new Set(tokenize(resume.text));
    matched = keys.filter(k => tokenize(k).some(w => words.has(w)));
    missing = keys.filter(k => !matched.includes(k));
    coverage = Math.round((matched.length / keys.length) * 100);
  }

  async function saveAtsArtifacts() {
    if (!pipe || coverage === null) return;
    const artifacts: any = { ...(pipe.artifacts || {}) };
    artifacts.ats = { coverage, matched, missing, updatedAt: Date.now() };
    try { pipe = await patchPipelineV2(pipe.id, { artifacts }); } catch (e:any) { error = e?.message || 'Save failed'; }
  }

  $: if (id) load();
</script>

{#if loading}
  <div class="p-4">
    <div class="animate-pulse space-y-3">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
      <div class="h-24 bg-slate-200 dark:bg-slate-700 rounded"></div>
    </div>
  </div>
{:else if error}
  <div class="m-4 border border-red-200 bg-red-50 dark:bg-red-900/20 rounded p-3 text-sm text-red-800">{error}</div>
{:else}
  <div class="p-4 space-y-4">
    <div class="flex items-center justify-between">
      <div class="text-sm font-semibold">ATS Keyword Coverage</div>
      <div class="text-xs text-slate-500">Based on JD key requirements vs resume</div>
    </div>

    {#if coverage === null}
      <div class="border rounded p-4 bg-white dark:bg-slate-800 text-sm text-slate-600">No JD key requirements or resume text available. Add JD in Intake and attach a resume to the pipeline.</div>
    {:else}
      <div class="border rounded p-4 bg-white dark:bg-slate-800 space-y-3">
        <div class="flex items-center gap-3">
          <div class="text-3xl font-bold">{coverage}%</div>
          <div class="text-xs text-slate-600">Keyword match</div>
        </div>

        <div class="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <div class="font-medium mb-2">Matched ({matched.length})</div>
            {#if matched.length}
              <ul class="list-disc pl-5 text-xs">
                {#each matched as m}
                  <li>{m}</li>
                {/each}
              </ul>
            {:else}
              <div class="text-xs text-slate-500">No matches found.</div>
            {/if}
          </div>
          <div>
            <div class="font-medium mb-2">Missing ({missing.length})</div>
            {#if missing.length}
              <ul class="list-disc pl-5 text-xs text-red-700 dark:text-red-300">
                {#each missing as mm}
                  <li>{mm}</li>
                {/each}
              </ul>
            {:else}
              <div class="text-xs text-slate-500">All key requirements present.</div>
            {/if}
          </div>
        </div>

        <div class="mt-3 flex items-center gap-2">
          <button class="px-3 py-1.5 rounded bg-blue-600 text-white" on:click={saveAtsArtifacts}>Save ATS Results</button>
          <div class="text-xs text-slate-500">Save matched/missing keywords to pipeline artifacts.</div>
        </div>
      </div>
    {/if}

    <StepFooterV2 current="ats" pipelineId={id} />
  </div>
{/if}
