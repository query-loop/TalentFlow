<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import type { V2StepKey } from '$lib/pipelineTrackerV2';
  export let current: V2StepKey;
  export let canComplete: (() => boolean) | null = null; // kept for API compat; unused
  export let pipelineId: string | undefined = undefined;
</script>

<div class="fixed bottom-4 right-4 z-40">
  <div class="border rounded-lg shadow-lg bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border-slate-200 dark:border-slate-700 p-3 min-w-[260px]">
    <div class="flex items-center justify-between">
      <div class="text-xs text-gray-600 dark:text-gray-300 flex items-center gap-1">
        <Icon name="layers" size={14}/> Pipeline
      </div>
      <div class="text-xs text-gray-900 dark:text-gray-100 capitalize">{current}</div>
    </div>
    <div class="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
      Progression is disabled for v2. Use the step navigation above to move between steps.
      {#if pipelineId}
        <a class="ml-1 text-blue-600 hover:underline" href={`/app/pipeline-v2/${pipelineId}`}>Overview</a>
      {/if}
    </div>
  </div>
</div>
