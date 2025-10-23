<script lang="ts">

  import Icon from '$lib/Icon.svelte';  import Icon from '$lib/Icon.svelte';

  import JDDisplay from '$lib/components/JDDisplay.svelte';  import JDDisplay from '$lib/components/JDDisplay.svelte';

  import { page } from '$app/stores';  import { page } from '$app/stores';

  import { onMount } from 'svelte';  import { onMount } from 'svelte';



  type JDItem = {  type JDItem = {

    id: string;    id: string;

    company?: string;    company?: string;

    role?: string;    role?: string;

    location?: string;    location?: string;

    source?: string;    source?: string;

    jd: string;    jd: string;

    createdAt: number;    createdAt: number;

    updatedAt: number;    updatedAt: number;

  };  };



  let id = '';  let id = '';

  let item: JDItem | null = null;  let item: JDItem | null = null;



  function load() {  function load() {

    try { id = $page.params.id as string; } catch {}    try { id = $page.params.id as string; } catch {}

    try {    try {

      const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];      const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];

      item = arr.find(i => i.id === id) || null;      item = arr.find(i => i.id === id) || null;

    } catch {}    } catch {}

  }  }



  onMount(load);  onMount(load);

</script>



<div class="p-3 md:p-6">

  <script lang="ts">
    import Icon from '$lib/Icon.svelte';
    import JDDisplay from '$lib/components/JDDisplay.svelte';
    import { page } from '$app/stores';
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

    let id = '';
    let item: JDItem | null = null;

    function load() {
      try { id = $page.params.id as string; } catch {}
      try {
        const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];
        item = arr.find(i => i.id === id) || null;
      } catch { item = null; }
    }

    onMount(load);
  </script>

  <div class="p-3 md:p-6">
    <section class="space-y-4">
      <nav aria-label="Breadcrumb" class="flex items-center justify-between">
        <ol class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <li><a href="/app" class="hover:text-gray-900 dark:hover:text-gray-200">Home</a></li>
          <li aria-hidden="true" class="text-gray-300">/</li>
          <li><a href="/app/extract" class="hover:text-gray-900 dark:hover:text-gray-200">Extract</a></li>
          <li aria-hidden="true" class="text-gray-300">/</li>
          <li class="text-gray-700 dark:text-gray-200 font-medium truncate max-w-[60vw]">{item?.role || 'Job Details'}</li>
        </ol>
      </nav>

      {#if item}
        <div class="border rounded-lg p-4 bg-white dark:bg-slate-800">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold">{item.role}</h2>
              {#if item.company}
                <div class="text-sm text-slate-500">{item.company} {#if item.location}· {item.location}{/if}</div>
              {/if}
            </div>
            <div class="text-xs text-slate-500 font-mono">{new Date(item.updatedAt).toLocaleString()}</div>
          </div>
          <div class="mt-4">
            <JDDisplay jdData={{ title: item.role, company: item.company, description: item.jd }} showHeader={false} />
          </div>
        </div>
      {:else}
        <div class="text-center py-12 text-gray-600 dark:text-gray-400">
          <Icon name="search" class="w-10 h-10 mx-auto text-gray-400 mb-3" />
          <h2 class="text-xl font-semibold">Job Description Not Found</h2>
          <p class="mt-1">The requested item could not be found. It might have been deleted.</p>
          <a href="/app/extract" class="mt-4 inline-block text-sm px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all">Go back to Imports</a>
        </div>
      {/if}
    </section>
  </div>
            onMount(load);
