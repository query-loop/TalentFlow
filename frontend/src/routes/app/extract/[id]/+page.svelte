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

  <section class="space-y-4">

    <!-- Top bar -->

    <nav aria-label="Breadcrumb" class="flex items-center justify-between">

      <ol class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">

        <li><a href="/app" class="hover:text-gray-900 dark:hover:text-gray-200">Home</a></li>    const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-').slice(0, 80);

        <li aria-hidden="true" class="text-gray-300">/</li>    const seen = new Set<string>();

        <li><a href="/app/extract" class="hover:text-gray-900 dark:hover:text-gray-200">Extract</a></li>    const uniqueId = (base: string) => {

        <li aria-hidden="true" class="text-gray-300">/</li>      let id = base;

        <li class="text-gray-700 dark:text-gray-200 font-medium truncate max-w-[60vw]">{item?.role || 'Job Details'}</li>      let i = 2;

      </ol>      while (seen.has(id)) { id = `${base}-${i++}`; }

      <div></div>      seen.add(id);

    </nav>      return id;

    };

    {#if item}

      <JDDisplay     const htmlParts: string[] = [];

        jdData={{    for (const block of blocks) {

          title: item.role,      const lines = block.split(/\n/).filter(Boolean);

          company: item.company,      const headingMatch = block.match(/^\s*(requirements?|responsibilities|benefits?|about|overview|qualification|skills|values)\s*:/i);

          location: item.location,      if (headingMatch) {

          source: item.source,        const heading = headingMatch[1];

          description: item.jd        const id = uniqueId(slug(heading));

        }}        const rest = block.replace(headingMatch[0], '').trim();

        showHeader={true}        htmlParts.push(`<h3 id="${id}" class="scroll-mt-24 text-base font-semibold mt-4">${escapeHtml(heading[0].toUpperCase() + heading.slice(1))}</h3>`);

      />        if (rest) {

    {:else}          const restLines = rest.split(/\n/);

      <div class="text-center py-12 text-gray-600 dark:text-gray-400">          if (restLines.every(isListLine)) htmlParts.push(linesToList(restLines));

        <Icon name="search" class="w-10 h-10 mx-auto text-gray-400 mb-3" />          else htmlParts.push(`<p class="mt-1">${autoLink(escapeHtml(rest))}</p>`);

        <h2 class="text-xl font-semibold">Job Description Not Found</h2>        }

        <p class="mt-1">The requested item could not be found. It might have been deleted.</p>        continue;

        <a href="/app/extract" class="mt-4 inline-block text-sm px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all">Go back to Imports</a>      }

      </div>

    {/if}      if (lines.length > 1 && lines.every(isListLine)) {

  </section>        htmlParts.push(linesToList(lines));

</div>      } else if (
        (lines.length === 1 && (looksLikeStandaloneTitle(lines[0]) || isKnownHeading(lines[0]))) ||
        (lines.length > 1 && (looksLikeStandaloneTitle(lines[0]) || isKnownHeading(lines[0])))
      ) {
        // First line as heading, rest as content
        const raw = lines[0].trim();
        const id = uniqueId(slug(raw));
        htmlParts.push(`<h3 id="${id}" class="scroll-mt-24 text-base font-semibold mt-4">${escapeHtml(raw)}</h3>`);
        const rest = lines.slice(1);
        if (rest.length) {
          if (rest.every(isListLine)) htmlParts.push(linesToList(rest));
          else htmlParts.push(`<p class="mt-1">${autoLink(escapeHtml(rest.join(' ')))}</p>`);
        }
      } else {
        htmlParts.push(`<p>${autoLink(escapeHtml(block))}</p>`);
      }
    }
    return htmlParts.join('\n');
  }

  onMount(load);

  // After mount, collect headings for navigator and enable search highlighting
  onMount(() => {
    
    collectHeadings();
    // small delay to allow {@html} render
    setTimeout(collectHeadings, 0);
  });

  function collectHeadings() {
    headings = [];
    const container = document.querySelector('#jd-container');
    if (!container) return;
    const hs = container.querySelectorAll('h3[id]');
    hs.forEach((h) => {
      const id = (h as HTMLElement).id;
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
          try {
            id = $page.params.id as string;
          } catch {}
          try {
            const arr = JSON.parse(localStorage.getItem('tf_jd_items') || '[]') as JDItem[];
            item = arr.find(i => i.id === id) || null;
          } catch { item = null; }
        }

        onMount(load);
      </script>

      <div class="p-3 md:p-6">
        <section class="space-y-4">
          <!-- Top bar -->
          <nav aria-label="Breadcrumb" class="flex items-center justify-between">
            <ol class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <li><a href="/app" class="hover:text-gray-900 dark:hover:text-gray-200">Home</a></li>
              <li aria-hidden="true" class="text-gray-300">/</li>
              <li><a href="/app/extract" class="hover:text-gray-900 dark:hover:text-gray-200">Extract</a></li>
              <li aria-hidden="true" class="text-gray-300">/</li>
              <li class="text-gray-700 dark:text-gray-200 font-medium truncate max-w-[60vw]">{item?.role || 'Job Details'}</li>
            </ol>
            <div></div>
          </nav>

          {#if item}
            <JDDisplay
              jdData={{
                title: item.role,
                company: item.company,
                location: item.location,
                source: item.source,
                description: item.jd
              }}
              showHeader={true}
            />
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
          location: item.location,
