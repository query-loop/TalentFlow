<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import { extractMeta, formatJD } from '$lib/jd';
  import { onMount } from 'svelte';

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

  let items: JDItem[] = [];
  let importUrl = '';
  let importing = false;
  let importOpen = false;
  let importPanelEl: HTMLDivElement;
  let importBtnEl: HTMLButtonElement;
  let confirmDeleteId: string | null = null;
  let modalBackdropEl: HTMLDivElement;

  function load() {
    try { items = JSON.parse(localStorage.getItem('tf_jd_items') || '[]'); } catch { items = []; }
  }
  function save() { localStorage.setItem('tf_jd_items', JSON.stringify(items)); }

  onMount(load);

  function openItem(id: string) { location.href = `/app/extract/${id}`; }
  function hostOf(url?: string) { try { return url ? new URL(url).host : ''; } catch { return ''; } }

  function removeItem(id: string) {
    items = items.filter(i => i.id !== id);
    save();
  }

  async function importFromUrl() {
    const url = importUrl.trim();
    if (!url) return;
  importOpen = false;
    importing = true;
    try {
      const res = await fetch('/api/fetch', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ url }) });
      if (!res.ok) throw new Error(`Fetch failed ${res.status}`);
      const { html } = await res.json();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      // Prefer JSON-LD JobPosting
      let jdText = '';
      const scripts = Array.from(doc.querySelectorAll('script[type="application/ld+json"]'));
      for (const s of scripts) {
        try {
          const data = JSON.parse(s.textContent || '{}');
          const arr = Array.isArray(data) ? data : [data];
          for (const d of arr) {
            if (d['@type'] === 'JobPosting') {
              const desc = d.description || d.responsibilities || d.qualifications || '';
              if (typeof desc === 'string') jdText = desc;
            }
          }
        } catch {}
      }
      if (!jdText) {
        const rich = doc.querySelector('.content, .posting, .posting-page, .section, article');
        jdText = rich?.textContent || doc.body.textContent || '';
      }
      jdText = jdText.replace(/<[^>]+>/g, '').replace(/\u00a0/g, ' ');
      jdText = formatJD(jdText);
      const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
      const meta = extractMeta(jdText);
      const item: JDItem = { id, company: meta.company, role: meta.title, location: meta.location, source: url, jd: jdText, createdAt: Date.now(), updatedAt: Date.now() };
      items = [item, ...items];
      save();
      // Navigate to detail page for this JD
      openItem(id);
    } catch (e) { console.error(e); }
    finally { importing = false; }
  }

  function addJD() {
    const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
    const now = Date.now();
    const item: JDItem = { id, jd: '', createdAt: now, updatedAt: now } as JDItem;
    items = [item, ...items];
    save();
    openItem(id);
  }
</script>

<svelte:window
  on:keydown={(e: KeyboardEvent) => { if (e.key === 'Escape' && importOpen) { importOpen = false; } }}
  on:click={(e: MouseEvent) => {
  const t = e.target as Node;
  if (!importOpen) return;
  // Close when clicking outside modal panel
  if (importPanelEl && importPanelEl.contains(t)) return;
  if (importBtnEl && importBtnEl.contains(t)) return;
  if (modalBackdropEl && modalBackdropEl.contains(t)) {
    // Only close if clicking the backdrop itself, not inside panel
    const target = e.target as HTMLElement;
    if (target === modalBackdropEl) {
      importOpen = false;
    }
    return;
  }
  importOpen = false;
}}
/>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="tag"/> Extract JD</h1>
    <span></span>
  </div>

  <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={addJD}><Icon name="plus"/> <span>New JD</span></button>
        <button bind:this={importBtnEl} class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => { importOpen = true; setTimeout(() => { try { (document.getElementById('import-url-input') as HTMLInputElement)?.focus(); } catch {} }, 0); }}>
          <Icon name="download"/> <span>Import JD</span>
        </button>
      </div>
      <div />
    </div>
  </div>

  {#if importOpen}
    <div bind:this={modalBackdropEl} class="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div bind:this={importPanelEl} class="w-[520px] max-w-[95vw] rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl">
        <div class="p-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="font-medium text-sm flex items-center gap-2"><Icon name="download"/> Import Job Description</div>
          <button class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={() => (importOpen = false)}>Close</button>
        </div>
        <div class="p-3 space-y-2">
          <label for="import-url-input" class="text-xs text-gray-600 dark:text-gray-300">Paste a job posting URL (Lever, Greenhouse, Workday, etc.)</label>
          <div class="flex items-center gap-2">
            <div class="relative flex-1">
              <span class="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">
                <Icon name="search" size={16} />
              </span>
              <input id="import-url-input" class="w-full text-sm border rounded pl-8 pr-3 py-2 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700" placeholder="https://jobs.company.com/..." bind:value={importUrl} on:keydown={(e) => { if (e.key === 'Enter') importFromUrl(); }} />
            </div>
            <button class="text-sm px-3 py-2 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 whitespace-nowrap" on:click={importFromUrl} disabled={!importUrl.trim() || importing}>{importing ? 'Importing…' : 'Import'}</button>
          </div>
          <div class="pt-1 text-[11px] space-y-1.5 text-gray-500 dark:text-gray-400">
            <div><span class="font-medium text-gray-600 dark:text-gray-300">Related:</span> Lever, Greenhouse, Workday, Ashby, Teamtailor, SmartRecruiters</div>
            <div><span class="font-medium text-gray-600 dark:text-gray-300">Warning:</span> Only import publicly accessible job posts; private or intranet links aren’t supported.</div>
            <div><span class="font-medium text-gray-600 dark:text-gray-300">Description:</span> Paste a job URL and we’ll extract the description to create a JD card automatically.</div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if items.length}
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 items-stretch">
      {#each items as it (it.id)}
        <article class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 p-3 flex flex-col h-full min-h-[220px] cursor-pointer hover:bg-gray-50/50 dark:hover:bg-slate-700/30" on:click={() => openItem(it.id)}>
          <div class="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between">
            <span class="truncate pr-2" title={it.company || '—'}>{it.company || '—'}</span>
            <span class="text-[11px] text-gray-400 dark:text-gray-500">{hostOf(it.source) || '—'}</span>
          </div>
          <div class="mt-1 min-h-[36px]">
            <div class="font-medium truncate" title={it.role || 'Untitled'}>{it.role || 'Untitled'}</div>
            <div class="text-xs text-gray-600 dark:text-gray-300 truncate">{it.location || ''}</div>
          </div>
          <p class="mt-2 text-xs text-gray-700 dark:text-gray-200 clamp-3 flex-1">{(it.jd || '').slice(0, 800)}</p>
          <div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
            {#if confirmDeleteId === it.id}
              <div class="border rounded bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700 p-2 flex items-center justify-between" on:click|stopPropagation>
                <span class="text-red-700 dark:text-red-300">Delete this JD?</span>
                <div class="flex items-center gap-2">
                  <button class="px-2 py-1 rounded border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/30" on:click|stopPropagation={() => { removeItem(it.id); confirmDeleteId = null; }}>Confirm</button>
                  <button class="px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700" on:click|stopPropagation={() => { confirmDeleteId = null; }}>Cancel</button>
                </div>
              </div>
            {:else}
              <div class="flex items-center justify-between gap-2">
                <span class="truncate">Updated {new Date(it.updatedAt).toLocaleDateString()}</span>
                <div class="flex items-center gap-2 shrink-0">
                  {#if (it as any).reference || (it as any).extracted}
                    <button class="px-2 py-1 rounded border border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20" title="Keep this reference" on:click|stopPropagation={() => {
                      try {
                        const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]');
                        const cur = arr.find((x: any) => x.id === it.id);
                        if (cur?.extracted) localStorage.setItem('tf_extracted_jd', JSON.stringify(cur.extracted));
                        const refText = cur?.reference || '';
                        localStorage.setItem('tf_generate_use_reference', String(!!refText));
                        if (refText) localStorage.setItem('tf_generate_reference_text', refText);
                      } catch {}
                    }}>Keep reference</button>
                  {/if}
                  <button class="px-2 py-1 rounded border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20"
                          aria-label="Delete JD"
                          on:click|stopPropagation={() => { confirmDeleteId = it.id; }}>Delete</button>
                </div>
              </div>
            {/if}
          </div>
        </article>
      {/each}
    </div>
  {:else}
    <div class="text-sm text-gray-600 dark:text-gray-400">No JDs yet. Create a new one or import from a URL.</div>
  {/if}
</section>

<style>
  .clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
