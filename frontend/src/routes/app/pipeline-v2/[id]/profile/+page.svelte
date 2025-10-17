<script lang="ts">
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

  function highlightImportant(text: string, keys: string[] = []): string {
    if (!text) return '';
    // Basic highlight: emphasize key requirements if provided, otherwise emphasize bullet headings
    let html = text
      .replace(/\n\s*[-•]\s*/g, '\n• ')
      .replace(/(Responsibilities|Requirements|Qualifications|About the role|What You\'ll Do)/gi, '<mark class="bg-yellow-100 dark:bg-yellow-900/30 rounded px-1">$1</mark>');
    if (keys && keys.length) {
      const escaped = keys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).filter(Boolean);
      if (escaped.length) {
        const re = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi');
        html = html.replace(re, '<span class="bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded px-1">$1</span>');
      }
    }
    return html;
  }
</script>

{#if loading}
  <div class="p-6">
    <div class="animate-pulse space-y-4">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3"></div>
      <div class="h-40 bg-slate-200 dark:bg-slate-700 rounded"></div>
      <div class="h-40 bg-slate-200 dark:bg-slate-700 rounded"></div>
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
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Profile</h1>
        <div class="text-xs text-slate-600 dark:text-slate-400 mt-1">{pipe.name}{#if pipe.company} • {pipe.company}{/if}</div>
      </div>
      <div class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
        <Icon name="id-card" size={12} class="mr-1 inline" /> Overview
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Resume -->
      <div class="border rounded-lg bg-white dark:bg-slate-800">
        <div class="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Icon name="user" size={16} />
            <h2 class="text-sm font-semibold">Candidate Resume</h2>
          </div>
          {#if pipe.artifacts && (pipe.artifacts as any).resume?.filename}
            <div class="text-xs text-slate-500 dark:text-slate-400">{(pipe.artifacts as any).resume.filename}</div>
          {/if}
        </div>
        <div class="p-4">
          {#if pipe.artifacts && (pipe.artifacts as any).resume?.text}
            <div class="max-h-[28rem] overflow-auto rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3">
              <pre class="whitespace-pre-wrap font-mono text-xs text-slate-800 dark:text-slate-200">{(pipe.artifacts as any).resume.text}</pre>
            </div>
          {:else}
            <div class="text-xs text-slate-500 dark:text-slate-400">No resume parsed for this pipeline.</div>
          {/if}
        </div>
      </div>

      <!-- Job Description (important/highlightable) -->
      <div class="border rounded-lg bg-white dark:bg-slate-800">
        <div class="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Icon name="briefcase" size={16} />
            <h2 class="text-sm font-semibold">Job Description (Highlights)</h2>
          </div>
          {#if pipe.jdId}
            <a href={pipe.jdId} target="_blank" rel="noopener" class="text-xs text-blue-600 hover:underline flex items-center gap-1">
              View Posting <Icon name="arrow-up-right" size={12} />
            </a>
          {/if}
        </div>
        <div class="p-4 space-y-2">
          {#if pipe.artifacts && (pipe.artifacts as any).jd}
            {#if (pipe.artifacts as any).jd.title || pipe.name}
              <div class="text-sm font-medium text-slate-900 dark:text-slate-100">{(pipe.artifacts as any).jd.title || pipe.name}</div>
            {/if}
            {#if (pipe.artifacts as any).jd.company || pipe.company}
              <div class="text-xs text-slate-600 dark:text-slate-400">{(pipe.artifacts as any).jd.company || pipe.company}</div>
            {/if}

            {#if (pipe.artifacts as any).jd.key_requirements?.length}
              <div class="mt-3">
                <div class="text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">Key Requirements</div>
                <ul class="list-disc pl-5 space-y-1">
                  {#each (pipe.artifacts as any).jd.key_requirements.slice(0, 12) as req}
                    <li class="text-xs text-slate-700 dark:text-slate-300">{req}</li>
                  {/each}
                </ul>
              </div>
            {/if}

            {#if (pipe.artifacts as any).jd.description}
              <div class="mt-3 max-h-[20rem] overflow-auto rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3">
                {@html highlightImportant((pipe.artifacts as any).jd.description, (pipe.artifacts as any).jd.key_requirements || [])}
              </div>
            {/if}
          {:else}
            <div class="text-xs text-slate-500 dark:text-slate-400">No job description extracted yet.</div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Note: Analysis (gaps, differentiators, strengths) is intentionally not shown here. Use dedicated tabs. -->
  </div>
{/if}
