<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '$lib/Icon.svelte';

  type Company = {
    name: string;
    domain?: string;
    logo?: string;
    matchScore: number;
    roles: string[];
    reason: string;
    openRoles?: number;
    metrics?: {
      relevance?: number;
      skills?: number;
      roleFit?: number;
      location?: number;
      culture?: number;
      salary?: number;
    };
  };

  let loading = true;
  let companies: Company[] = [];
  let err = '';
  let sort: 'score' | 'name' = 'score';

  onMount(async () => {
    try {
      const res = await fetch('/api/mock/companies');
      if (!res.ok) throw new Error('Failed to load companies');
      companies = await res.json();
      sortCompanies();
    } catch (e: any) { err = e?.message ?? String(e); }
    finally { loading = false; }
  });

  function sortCompanies() {
    companies = [...companies].sort((a, b) => sort === 'score' ? b.matchScore - a.matchScore : a.name.localeCompare(b.name));
  }
</script>

<section class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="folder"/> Companies you top at</h1>
    <div class="flex items-center gap-2 text-sm">
      <label class="text-gray-600">Sort</label>
      <select class="border rounded px-2 py-1" bind:value={sort} on:change={sortCompanies}>
        <option value="score">Match score</option>
        <option value="name">Name</option>
      </select>
    </div>
  </div>

  {#if loading}
    <div>Loading…</div>
  {:else if err}
    <div class="text-red-700">{err}</div>
  {:else}
    <ul class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each companies as c}
        <li class="border rounded-lg p-3 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2 min-w-0">
              {#if c.logo}
                <img src={c.logo} alt={c.name} class="w-6 h-6 rounded bg-white border border-slate-200 object-contain" />
              {/if}
              <div class="font-medium truncate">{c.name}</div>
            </div>
            <div class="text-sm"><span class="font-semibold">{c.matchScore}%</span> match</div>
          </div>
          <div class="text-xs text-gray-600 dark:text-gray-300 mt-1">{c.reason}</div>
          <div class="mt-2 flex flex-wrap gap-1">
            {#each c.roles as r}
              <span class="text-xs px-2 py-0.5 border rounded bg-gray-50 dark:bg-slate-700 dark:border-slate-600">{r}</span>
            {/each}
          </div>
          {#if c.metrics}
            <div class="mt-3 space-y-1">
              {#each Object.entries(c.metrics) as [k, v]}
                {#if v != null}
                <div class="flex items-center gap-2 text-xs">
                  <div class="w-24 capitalize text-gray-600 dark:text-gray-300">{k}</div>
                  <div class="flex-1 h-1.5 bg-gray-100 dark:bg-slate-700 rounded">
                    <div class="h-1.5 bg-indigo-600 rounded" style={`width:${v}%`}></div>
                  </div>
                  <div class="w-10 text-right text-gray-600 dark:text-gray-300">{v}%</div>
                </div>
                {/if}
              {/each}
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</section>
