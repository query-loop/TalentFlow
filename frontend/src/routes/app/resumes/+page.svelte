<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { onMount } from 'svelte';

  type SavedResume = { id: string; name: string; when: number; job?: string; result: { summary?: string; skills?: string[]; experience?: string[] } };
  let resumes: SavedResume[] = [];
  let loading = true;
  let q = '';

  onMount(() => {
    try { resumes = JSON.parse(localStorage.getItem('tf_recent_resumes') || '[]') as SavedResume[]; } catch {}
    loading = false;
  });

  function persist() {
    try { localStorage.setItem('tf_recent_resumes', JSON.stringify(resumes)); } catch {}
  }

  function openInGenerator(r: SavedResume) {
    try { localStorage.setItem('tf_selected_resume', JSON.stringify(r)); } catch {}
    location.href = '/app/generate';
  }

  function rename(r: SavedResume) {
    const name = prompt('Rename resume', r.name || '');
    if (name === null) return;
    r.name = name.trim() || r.name;
    resumes = [...resumes];
    persist();
  }

  function removeOne(id: string) {
    resumes = resumes.filter(r => r.id !== id);
    persist();
  }

  function clearAll() {
    if (!resumes.length) return;
    if (!confirm('Clear all recent resumes?')) return;
    resumes = [];
    persist();
  }

  $: filtered = (resumes || [])
    .filter(r => !q.trim() || r.name?.toLowerCase().includes(q.trim().toLowerCase()) || (r.job || '').toLowerCase().includes(q.trim().toLowerCase()))
    .sort((a,b) => b.when - a.when);
</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="folder"/> All resumes</h1>
    <div class="flex items-center gap-2">
      <input class="text-sm px-2 py-1 border rounded bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700" placeholder="Search by name or JD…" bind:value={q} />
      <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50" on:click={clearAll} disabled={!resumes.length}>Clear all</button>
    </div>
  </div>

  <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
    {#if loading}
      <div class="p-4 text-sm text-gray-600 dark:text-gray-400">Loading…</div>
    {:else if filtered.length}
      <ul class="divide-y divide-slate-200 dark:divide-slate-700">
        {#each filtered as r (r.id)}
          <li class="p-3 flex items-center gap-3">
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{r.name}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{new Date(r.when).toLocaleString()}</div>
            </div>
            <div class="flex items-center gap-2">
              <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => openInGenerator(r)}>View</button>
              <a href="/app/generate" class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700">Edit</a>
              <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => rename(r)}>Rename</button>
              <button class="text-xs px-2 py-1 rounded border border-red-200 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20" on:click={() => removeOne(r.id)}>Delete</button>
            </div>
          </li>
        {/each}
      </ul>
    {:else}
      <div class="p-4 text-sm text-gray-600 dark:text-gray-400">No resumes yet. Try the <a href="/app/generate" class="text-blue-600 hover:underline">generator</a>.</div>
    {/if}
  </div>
</section>
