<script lang="ts">
  import { onMount } from 'svelte';
  import { getExtractionStats, debugTestExtraction } from '$lib/pipelinesV2';
  import Icon from '$lib/Icon.svelte';

  let stats: any = null;
  let error: string | null = null;
  let loading = true;
  let fromDate: string | null = null;
  let toDate: string | null = null;

  // Debug test vars
  let testUrl = '';
  let debugResult: any = null;
  let debugLoading = false;

  async function loadStats() {
    try {
      loading = true;
      error = null;
      stats = await getExtractionStats();
    } catch (e: any) {
      error = e.message || 'Failed to load stats';
    } finally {
      loading = false;
    }
  }

  onMount(loadStats);

  function exportCsv() {
    // Basic CSV export of top_pipelines if present
    const rows: string[] = [];
    rows.push(['id','name','company','quality_score','runs'].join(','));
    const list = stats?.top_pipelines || [];
    for (const p of list) {
      rows.push([p.id, `"${(p.name||'').replace(/\"/g,'\"')}"`, `"${(p.company||'').replace(/\"/g,'\"')}"`, p.quality_score, p.runs].join(','));
    }
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `pipeline_v2_stats_${Date.now()}.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  async function runDebugTest() {
    if (!testUrl?.trim()) return;

    try {
      debugLoading = true;
      debugResult = await debugTestExtraction(testUrl);
    } catch (e: any) {
      debugResult = { error: e.message || 'Test failed' };
    } finally {
      debugLoading = false;
    }
  }

</script>

<div class="p-6">
  <div class="flex items-center justify-between mb-6 gap-4">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Pipeline V2 Statistics</h1>
      <div class="text-sm text-slate-500 mt-1">Overview of extraction, pipeline performance and IP rotation health.</div>
    </div>
    <div class="flex items-center gap-2">
      <input type="date" bind:value={fromDate} class="px-3 py-1 border rounded bg-white dark:bg-slate-800 text-sm" />
      <input type="date" bind:value={toDate} class="px-3 py-1 border rounded bg-white dark:bg-slate-800 text-sm" />
      <button class="px-3 py-1 border rounded text-sm" on:click={loadStats} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
      <button class="px-3 py-1 bg-slate-50 dark:bg-slate-700 border rounded text-sm" on:click={exportCsv}>Export CSV</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center gap-2 text-slate-600 dark:text-slate-400">
      <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
      </svg>
      <span>Loading statistics...</span>
    </div>
  {:else if error}
    <div class="border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 rounded-lg p-4">
      <div class="flex items-center gap-2 text-red-800 dark:text-red-200">
        <Icon name="alert-circle" size={16} />
        <span class="font-medium">Error loading statistics</span>
      </div>
      <p class="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
    </div>
  {:else if stats}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Anti-Bot Summary -->
      <div class="border rounded-lg p-6 bg-white dark:bg-slate-800 shadow-sm">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <Icon name="shield" size={20} />
          Anti-Bot Performance
        </h2>
        <div class="space-y-3">
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Total Attempts</span>
            <span class="font-medium">{stats.anti_bot_summary?.total_attempts || 0}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Success Rate</span>
            <span class="font-medium text-green-600">{((stats.anti_bot_summary?.success_rate || 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Block Rate</span>
            <span class="font-medium text-red-600">{((stats.anti_bot_summary?.block_rate || 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Browser Automation Used</span>
            <span class="font-medium">{stats.anti_bot_summary?.browser_automation_usage || 0}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Fallback Used</span>
            <span class="font-medium">{stats.anti_bot_summary?.fallback_usage || 0}</span>
          </div>
        </div>
      </div>

      <!-- Pipeline Performance -->
      <div class="border rounded-lg p-6 bg-white dark:bg-slate-800 shadow-sm">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <Icon name="bar-chart" size={20} />
          Pipeline Performance
        </h2>
        <div class="space-y-3">
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Pipelines Analyzed</span>
            <span class="font-medium">{stats.pipeline_performance?.total_pipelines_analyzed || 0}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Success Rate</span>
            <span class="font-medium text-green-600">{((stats.pipeline_performance?.pipeline_success_rate || 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Avg Quality Score</span>
            <span class="font-medium">{((stats.pipeline_performance?.average_quality_score || 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Blocked Pipelines</span>
            <span class="font-medium text-red-600">{stats.pipeline_performance?.blocked_pipelines || 0}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600 dark:text-slate-400">Failed Pipelines</span>
            <span class="font-medium text-red-600">{stats.pipeline_performance?.failed_pipelines || 0}</span>
          </div>
        </div>
      </div>

      <!-- Extraction Methods -->
      <div class="border rounded-lg p-6 bg-white dark:bg-slate-800 shadow-sm">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <Icon name="settings" size={20} />
          Extraction Methods Used
        </h2>
        <div class="space-y-2">
          {#each Object.entries(stats.pipeline_performance?.extraction_methods || {}) as [method, count]}
            <div class="flex justify-between">
              <span class="text-sm text-slate-600 dark:text-slate-400 capitalize">{method.replace('_', ' ')}</span>
              <span class="font-medium">{count}</span>
            </div>
          {/each}
          {#if Object.keys(stats.pipeline_performance?.extraction_methods || {}).length === 0}
            <div class="text-sm text-slate-500 dark:text-slate-400">No extraction methods recorded yet</div>
          {/if}
        </div>
      </div>

      <!-- IP Rotation Stats -->
      <div class="border rounded-lg p-6 bg-white dark:bg-slate-800 shadow-sm">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <Icon name="globe" size={20} />
          IP Rotation Performance
        </h2>
        <div class="space-y-3">
          {#if stats.ip_rotation}
            <div class="text-sm text-slate-600 dark:text-slate-400">
              IP rotation statistics and performance metrics will be displayed here.
            </div>
          {:else}
            <div class="text-sm text-slate-500 dark:text-slate-400">IP rotation stats not available</div>
          {/if}
        </div>
      </div>

      <!-- Top Pipelines -->
      <div class="border rounded-lg p-6 bg-white dark:bg-slate-800 shadow-sm lg:col-span-2">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <Icon name="star" size={20} />
          Top Pipelines
        </h2>
        <div class="space-y-2">
          {#if stats.top_pipelines && stats.top_pipelines.length}
            {#each stats.top_pipelines as p}
              <div class="flex items-center justify-between">
                <div class="min-w-0">
                  <div class="font-medium truncate">{p.name}</div>
                  <div class="text-xs text-slate-500">{p.company} · {p.id}</div>
                </div>
                <div class="text-right">
                  <div class="font-medium">{(p.quality_score*100).toFixed(0)}%</div>
                  <div class="text-xs text-slate-500">{p.runs} runs</div>
                </div>
              </div>
            {/each}
          {:else}
            <div class="text-sm text-slate-500">No pipeline rankings available yet</div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Debug Section -->
    <div class="mt-8 border rounded-lg p-6 bg-white dark:bg-slate-800">
      <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
        <Icon name="bug" size={20} />
        Debug Extraction Test
      </h2>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Test URL</label>
          <input
            type="url"
            placeholder="https://example.com/job/123"
            class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
            bind:value={testUrl}
          />
        </div>
        <button
          class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
          on:click={runDebugTest}
          disabled={debugLoading || !testUrl?.trim()}
        >
          {debugLoading ? 'Testing...' : 'Test Extraction'}
        </button>

        {#if debugResult}
          <div class="border rounded p-4 bg-slate-50 dark:bg-slate-700">
            <h3 class="font-medium mb-2">Test Results</h3>
            <pre class="text-xs overflow-x-auto">{JSON.stringify(debugResult, null, 2)}</pre>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>