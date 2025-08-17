<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  let text = '';
  let loading = false;
  let score: number | null = null;
  let tips: string[] = [];
  let err = '';

  async function run() {
    err = '';
    score = null;
    tips = [];
    loading = true;
    try {
      const res = await fetch('/api/mock/ats', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      score = data.score;
      tips = data.tips;
      if (score !== null) localStorage.setItem('tf_last_ats_score', String(score));
    } catch (e: any) { err = e?.message ?? String(e); }
    loading = false;
  }
</script>

<section class="space-y-4">
  <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="shield-check"/> ATS Score</h1>
  <p class="text-sm text-gray-600 dark:text-gray-300">Paste your resume or job description to check ATS compatibility.</p>
  <textarea class="border rounded p-2 min-h-[160px] w-full bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-100" bind:value={text} placeholder="Paste resume or JD..."></textarea>
  <div class="flex items-center gap-2">
    <button class="px-3 py-1.5 rounded bg-emerald-600 text-white disabled:opacity-50" disabled={loading || !text.trim()} on:click={run}>
      {loading ? 'Checking…' : 'Check ATS'}
    </button>
  </div>

  {#if err}
    <div class="text-sm text-red-700 dark:text-red-400">{err}</div>
  {/if}

  {#if score !== null}
    <div class="border rounded-lg bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 divide-y divide-slate-200 dark:divide-slate-700">
      <div class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">Result</div>
      <div class="p-4 space-y-3">
        <div class="text-2xl font-semibold">{score}%</div>
        <ul class="list-disc pl-5 text-sm text-gray-700 dark:text-gray-200">
          {#each tips as t}
            <li>{t}</li>
          {/each}
        </ul>
      </div>
    </div>
  {/if}
</section>
