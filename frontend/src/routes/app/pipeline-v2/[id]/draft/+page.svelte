<script lang="ts">
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';
  
  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let loading = true;
  
  async function loadPipeline() {
    if (!id) return;
    try {
      loading = true;
      error = null;
      pipe = await getPipelineV2(id);
    } catch (e: any) {
      error = e.message || 'Failed to load pipeline';
    } finally {
      loading = false;
    }
  }
  
  $: if (id) loadPipeline();
  
  // Get template from intake data
  $: template = (pipe?.artifacts?.intake as any)?.template || 'standard';
</script>

{#if loading}
  <div class="space-y-4">
    <div class="border rounded-lg p-6">
      <div class="animate-pulse space-y-4">
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
        <div class="h-64 bg-slate-200 dark:bg-slate-700 rounded"></div>
      </div>
    </div>
  </div>
{:else if error}
  <div class="border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
    <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
      <Icon name="alert-circle" size={16} />
      <span class="font-medium">Error loading pipeline</span>
    </div>
    <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
  </div>
{:else if pipe}
  <div class="space-y-6">
    <!-- Draft Header -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Resume Draft Generation
          </h2>
          <p class="text-sm text-slate-600 dark:text-slate-400">
            Generate and edit your tailored resume draft for {pipe.company || 'this position'}
          </p>
        </div>
        <div class="flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300">
          <Icon name="edit" size={12} />
          Draft Mode
        </div>
      </div>
    </div>

    <!-- Template Info -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">
        Selected Template
      </h3>
      <div class="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
        <Icon name="file-text" size={16} class="text-blue-600" />
        <div>
          <div class="text-sm font-medium text-slate-900 dark:text-slate-100 capitalize">{template}</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">
            {#if template === 'standard'}
              Clean, professional template suitable for most industries
            {:else if template === 'creative'}
              Modern design with visual elements for creative roles
            {:else if template === 'minimal'}
              Simple, text-focused layout for traditional industries
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Generation Status -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">
        Generation Progress
      </h3>
      <div class="space-y-4">
        <div class="flex items-center gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <Icon name="clock" size={16} class="text-amber-600" />
          <div>
            <div class="text-sm font-medium text-amber-800 dark:text-amber-200">
              Draft Generation Pending
            </div>
            <div class="text-xs text-amber-700 dark:text-amber-300">
              Resume draft has not been generated yet. This step will create a tailored resume based on the job requirements.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Draft Preview Placeholder -->
    <div class="border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h3 class="text-base font-medium text-slate-900 dark:text-slate-100 mb-4">
        Draft Preview
      </h3>
      <div class="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg p-8 text-center">
        <Icon name="file-plus" size={24} class="text-slate-400 mx-auto mb-3" />
        <div class="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
          No draft generated yet
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-500">
          Complete the previous steps to generate your tailored resume draft
        </div>
      </div>
    </div>
  </div>

  <StepFooterV2 current="draft" pipelineId={id} />
{/if}
