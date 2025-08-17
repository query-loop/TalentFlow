<script lang="ts">
  // Use same-origin API routes that proxy to the backend
  const API = '';
  let ping = '';
  let resume = '';
  let endpoints: Array<{ method: string; path: string; description: string }>= [];
  let errorPing = '';
  let errorResume = '';
  let errorEndpoints = '';

  // Lazy-load Carbon Web Components (esm)
  import { onMount } from 'svelte';
  onMount(async () => {
    try {
      await import('@carbon/web-components/es/components/button/index.js');
      await import('@carbon/web-components/es/components/tile/index.js');
      await import('@carbon/web-components/es/components/inline-loading/index.js');
      await import('@carbon/web-components/es/components/notification/index.js');
    } catch (e) {
      console.warn('Carbon components failed to load', e);
    }
  });

  async function testPing() {
    errorPing = '';
    ping = 'your resume has been curating...';
    try {
  const res = await fetch(`/api/ping`, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      ping = await res.text();
    } catch (e: any) {
      ping = 'no response';
      errorPing = e?.message ?? String(e);
    }
  }

  async function fetchResume() {
    errorResume = '';
    resume = 'loading...';
    try {
  const res = await fetch(`/api/resume`, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      resume = await res.text();
    } catch (e: any) {
      resume = 'no response';
      errorResume = e?.message ?? String(e);
    }
  }

  async function loadEndpoints() {
    errorEndpoints = '';
    try {
  const res = await fetch(`/api/endpoints`, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      endpoints = await res.json();
    } catch (e: any) {
      endpoints = [];
      errorEndpoints = e?.message ?? String(e);
    }
  }
</script>

<div class="min-h-screen flex flex-col">
  <header class="border-b bg-white">
    <div class="mx-auto max-w-5xl p-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold">TalentFlow</h1>
      <nav class="text-sm text-gray-600">SvelteKit + Tailwind + Ktor</nav>
    </div>
  </header>

  <main class="flex-1 mx-auto max-w-5xl p-6 space-y-6">
    <p class="text-sm text-gray-500">Using same-origin API routes: /api/ping, /api/resume, /api/endpoints</p>

    <!-- Carbon Design System demo block -->
    <section class="space-y-3">
      <bx-inline-notification title="Carbon loaded" subtitle="Demo components below" kind="success" low-contrast></bx-inline-notification>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <bx-tile>
          <div class="flex items-center gap-3">
            <bx-btn kind="primary" on:click={testPing}>Carbon Ping</bx-btn>
            <bx-btn kind="secondary" on:click={fetchResume}>Carbon /resume</bx-btn>
          </div>
        </bx-tile>
        <bx-tile>
          <div class="flex items-center gap-3">
            <bx-inline-loading status={ping && ping !== 'no response' ? 'finished' : 'active'}></bx-inline-loading>
            <span class="text-gray-700">{ping || 'Tap Carbon Ping'}</span>
          </div>
        </bx-tile>
      </div>
    </section>
    <section class="space-y-2">
      <h2 class="text-lg font-medium">Welcome</h2>
      <p class="text-gray-700">
        This is a starter SvelteKit app styled with Tailwind. The button below calls the Ktor backend.
      </p>
    </section>

    <div class="space-x-2 items-center flex">
      <button class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700" on:click={testPing}>
        Ping backend
      </button>
      <span class="text-gray-600">{ping}</span>
      {#if errorPing}
        <span class="text-xs text-red-600">({errorPing})</span>
      {/if}
    </div>

    <div class="space-x-2 items-center flex">
      <button class="px-4 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700" on:click={fetchResume}>
        Get /resume
      </button>
      <span class="text-gray-600">{resume}</span>
      {#if errorResume}
        <span class="text-xs text-red-600">({errorResume})</span>
      {/if}
    </div>

    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <button class="px-3 py-1.5 rounded bg-gray-800 text-white hover:bg-black" on:click={loadEndpoints}>
          List endpoints
        </button>
        {#if endpoints.length}
          <span class="text-sm text-gray-500">{endpoints.length} endpoints</span>
        {/if}
      </div>
      {#if errorEndpoints}
        <div class="text-xs text-red-600">{errorEndpoints}</div>
      {/if}
      {#if endpoints.length}
        <ul class="text-sm divide-y border rounded">
          {#each endpoints as e}
            <li class="p-2 flex items-center gap-3">
              <span class="font-mono text-indigo-700">{e.method}</span>
              <span class="font-mono">{e.path}</span>
              <span class="text-gray-500">— {e.description}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </main>

  <footer class="border-t text-center text-sm text-gray-500 py-4">
    © {new Date().getFullYear()} TalentFlow
  </footer>
</div>
