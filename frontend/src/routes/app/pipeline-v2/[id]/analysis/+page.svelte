<script lang="ts">
  import { page } from '$app/stores';
  import { getPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';
  import { v2PathForStep } from '$lib/pipelineTrackerV2';

  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let loading = true;

  async function load() {
    if (!id) return;
    try { loading = true; error = null; pipe = await getPipelineV2(id); }
    catch(e:any){ error = e?.message || 'Failed to load pipeline'; }
    finally { loading = false; }
  }
  $: if (id) load();

  $: scoring = pipe?.artifacts && (pipe.artifacts as any).scoring;
</script>

{#if loading}
  <div class="p-6">
    <div class="animate-pulse space-y-4">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
      <div class="h-24 bg-slate-200 dark:bg-slate-700 rounded"></div>
    </div>
  </div>
{:else if error}
  <div class="m-6 border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
    <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
      <Icon name="alert-circle" size={16} />
      <span class="font-medium">Error loading pipeline</span>
    </div>
    <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
  </div>
{:else if pipe}
  <div class="p-4 md:p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Analysis</h1>
      <div class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
        <Icon name="activity" size={12} class="inline mr-1" /> Overview and insights
      </div>
    </div>

    {#if scoring}
      <!-- Score overview cards -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div class="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-center">
          <div class="text-2xl font-bold">{scoring.overall_score ?? '--'}%</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">Overall</div>
        </div>
        <div class="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-center">
          <div class="text-2xl font-bold">{scoring.skills_score ?? '--'}%</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">Skills</div>
        </div>
        <div class="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-center">
          <div class="text-2xl font-bold">{scoring.keywords_score ?? '--'}%</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">Keywords</div>
        </div>
        <div class="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-center">
          <div class="text-2xl font-bold">{scoring.experience_score ?? '--'}%</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">Experience</div>
        </div>
        <div class="p-3 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-center">
          <div class="text-2xl font-bold">{scoring.education_score ?? '--'}%</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">Education</div>
        </div>
      </div>

      <!-- Quick links -->
      <div class="grid md:grid-cols-2 gap-4">
        <a href={v2PathForStep('gaps', id)} class="block p-4 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium">Gaps</div>
            <Icon name="x-circle" size={16} class="text-red-500" />
          </div>
          <div class="text-xs text-slate-600 dark:text-slate-400 mt-1">{scoring.gaps?.length || 0} items</div>
        </a>
        <a href={v2PathForStep('differentiators', id)} class="block p-4 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium">Differentiators</div>
            <Icon name="star" size={16} class="text-blue-500" />
          </div>
          <div class="text-xs text-slate-600 dark:text-slate-400 mt-1">{scoring.strengths?.length || 0} items</div>
        </a>
      </div>

      <!-- Recommendations -->
      {#if scoring.recommendations?.length}
        <div class="border rounded-lg bg-white dark:bg-slate-800 p-4">
          <div class="text-sm font-semibold mb-2">Recommendations</div>
          <ul class="text-xs space-y-2">
            {#each scoring.recommendations as rec}
              <li class="p-2 rounded border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/10">{rec}</li>
            {/each}
          </ul>
        </div>
      {/if}
    {:else}
      <div class="border rounded-lg bg-white dark:bg-slate-800 p-4 text-sm text-slate-600 dark:text-slate-400">
        No analysis available yet. Run scoring from the JD step once both JD and resume are present.
      </div>
    {/if}
  </div>
{/if}
