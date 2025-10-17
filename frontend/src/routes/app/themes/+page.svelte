<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';
  import { getPipeline, type Pipeline } from '$lib/pipelines';
  import { getActivePipelineId } from '$lib/pipelineTracker';
  let selected: 'default' | 'modern' | 'classic' | 'system' | 'other' = (localStorage.getItem('tf_theme') as any) || 'default';
  onMount(() => { localStorage.setItem('tf_theme', selected); });
  function save() { localStorage.setItem('tf_theme', selected); }

  // Active pipeline name for header
  let activePipeline: Pipeline | null = null;
  let pipelineHeaderName = '';
  onMount(async () => {
    try {
      const pid = getActivePipelineId();
      if (pid) {
        activePipeline = await getPipeline(pid);
        pipelineHeaderName = (activePipeline?.name || activePipeline?.company || '').trim();
      }
    } catch {}
  });
</script>

<section class="space-y-4">
  <h1 class="text-xl font-semibold flex items-center gap-2">
    <Icon name="palette"/> Themes
    {#if pipelineHeaderName}
      <span class="text-sm text-gray-500">— {pipelineHeaderName}</span>
    {/if}
  </h1>
  <p class="text-sm text-gray-600">Choose how generated resumes and the UI are styled.</p>
  <div class="grid md:grid-cols-3 gap-4">
    <label class="border rounded-lg p-4 flex gap-3 items-start bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <input type="radio" name="theme" value="default" bind:group={selected} on:change={save}>
      <div>
        <div class="font-medium">Default</div>
        <div class="text-sm text-gray-500">Clean, balanced layout for most roles.</div>
      </div>
    </label>
    <label class="border rounded-lg p-4 flex gap-3 items-start bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <input type="radio" name="theme" value="modern" bind:group={selected} on:change={save}>
      <div>
        <div class="font-medium">Modern</div>
        <div class="text-sm text-gray-500">Contemporary styling with accent headings.</div>
      </div>
    </label>
    <label class="border rounded-lg p-4 flex gap-3 items-start bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <input type="radio" name="theme" value="classic" bind:group={selected} on:change={save}>
      <div>
        <div class="font-medium">Classic</div>
        <div class="text-sm text-gray-500">Traditional serif-inspired layout.</div>
      </div>
    </label>
    <label class="border rounded-lg p-4 flex gap-3 items-start bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <input type="radio" name="theme" value="system" bind:group={selected} on:change={save}>
      <div>
        <div class="font-medium">System</div>
        <div class="text-sm text-gray-500">Follow OS setting (auto light/dark).</div>
      </div>
    </label>
    <!-- 'Dark' option removed to avoid explicit black/white theme selection -->
    <label class="border rounded-lg p-4 flex gap-3 items-start bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <input type="radio" name="theme" value="other" bind:group={selected} on:change={save}>
      <div>
        <div class="font-medium">Other</div>
        <div class="text-sm text-gray-500">Experimental accent background.</div>
      </div>
    </label>
  </div>
  <div class="text-sm text-gray-600">Selection persists and applies across pages.</div>
</section>
