<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import JDDisplay from '$lib/components/JDDisplay.svelte';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { onDestroy } from 'svelte';

  type JobPosting = {
    title?: string;
    description?: string;
    jobLocationType?: string; // e.g., TELECOMMUTE
    jobLocation?: Array<{
      address?: {
        addressLocality?: string;
        addressRegion?: string;
        addressCountry?: string;
      }
    }>;
    hiringOrganization?: { name?: string };
  };

  type JDItem = {
    id: string;
    company?: string;
    role?: string;
    location?: string;
    source?: string;
    jd: string;
    createdAt: number;
    updatedAt: number;
  };

  let url = '';
  let loading = false;
  let error: string | null = null;
  let items: JDItem[] = [];
  let selectedId: string | null = null;
  let successMsg: string | null = null;
  let editId: string | null = null;
  let editForm: Partial<JDItem> = {};

  function loadItems() {
    try {
      items = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];
    } catch {
      items = [];
    }
    if (!selectedId && items.length > 0) selectedId = items[0].id;
  }

  function saveItems() {
    localStorage.setItem('tf_jd_items', JSON.stringify(items));
  }

  function idGen(): string {
    try { return crypto.randomUUID(); } catch { return `${Date.now()}-${Math.random().toString(36).slice(2,8)}`; }
  }

  function deriveLocation(job: JobPosting): string | undefined {
    if (job.jobLocationType === 'TELECOMMUTE') return 'Remote';
    const a = job.jobLocation?.[0]?.address;
    if (!a) return undefined;
    const parts = [a.addressLocality, a.addressRegion, a.addressCountry].filter(Boolean);
    return parts.join(', ') || undefined;
  }

  function companyFromUrl(u: string): string | undefined {
    try {
      const { hostname, pathname } = new URL(u);
      const host = hostname.toLowerCase();
      const pathParts = pathname.split('/').filter(Boolean);

      const nicify = (s: string) => s.replace(/[-_]+/g, ' ').replace(/[^a-z0-9 ]/gi, ' ').trim().replace(/\s+/g, ' ');
      const title = (s: string) => nicify(s).split(' ').map(w => w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : '').join(' ').trim();

      if (host.endsWith('lever.co') && pathParts[0]) return title(pathParts[0]);
      if (host.endsWith('greenhouse.io') && pathParts[0]) return title(pathParts[0]);

      const sldCandidates = new Set(['www','jobs','careers','boards']);
      const first = host.split('.')[0];
      let name = first && !sldCandidates.has(first) ? first : host.split('.').slice(-2, -1)[0];
      const clean = nicify(name);
      return clean ? title(clean) : undefined;
    } catch { return undefined; }
  }

  function domainOf(u?: string): string | null {
    if (!u) return null;
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return null; }
  }

  function snippet(s: string, n = 280): string {
    const t = (s || '').trim();
    if (t.length <= n) return t;
    return t.slice(0, n - 1).trimEnd() + '…';
  }

  async function onSubmit() {
    error = null;
    const u = url.trim();
    if (!u) { error = 'Please paste a job URL.'; return; }
    loading = true;
    try {
      const res = await api<{ success: boolean; data?: JobPosting; message?: string }>(
        '/api/extract/ai',
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: u }) }
      );
      if (!res?.success || !res?.data) {
        throw new Error(res?.message || 'Extraction failed');
      }
      const job = res.data;
      const item: JDItem = {
        id: idGen(),
        role: job.title || 'Untitled Role',
        company: job.hiringOrganization?.name || companyFromUrl(u) || undefined,
        location: deriveLocation(job),
        source: u,
        jd: job.description || '',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      items = [item, ...items].slice(0, 200);
      saveItems();
      selectedId = item.id;
      successMsg = 'Extracted successfully — opening details…';
      // Navigate to details
      goto(`/app/extract/${item.id}`);
    } catch (e: any) {
      error = e?.message || 'Failed to extract job posting.';
    } finally {
      loading = false;
      setTimeout(() => (successMsg = null), 2500);
    }
  }

  function removeItem(id: string) {
    items = items.filter(i => i.id !== id);
    saveItems();
    if (selectedId === id) selectedId = items[0]?.id || null;
  }

  function startEdit(it: JDItem) {
    editId = it.id;
    editForm = { role: it.role, company: it.company, location: it.location, source: it.source };
  }
  function cancelEdit() { editId = null; editForm = {}; }
  function saveEdit(id: string) {
    items = items.map(it => it.id === id ? { ...it, ...editForm, updatedAt: Date.now() } : it);
    saveItems();
    editId = null; editForm = {};
  }

  onMount(loadItems);
</script>

<div class="p-3 md:p-6">
  <section class="grid grid-cols-12 gap-5 items-start">
    <!-- Left: form + saved imports -->
    <div class="col-span-12 lg:col-span-5 space-y-5">
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 p-5">
        <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-black dark:text-white">Extract Job Description</h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Paste a job posting URL. We’ll fetch it and format the description professionally.</p>

        <div class="mt-4">
          <label for="job-url" class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Job URL</label>
          <input
            class="w-full text-base px-3.5 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            type="url"
            placeholder="https://jobs.lever.co/company/role..."
            id="job-url"
            bind:value={url}
            on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onSubmit(); } }}
          />
          {#if error}
            <div class="mt-2 text-sm text-red-600">{error}</div>
          {/if}
          {#if successMsg}
            <div class="mt-2 text-sm text-green-700">{successMsg}</div>
          {/if}
          <div class="mt-3 flex items-center gap-2">
            <button class="inline-flex items-center gap-2 text-sm px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50" on:click={onSubmit} disabled={loading}>
              {#if loading}
                <Icon name="spinner" class="w-4 h-4 animate-spin" /> Fetching & formatting…
              {:else}
                <Icon name="sparkles" class="w-4 h-4" /> Extract
              {/if}
            </button>
            <a class="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white" href="/app/extract">Reset</a>
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 p-5">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-black dark:text-white">Saved Imports</h2>
          <div class="text-sm text-gray-500">{items.length} total</div>
        </div>
        {#if items.length === 0}
          <div class="mt-3 text-sm text-gray-600 dark:text-gray-300">No imports yet. Paste a URL above to get started.</div>
        {:else}
          <div class="mt-4 grid grid-cols-1 gap-3">
            {#each items as it}
              <div class={`border rounded-lg p-4 ${selectedId === it.id ? 'ring-2 ring-blue-500 border-blue-300' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800/70`}>
                {#if editId === it.id}
                  <div class="space-y-2">
                    <div class="grid grid-cols-2 gap-2">
                      <input class="border rounded px-2 py-1.5 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700" placeholder="Role" bind:value={editForm.role} />
                      <input class="border rounded px-2 py-1.5 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700" placeholder="Company" bind:value={editForm.company} />
                      <input class="border rounded px-2 py-1.5 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700" placeholder="Location" bind:value={editForm.location} />
                      <input class="border rounded px-2 py-1.5 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700" placeholder="Source URL" bind:value={editForm.source} />
                    </div>
                    <div class="flex items-center justify-end gap-2">
                      <button class="px-3 py-1.5 text-sm rounded border" on:click={cancelEdit}>Cancel</button>
                      <button class="px-3 py-1.5 text-sm rounded bg-blue-600 text-white" on:click={() => saveEdit(it.id)}>Save</button>
                    </div>
                  </div>
                {:else}
                  <div class="flex items-start gap-3">
                    <button class="flex-1 text-left" on:click={() => (selectedId = it.id)}>
                      <div class="text-base font-medium text-gray-900 dark:text-gray-100">{it.role || 'Job Details'}</div>
                      <div class="mt-0.5 text-sm text-gray-600 dark:text-gray-300 flex flex-wrap items-center gap-x-2 gap-y-1">
                        {#if it.company}<span class="inline-flex items-center gap-1"><Icon name="building" class="w-4 h-4" /> {it.company}</span>{/if}
                        {#if it.location}<span class="inline-flex items-center gap-1"><Icon name="map" class="w-4 h-4" /> {it.location}</span>{/if}
                        {#if it.source}<span class="inline-flex items-center gap-1 text-gray-500"><Icon name="external-link" class="w-4 h-4" /> {domainOf(it.source)}</span>{/if}
                      </div>
                      {#if it.jd}
                        <div class="mt-1 text-xs text-gray-500 line-clamp-2">{snippet(it.jd)}</div>
                      {/if}
                    </button>
                    <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      <a class="text-sm px-2.5 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700" href={`/app/extract/${it.id}`}>Open</a>
                      <button class="text-sm px-2.5 py-1.5 rounded border border-gray-300 dark:border-gray-600" on:click={() => startEdit(it)}>Edit</button>
                      <button class="text-sm px-2.5 py-1.5 rounded border border-red-300 text-red-700 hover:bg-red-50" on:click={() => removeItem(it.id)}>Delete</button>
                    </div>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Right: preview pane -->
    <aside class="col-span-12 lg:col-span-7">
      <div class="sticky top-4 space-y-4">
        {#if items.length > 0}
          {#key selectedId}
            {#if selectedId}
              {#each items as it}
                {#if it.id === selectedId}
                  <JDDisplay 
                    jdData={{
                      title: it.role,
                      company: it.company,
                      location: it.location,
                      source: it.source,
                      description: it.jd
                    }}
                    showHeader={true}
                  />
                {/if}
              {/each}
            {/if}
          {/key}
        {/if}
      </div>
    </aside>
  </section>
</div>
