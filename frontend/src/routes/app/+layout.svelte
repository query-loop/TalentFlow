<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from '$lib/Icon.svelte';

  let sidebarOpen = false;
  let media: MediaQueryList | null = null;
  // Support chat widget state
  type ChatMsg = { role: 'user' | 'assistant'; text: string };
  let chatOpen = false;
  let chatInput = '';
  let chatMessages: ChatMsg[] = [
    { role: 'assistant', text: 'Hi! Need help with resume curation, ATS, or pipelines? Ask me anything.' }
  ];

  // Mouse-follow spotlight background
  let spotlightX = 50; // percent
  let spotlightY = 50; // percent
  let reducedMotion = false;
  let rafId = 0;

  const workflows = [
  { href: '/app/extract', label: 'Extract', desc: 'Parse JDs per company/role', icon: 'tag' },
    { href: '/app/generate', label: 'Generate', desc: 'Create tailored resumes per job', icon: 'sparkles' },
    { href: '/app/ats', label: 'ATS Score', desc: 'Scan and get improvement tips', icon: 'shield-check' },
    { href: '/app/keywords', label: 'Keywords', desc: 'Analyze JD and resume terms', icon: 'tag' },
  { href: '/app/themes', label: 'Themes', desc: 'Choose formatting styles', icon: 'palette' },
  { href: '/app/pipelines', label: 'Pipelines', desc: 'All curation pipelines', icon: 'layers' }
  ] as const;

  const resources = [
  { href: '/app/companies', label: 'Companies', desc: 'Where you’re a strong match', icon: 'building' },
    { href: '/app/library', label: 'Library', desc: 'Saved resumes & drafts', icon: 'folder' },
    { href: '/app/templates', label: 'Templates', desc: 'Reusable layouts', icon: 'layers' },
    { href: '/app/history', label: 'History', desc: 'Recent actions', icon: 'clock' },
    { href: '/app/integrations', label: 'Integrations', desc: 'Connect ATS & boards', icon: 'plug' },
    { href: '/app/settings', label: 'Settings', desc: 'Preferences & defaults', icon: 'gear' },
    { href: '/app/help', label: 'Help', desc: 'Guides & FAQs', icon: 'info' }
  ] as const;

  onMount(() => {
    // No theme management; default light styles

    // Respect prefers-reduced-motion and set up spotlight tracker
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion = mq.matches;
    const onMq = (e: MediaQueryListEvent) => (reducedMotion = e.matches);
    mq.addEventListener?.('change', onMq);

    const onMove = (e: MouseEvent) => {
      if (reducedMotion) return;
      if (rafId) return;
      const { clientX, clientY } = e;
      rafId = requestAnimationFrame(() => {
        const w = window.innerWidth || 1;
        const h = window.innerHeight || 1;
        spotlightX = Math.max(0, Math.min(100, (clientX / w) * 100));
        spotlightY = Math.max(0, Math.min(100, (clientY / h) * 100));
        rafId = 0;
      });
    };
    window.addEventListener('mousemove', onMove, { passive: true });

    return () => {
      window.removeEventListener('mousemove', onMove);
      mq.removeEventListener?.('change', onMq);
      if (rafId) cancelAnimationFrame(rafId);
    };
  });

  function sendChat() {
    const text = chatInput.trim();
    if (!text) return;
    chatMessages = [...chatMessages, { role: 'user', text }];
    chatInput = '';
    // Mock assistant reply
    const reply = "Thanks for reaching out! Support chat is coming soon. For now, check Pipelines or the Help page.";
    setTimeout(() => {
      chatMessages = [...chatMessages, { role: 'assistant', text: reply }];
    }, 300);
  }
</script>

<div class="min-h-screen w-full bg-gray-50 relative overflow-hidden">
  <!-- Decorative background layers (non-interactive) -->
  <div class="pointer-events-none fixed inset-0 -z-10">
    <!-- Soft grid pattern -->
    <div class="absolute inset-0 opacity-[0.25] md:opacity-[0.18] dark:opacity-[0.12] [mask-image:radial-gradient(ellipse_at_center,white,transparent_70%)]" style="background-image: linear-gradient(to_right, rgba(148,163,184,0.18) 1px, transparent 1px), linear-gradient(to_bottom, rgba(148,163,184,0.18) 1px, transparent 1px); background-size: 24px 24px;"></div>

    <!-- Floating gradient blobs -->
    <div class="bg-blob-1 absolute -top-24 -right-24 h-96 w-96 rounded-full blur-3xl opacity-60 md:opacity-50" style="background: radial-gradient(closest-side, rgba(59,130,246,0.35), rgba(147,51,234,0.18), transparent 70%);"></div>
    <div class="bg-blob-2 absolute -bottom-32 -left-24 h-[28rem] w-[28rem] rounded-full blur-3xl opacity-60 md:opacity-45" style="background: radial-gradient(closest-side, rgba(16,185,129,0.30), rgba(6,182,212,0.18), transparent 70%);"></div>

  <!-- Subtle noise overlay (very light) -->
  <div aria-hidden="true" class="absolute inset-0 opacity-[0.05] mix-blend-overlay" style="background-image:url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%22160%22 viewBox=%220 0 100 100%22><filter id=%22n%22><feTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%224%22 stitchTiles=%22stitch%22/></filter><rect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23n)%22/></svg>'); background-size: cover;"></div>

  <!-- Mouse-follow spotlight -->
  <div aria-hidden="true" class="absolute inset-0 bg-spotlight opacity-70 md:opacity-60" style={`--spot-x: ${spotlightX}%; --spot-y: ${spotlightY}%;`}></div>
  </div>
  <!-- Top bar -->
  <header class="sticky top-0 z-20 border-b bg-white/90 dark:bg-slate-800/90 border-slate-200 dark:border-slate-700 backdrop-blur">
    <div class="mx-auto max-w-7xl px-4 py-3 flex items-center gap-4 justify-between">
      <div class="flex items-center gap-3">
        <button class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700" aria-label="Open sidebar" on:click={() => (sidebarOpen = true)}>
          ☰
        </button>
        <a href="/" class="font-semibold">TalentFlow</a>
        <span class="text-gray-400">/</span>
        <span class="text-gray-600">Dashboard</span>
      </div>
  <div></div>
    </div>
  </header>

  <!-- Backdrop -->
  <div class={sidebarOpen ? 'fixed inset-0 bg-black/40 z-30' : 'hidden'} on:click={() => (sidebarOpen = false)}></div>

  <!-- Full-page sidebar overlay with grouped sections and descriptions -->
  <aside class={`fixed inset-0 z-40 bg-white dark:bg-slate-800 overflow-y-auto transform transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`} aria-hidden={!sidebarOpen}>
    <div class="mx-auto max-w-7xl px-4 py-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center gap-2 text-gray-600 dark:text-gray-300 text-sm">
          <Icon name="home" />
          <span>All navigation</span>
        </div>
        <button class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700" aria-label="Close sidebar" on:click={() => (sidebarOpen = false)}>×</button>
      </div>

      <div class="mt-4 space-y-6">
        <section>
          <div class="px-1 mb-2 text-sm font-medium text-gray-700 dark:text-gray-200">Workflows</div>
          <ul class="grid md:grid-cols-2 lg:grid-cols-3 gap-2">
            {#each workflows as item}
              <li>
                <a href={item.href}
                   on:click={() => (sidebarOpen = false)}
                   class="flex items-start gap-3 border border-slate-200 dark:border-slate-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition">
                  <div class="mt-0.5"><Icon name={item.icon as any} /></div>
                  <div>
                    <div class="font-medium">{item.label}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{item.desc}</div>
                  </div>
                </a>
              </li>
            {/each}
          </ul>
        </section>

        <section>
          <div class="px-1 mb-2 text-sm font-medium text-gray-700 dark:text-gray-200">Resources</div>
          <ul class="grid md:grid-cols-2 lg:grid-cols-3 gap-2">
            {#each resources as item}
              <li>
                <a href={item.href}
                   on:click={() => (sidebarOpen = false)}
                   class="flex items-start gap-3 border border-slate-200 dark:border-slate-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition">
                  <div class="mt-0.5"><Icon name={item.icon as any} /></div>
                  <div>
                    <div class="font-medium">{item.label}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{item.desc}</div>
                  </div>
                </a>
              </li>
            {/each}
          </ul>
        </section>
      </div>
    </div>
  </aside>

  <!-- Content area -->
  <div class="mx-auto max-w-7xl px-4 py-6">
    <main class="min-w-0">
      <slot />
    </main>
  </div>

  <!-- Floating Support Chat -->
  <div class="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
    {#if chatOpen}
      <div class="w-80 max-w-[92vw] border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 shadow-xl">
        <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div class="text-sm font-medium flex items-center gap-1.5 text-gray-700 dark:text-gray-200"><Icon name="info" /> Support</div>
          <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" aria-label="Close support chat" on:click={() => chatOpen = false}>×</button>
        </div>
        <div class="p-3 max-h-72 overflow-auto space-y-2 text-sm">
          {#each chatMessages as m, i}
            <div class={m.role === 'user' ? 'text-right' : ''}>
              <div class={`inline-block rounded px-2 py-1 ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-gray-200'}`}>{m.text}</div>
            </div>
          {/each}
        </div>
        <form class="p-2 border-t border-slate-200 dark:border-slate-700 flex items-center gap-2" on:submit|preventDefault={sendChat}>
          <input class="flex-1 text-sm px-2 py-1 border rounded bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700"
                 placeholder="Type your message…" bind:value={chatInput} />
          <button type="submit" class="text-sm px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50" disabled={!chatInput.trim()}>Send</button>
        </form>
      </div>
    {/if}
    <button class="w-12 h-12 rounded-full shadow-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center border border-blue-700"
            aria-label="Open support chat"
            on:click={() => chatOpen = !chatOpen}>
      <span class="sr-only">Support</span>
      <Icon name="info" />
    </button>
  </div>
</div>

<style>
  /* Gentle motion for background blobs */
  @keyframes float1 {
    0% { transform: translate3d(0,0,0) scale(1); }
    50% { transform: translate3d(10px, -8px, 0) scale(1.05); }
    100% { transform: translate3d(0, 6px, 0) scale(1); }
  }
  @keyframes float2 {
    0% { transform: translate3d(0,0,0) scale(1); }
    50% { transform: translate3d(-8px, 10px, 0) scale(1.04); }
    100% { transform: translate3d(6px, 0, 0) scale(1); }
  }
  .bg-blob-1 { animation: float1 28s ease-in-out infinite alternate; }
  .bg-blob-2 { animation: float2 32s ease-in-out infinite alternate; }

  /* Prefer darker, softer accents for dark mode */
  @media (prefers-color-scheme: dark) {
    .bg-blob-1 { filter: saturate(90%) brightness(85%); }
    .bg-blob-2 { filter: saturate(90%) brightness(85%); }
  }

  /* Spotlight layer: radial gradient that follows mouse */
  .bg-spotlight {
    pointer-events: none;
    background: radial-gradient(300px 300px at var(--spot-x, 50%) var(--spot-y, 50%), rgba(255,255,255,0.16), rgba(255,255,255,0.06) 35%, transparent 65%);
  }
  @media (prefers-color-scheme: dark) {
    .bg-spotlight {
      background: radial-gradient(320px 320px at var(--spot-x, 50%) var(--spot-y, 50%), rgba(255,255,255,0.10), rgba(255,255,255,0.04) 35%, transparent 70%);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .bg-blob-1, .bg-blob-2 { animation: none; }
  }
</style>
