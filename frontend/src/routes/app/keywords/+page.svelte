<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  let text = '';
  let jd = '';
  let err = '';
  let loading = false;
  let keywords: Array<{ term: string; count: number }> = [];

  async function run() {
    loading = true; err = ''; keywords = [];
    try {
      const res = await fetch('/api/mock/keywords', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text, jd }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      keywords = await res.json();
      localStorage.setItem('tf_last_keywords_count', String(keywords.length));
    } catch (e: any) { err = e?.message ?? String(e); }
    loading = false;
  }
</script>

<section class="space-y-4">
  <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="tag"/> Keyword Analysis</h1>
  <div class="grid md:grid-cols-2 gap-4">
    <div>
      <label class="text-sm text-gray-700 dark:text-gray-200">Resume</label>
      <textarea class="border rounded p-2 min-h-[140px] w-full bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-100" bind:value={text} placeholder="Paste your resume..."></textarea>
    </div>
    <div>
      <label class="text-sm text-gray-700 dark:text-gray-200">Job description</label>
      <textarea class="border rounded p-2 min-h-[140px] w-full bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-100" bind:value={jd} placeholder="Paste JD..."></textarea>
    </div>
  </div>
  <div>
    <button class="px-3 py-1.5 rounded bg-indigo-600 text-white disabled:opacity-50" disabled={loading || (!text.trim() && !jd.trim())} on:click={run}>
      {loading ? 'Analyzing…' : 'Analyze'}
    </button>
  </div>

  {#if err}
    <div class="text-sm text-red-700 dark:text-red-400">{err}</div>
  {/if}

  {#if keywords.length}
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      <div class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">Top Terms</div>
      <ul class="divide-y divide-slate-200 dark:divide-slate-700">
        {#each keywords as k}
          <li class="px-4 py-2 flex items-center gap-3">
            <span class="font-mono w-10 text-indigo-700 dark:text-indigo-400">{k.count}×</span>
            <span class="font-mono text-gray-800 dark:text-gray-100">{k.term}</span>
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</section>
