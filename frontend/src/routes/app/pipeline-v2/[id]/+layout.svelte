<script lang="ts">
  import { page } from '$app/stores';
  import StepNavV2 from '$lib/components/StepNavV2.svelte';
  import Icon from '$lib/Icon.svelte';
  import { v2StepOrder, type V2StepKey } from '$lib/pipelineTrackerV2';
  import { getPipelineV2, type PipelineV2 } from '$lib/pipelinesV2';
  let pipe: PipelineV2 | null = null;
  let error: string | null = null;
  let isLoading = true;
  $: id = $page.params.id;
  async function load(){
    error = null; isLoading = true;
    try { pipe = await getPipelineV2(id); }
    catch(e:any){ error = e?.message || 'Failed to load'; pipe = null; }
    finally { isLoading = false; }
  }
  $: if (id) { load(); }

  // Derive current step from the URL
  const titles: Record<V2StepKey, string> = {
    intake: 'Intake',
    jd: 'Job description',
    profile: 'Profile',
    analysis: 'Analysis',
    ats: 'ATS',
    actions: 'Actions',
    export: 'Export'
  };
  const descs: Partial<Record<V2StepKey, string>> = {
    intake: 'Initial pipeline setup and configuration.',
    jd: 'View and refine the extracted job description details.',
    profile: 'Build and customize your professional profile.',
    analysis: 'Overall scoring summary and quick insights.',
    ats: 'Score against ATS heuristics and improve parsing.',
    actions: 'Define action items and next steps.',
    export: 'Export or share the final resume and artifacts.'
  };

  function getStepColor(step: V2StepKey, pipelineData: PipelineV2): string {
    const status = pipelineData?.statuses?.[step];
    if (status === 'complete') return 'text-green-600';
    if (status === 'active') return 'text-blue-600';
    return 'text-gray-400';
  }

  function getCurrentStep(pipelineData: PipelineV2): V2StepKey {
    // Find the first step that's not complete, or default to the last step
    for (const step of v2StepOrder) {
      if (pipelineData?.statuses?.[step] !== 'complete') {
        return step;
      }
    }
    return v2StepOrder[v2StepOrder.length - 1];
  }

  function stepFromPath(pathname: string): V2StepKey {
    const seg = pathname.split('/').filter(Boolean).at(-1) || '';
    return (v2StepOrder as string[]).includes(seg) ? (seg as V2StepKey) : 'jd';
  }
  $: currentStep = stepFromPath($page.url.pathname);
  let showSteps = false; // mobile toggle for step nav
  let sidebarOpen = false; // collapsible sidebar toggle
</script>

{#if error}
  <div class="p-6">
    <div class="rounded-lg border border-red-200 bg-red-50 text-red-800 p-4">
      <div class="font-medium mb-1">Couldn’t load pipeline</div>
      <div class="text-sm">{error}</div>
      <div class="mt-3 text-xs text-red-700">Try going back to <a href="/app/pipelines-v2" class="underline">Pipelines v2</a>.</div>
    </div>
  </div>
{:else}
  <div class="p-0">
    <!-- Sticky top header -->
    <div class="sticky top-0 z-30 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/70 backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-950/60">
      <div class="px-0 sm:px-0 w-full">
        <div class="flex items-center justify-between py-3 gap-3">
          <div class="flex items-center gap-2 min-w-0">
            <a href="/app/pipelines-v2" class="text-xs sm:text-sm text-blue-600 hover:underline shrink-0">Pipelines v2</a>
            <span class="text-slate-300">/</span>
            <h1 class="text-base sm:text-lg font-semibold truncate" title={pipe?.name || 'Pipeline'}>
              {#if isLoading}
                <span class="inline-block h-4 w-40 rounded bg-slate-200 animate-pulse"></span>
              {:else}
                {pipe?.name}
              {/if}
            </h1>
          </div>
          <div class="hidden sm:flex items-center gap-3 text-xs text-gray-500">
            {#if pipe}
              <span class="hidden md:inline">ID:</span> <span class="font-mono">{pipe.id}</span>
            {/if}
          </div>
        </div>
      </div>
      <!-- Sticky Step Nav -->
      <div class="border-t border-slate-100 dark:border-slate-900">
        <div class="px-3 sm:px-0 sm:container sm:mx-auto py-2">
          <div class="flex items-center justify-between gap-2">
            <div class="flex-1 overflow-hidden">
              <StepNavV2 statuses={pipe?.statuses as any} pipelineId={pipe?.id} variant="soft" />
            </div>
            <!-- Mobile step switcher button -->
            <button class="sm:hidden inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900" on:click={() => showSteps = !showSteps}>
              <Icon name="chevrons-right-left" size={14} /> Steps
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main content area with collapsible sidebar -->
    <div class="relative flex">
      <!-- Main content -->
      <div class="flex-1 transition-all duration-300" class:pr-80={sidebarOpen}>
        <!-- Slot renders the actual step content -->
        <div class="min-h-[40vh] p-0">
          {#if isLoading}
            <div class="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 animate-pulse h-40"></div>
          {:else}
            <slot />
          {/if}
        </div>
      </div>

      <!-- Collapsible Sidebar -->
   <div class="fixed right-0 top-0 h-full w-80 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-lg transform transition-transform duration-300 z-40" 
     class:translate-x-0={sidebarOpen} 
     class:translate-x-full={!sidebarOpen}>
        
        <!-- Sidebar Header -->
        <div class="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
          <h3 class="font-semibold text-slate-900 dark:text-slate-100">Pipeline Details</h3>
          <button 
            on:click={() => sidebarOpen = false}
            class="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Icon name="x" size={16} />
          </button>
        </div>

        <!-- Sidebar Content -->
        <div class="p-4 space-y-6 overflow-y-auto h-full pb-20">
          <!-- Current Step Info -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300">Current Step</h4>
            <div class="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                {#if currentStep === 'jd'}<Icon name="tag" size={16} />{/if}
                {#if currentStep === 'draft'}<Icon name="sparkles" size={16} />{/if}
                {#if currentStep === 'ats'}<Icon name="shield-check" size={16} />{/if}
                {#if currentStep === 'export'}<Icon name="layers" size={16} />{/if}
                <span class="font-medium text-slate-900 dark:text-slate-100">{titles[currentStep]}</span>
              </div>
              {#if descs[currentStep]}
                <p class="text-sm text-slate-600 dark:text-slate-400">{descs[currentStep]}</p>
              {/if}
            </div>
          </div>

          <!-- Pipeline Info -->
          {#if pipe}
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300">Pipeline Info</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-800">
                <span class="text-slate-500 dark:text-slate-400">Name</span>
                <span class="font-medium text-slate-900 dark:text-slate-100 truncate max-w-40" title={pipe.name}>{pipe.name}</span>
              </div>
              {#if pipe.company}
              <div class="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-800">
                <span class="text-slate-500 dark:text-slate-400">Company</span>
                <span class="font-medium text-slate-900 dark:text-slate-100 truncate max-w-40" title={pipe.company}>{pipe.company}</span>
              </div>
              {/if}
              <div class="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-800">
                <span class="text-slate-500 dark:text-slate-400">ID</span>
                <span class="font-mono text-xs text-slate-700 dark:text-slate-300">{pipe.id}</span>
              </div>
              {#if pipe.jdId}
              <div class="flex justify-between items-center py-2">
                <span class="text-slate-500 dark:text-slate-400">JD</span>
                <a class="text-blue-600 hover:underline text-xs" href={`/app/pipeline-v2/${pipe.id}/jd`}>View JD</a>
              </div>
              {/if}
            </div>
          </div>
          {/if}

          <!-- All Steps Progress -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300">All Steps</h4>
            <div class="space-y-2">
              {#each v2StepOrder as step, i}
                {@const stepStatus = pipe?.statuses?.[step] || 'pending'}
                {@const isCurrentStep = currentStep === step}
                <a 
                  href={`/app/pipeline-v2/${pipe?.id}/${step}`}
                  class={`flex items-center gap-3 p-2 rounded-lg border transition
                    ${isCurrentStep 
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' 
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50'}`}
                >
                  <span class={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium
                    ${stepStatus === 'complete' ? 'bg-emerald-600 text-white' : 
                      stepStatus === 'active' || currentStep === step ? 'bg-blue-600 text-white' : 
                      'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'}`}>
                    {i + 1}
                  </span>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm capitalize text-slate-900 dark:text-slate-100">{step}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 capitalize">{stepStatus}</div>
                  </div>
                  {#if stepStatus === 'complete'}
                    <Icon name="check" size={14} class="text-emerald-600" />
                  {:else if stepStatus === 'active' || currentStep === step}
                    <Icon name="arrow-right" size={14} class="text-blue-600" />
                  {/if}
                </a>
              {/each}
            </div>
          </div>

          <!-- Quick Tips -->
          <div class="space-y-3">
            <h4 class="text-sm font-medium text-slate-700 dark:text-slate-300">Tips</h4>
            <ul class="text-xs text-slate-600 dark:text-slate-400 space-y-2">
              <li class="flex items-start gap-2">
                <Icon name="info" size={12} class="mt-0.5 text-blue-500" />
                <span>Click any step above to navigate directly</span>
              </li>
              <li class="flex items-start gap-2">
                <Icon name="sparkles" size={12} class="mt-0.5 text-yellow-500" />
                <span>Save your progress frequently</span>
              </li>
              <li class="flex items-start gap-2">
                <Icon name="check" size={12} class="mt-0.5 text-emerald-500" />
                <span>Complete steps in order for best results</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Sidebar Toggle Button -->
      <button
        on:click={() => sidebarOpen = !sidebarOpen}
        class="fixed right-4 top-1/2 transform -translate-y-1/2 z-50 border-none bg-transparent p-0 m-0 shadow-none hover:shadow-none transition-all duration-200"
        class:right-84={sidebarOpen}
        title={sidebarOpen ? 'Hide details' : 'Show details'}
      >
        <Icon name={sidebarOpen ? 'arrow-right' : 'arrow-left'} size={22} />
      </button>

      <!-- Overlay for mobile -->
      {#if sidebarOpen}
        <div 
          class="fixed inset-0 bg-black/20 z-30 lg:hidden" 
          on:click={() => sidebarOpen = false}
        ></div>
      {/if}
    </div>
  </div>
{/if}
