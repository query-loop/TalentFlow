<script lang="ts">
  import { v2StepOrder, v2PathForStep, type V2StepKey } from '$lib/pipelineTrackerV2';
  export let statuses: Record<V2StepKey, 'pending' | 'active' | 'complete' | 'failed'> | undefined = undefined;
  export let pipelineId: string | undefined = undefined;
  export let variant: 'default' | 'soft' = 'default';
</script>

<nav aria-label="Pipeline v2 steps" class="w-full overflow-x-auto no-scrollbar">
  <ol class="flex items-center gap-2 min-w-max">
    {#each v2StepOrder as key, i (key)}
      {@const isActive = (statuses?.[key] === 'active') || (!Object.values(statuses || {}).includes('active') && i === 0)}
      <li class="flex items-center gap-2">
        <a
          href={v2PathForStep(key, pipelineId)}
          class={`group inline-flex items-center gap-2 ${variant === 'soft' ? 'px-2 py-1' : 'px-2.5 py-1.5'} rounded border transition text-xs
            ${statuses?.[key] === 'complete'
              ? (variant === 'soft' ? 'border-transparent ring-1 ring-emerald-200 bg-emerald-50/50 text-emerald-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700')
              : isActive
                ? (variant === 'soft' ? 'border-transparent ring-1 ring-blue-200 bg-blue-50/50 text-blue-700' : 'border-blue-200 bg-blue-50 text-blue-700')
                : (variant === 'soft' ? 'border-transparent bg-transparent text-gray-700 dark:text-gray-200 hover:bg-slate-50 dark:hover:bg-slate-800' : 'border-slate-200 bg-white text-gray-700 dark:bg-slate-800 dark:text-gray-200')}`}
          title={`Go to ${key}`}
        >
          <span
            class={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] shrink-0
              ${statuses?.[key] === 'complete'
                ? 'bg-emerald-600 text-white'
                : isActive
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-200 text-gray-700'}`}
          >{i + 1}</span>
          <span class="capitalize">{key}</span>
        </a>
        {#if i < v2StepOrder.length - 1}
          <span class={`h-[2px] ${variant === 'soft' ? 'w-4 bg-slate-200/70 dark:bg-slate-700/70' : 'w-6 bg-slate-200 dark:bg-slate-700'}`}></span>
        {/if}
      </li>
    {/each}
  </ol>
  <style>
    .no-scrollbar::-webkit-scrollbar { display: none; }
  </style>
</nav>
