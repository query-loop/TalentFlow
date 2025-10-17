<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { stepOrder, stepPaths, type StepKey } from '$lib/pipelineTracker';
  // Optional: consumer may omit; default to undefined to mark as optional in TS
  export let statuses: Record<StepKey, 'pending'|'active'|'complete'|'failed'> | undefined = undefined;
  // Optional: when provided, links target nested pipeline path
  export let pipelineId: string | undefined = undefined;

  const nestedPaths: Record<StepKey, (id: string) => string> = {
    extract: (id) => `/app/pipeline/${id}/extract`,
    profile: (id) => `/app/pipeline/${id}/profile`,
    generate: (id) => `/app/pipeline/${id}/generate`,
    keywords: (id) => `/app/pipeline/${id}/keywords`,
    ats: (id) => `/app/pipeline/${id}/ats`,
    export: (id) => `/app/pipeline/${id}/export`,
    save: (id) => `/app/pipeline/${id}/save`,
  };
</script>

<nav aria-label="Pipeline steps" class="w-full overflow-x-auto no-scrollbar">
  <ol class="flex items-center gap-3 min-w-max">
    {#each stepOrder as key, i}
      <li class="flex items-center gap-2">
        <a href={pipelineId ? nestedPaths[key](pipelineId) : stepPaths[key]}
           class={`group flex items-center gap-2 px-2.5 py-1.5 rounded border transition text-xs
             ${statuses?.[key] === 'complete' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' :
               statuses?.[key] === 'active' ? 'border-blue-200 bg-blue-50 text-blue-700' :
               'border-slate-200 bg-white text-gray-700 dark:bg-slate-800 dark:text-gray-200'}`}
           title={`Go to ${key}`}>
          {#if key === 'extract'}<Icon name="tag" size={14} />{/if}
          {#if key === 'profile'}<Icon name="user" size={14} />{/if}
          {#if key === 'generate'}<Icon name="sparkles" size={14} />{/if}
          {#if key === 'keywords'}<Icon name="tag" size={14} />{/if}
          {#if key === 'ats'}<Icon name="shield-check" size={14} />{/if}
          {#if key === 'export'}<Icon name="layers" size={14} />{/if}
          {#if key === 'save'}<Icon name="folder" size={14} />{/if}
          <span class="capitalize">{key}</span>
        </a>
        {#if i < stepOrder.length - 1}
          <span class="w-6 h-[2px] bg-slate-200 dark:bg-slate-700"></span>
        {/if}
      </li>
    {/each}
  </ol>
</nav>

<style>
  .no-scrollbar { scrollbar-width: none; }
  .no-scrollbar::-webkit-scrollbar { display: none; }
</style>
