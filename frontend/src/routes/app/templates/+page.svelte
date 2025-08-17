<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import TemplatePreview from '$lib/TemplatePreview.svelte';
  import { templates, setActiveTemplate, getActiveTemplate } from '$lib/templates';
  let active = getActiveTemplate() || 'default';
  function useTemplate(id: string) {
    active = id;
    setActiveTemplate(id);
    location.href = '/app/generate';
  }
  function previewOnly(id: string) {
    active = id;
    setActiveTemplate(id);
  }
</script>

<section class="space-y-4">
  <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="layers"/> Templates</h1>
  <p class="text-sm text-gray-600">Pick a resume template. Using one takes you to the generator.</p>
  <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each templates as t (t.id)}
      <div class={`border rounded-lg p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 ${active === t.id ? 'ring-2 ring-indigo-500' : ''}`}>
        <TemplatePreview id={t.id} name={t.name} />
        <div class="mt-2">
          <div class="font-medium">{t.name}</div>
          <div class="text-sm text-gray-500">{t.description}</div>
        </div>
        <div class="mt-3 flex items-center gap-2">
          <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => previewOnly(t.id)}>{active === t.id ? 'Selected' : 'Preview'}</button>
          <button class="text-xs px-2 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700" on:click={() => useTemplate(t.id)}>Use template</button>
        </div>
      </div>
    {/each}
  </div>
</section>
