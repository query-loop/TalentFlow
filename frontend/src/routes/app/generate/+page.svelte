<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import jsPDF from 'jspdf';
  import { onMount } from 'svelte';
  import { normalizeText, extractMeta, extractExperienceYears, guessSeniority, findSkills, extractSections, buildReferenceText, formatJD } from '$lib/jd';
  let job = '';
  // Theme removed; use default styling
  let loading = false;
  let result: any = null;
  let error = '';
  let activeTab: 'html' | 'pdf' = 'html';
  let prompt = '';
  let pdfUrl: string | null = null;
  // Chat state
  type ChatMsg = { role: 'user' | 'assistant'; text: string; when: number };
  let messages: ChatMsg[] = [];
  let chatInput = '';
  let chatInputEl: HTMLInputElement;
  let previewUpdatedAt: number | null = null;
  let showResumeModal = false;
  let resumeFile: File | null = null;
  let savedResumeName: string | null = null;
  // Resizer
  let containerEl: HTMLDivElement;
  let leftWidth = 50; // percent
  // Job description view state
  type JDView = 'hidden' | 'compact' | 'expanded';
  let jdView: JDView = 'compact';

  // Extracted JD state
  type ExtractedJD = {
    title?: string;
    company?: string;
    location?: string;
    experienceYears?: number | null;
    seniority?: string | null;
    skills: string[];
    responsibilities: string[];
    requirements: string[];
    raw: string;
    when: number;
  };
  let extracted: ExtractedJD | null = null;
  let extracting = false;

  // Reference builder config/state
  type RefConfig = {
    includeMeta: boolean;
    includeSkills: boolean;
    includeRequirements: boolean;
    includeResponsibilities: boolean;
    topSkills: number;
    topRequirements: number;
    topResponsibilities: number;
    maxChars: number;
  };
  let useReference = false;
  let refConfig: RefConfig = {
    includeMeta: true,
    includeSkills: true,
    includeRequirements: true,
    includeResponsibilities: false,
    topSkills: 10,
    topRequirements: 5,
    topResponsibilities: 4,
    maxChars: 800
  };
  let referenceText = '';
  $: hasReference = Boolean(referenceText && referenceText.trim().length);

  // Saved resume shape for dashboard overview
  type SavedResume = {
    id: string;
    name: string;
    when: number;
    job?: string;
    result: { summary?: string; skills?: string[]; experience?: string[] };
  };

  onMount(() => {
    try {
      const savedJob = localStorage.getItem('tf_generate_job');
      if (savedJob) job = savedJob;
    } catch {}
    try {
      const savedView = localStorage.getItem('tf_generate_jd_view') as JDView | null;
      if (savedView === 'hidden' || savedView === 'compact' || savedView === 'expanded') jdView = savedView;
    } catch {}
    try {
      const raw = localStorage.getItem('tf_extracted_jd');
      if (raw) extracted = JSON.parse(raw);
    } catch {}
    try {
      const savedUse = localStorage.getItem('tf_generate_use_reference');
      useReference = savedUse ? savedUse === 'true' : false;
      const savedCfg = localStorage.getItem('tf_generate_reference_config');
      if (savedCfg) refConfig = { ...refConfig, ...JSON.parse(savedCfg) };
      const savedRef = localStorage.getItem('tf_generate_reference_text');
      if (savedRef) referenceText = savedRef;
    } catch {}
  });

  // If a resume was selected from the overview, load it
  onMount(() => {
    try {
      const raw = localStorage.getItem('tf_selected_resume');
      if (!raw) return;
      const sel = JSON.parse(raw) as SavedResume;
      if (sel?.result) {
        job = sel.job || '';
        result = sel.result;
        previewUpdatedAt = Date.now();
        buildPdf();
      }
    } catch {}
    finally { try { localStorage.removeItem('tf_selected_resume'); } catch {} }
  });

  $: (() => { try { localStorage.setItem('tf_generate_job', job); } catch {} })();
  $: (() => { try { localStorage.setItem('tf_generate_jd_view', jdView); } catch {} })();
  $: (() => { try { localStorage.setItem('tf_generate_use_reference', String(useReference)); } catch {} })();
  $: (() => { try { localStorage.setItem('tf_generate_reference_config', JSON.stringify(refConfig)); } catch {} })();
  $: (() => { try { localStorage.setItem('tf_generate_reference_text', referenceText); } catch {} })();

  // Using shared JD helpers from $lib/jd

  function updatePipelineAfterExtract() {
    try {
      let list = [] as any[];
      const raw = localStorage.getItem('tf_pipelines');
      if (raw) list = JSON.parse(raw);
      if (!list.length) {
        const id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
        list = [{ id, name: 'Pipeline 1', createdAt: Date.now(), statuses: { extract: 'pending', generate: 'pending', keywords: 'pending', ats: 'pending', export: 'pending', save: 'pending' } }];
        localStorage.setItem('tf_active_pipeline', list[0].id);
      }
      const activeId = localStorage.getItem('tf_active_pipeline') || list[0].id;
      const p = list.find((x: any) => x.id === activeId) || list[0];
      // Mark extract complete; advance generate to active if not already complete
      p.statuses.extract = 'complete';
      if (p.statuses.generate !== 'complete') {
        const keys: Array<'extract'|'generate'|'keywords'|'ats'|'export'|'save'> = ['extract','generate','keywords','ats','export','save'];
        for (const k of keys) {
          if (p.statuses[k] !== 'complete') p.statuses[k] = 'pending';
        }
        p.statuses.generate = 'active';
      }
      localStorage.setItem('tf_pipelines', JSON.stringify(list));
    } catch {}
  }

  async function extractJD() {
    extracting = true;
    try {
      const text = normalizeText(job);
      if (!text) { extracted = null; return; }
      // Optionally standardize formatting for consistent parsing
      const cleaned = formatJD(text);
      const meta = extractMeta(text);
      const responsibilitiesRequirements = extractSections(cleaned);
      const experienceYears = extractExperienceYears(cleaned);
      const seniority = guessSeniority(cleaned);
      const skills = findSkills(cleaned);
      const payload: ExtractedJD = {
        ...meta,
        location: meta.location,
        experienceYears,
        seniority,
        skills,
        responsibilities: responsibilitiesRequirements.responsibilities,
        requirements: responsibilitiesRequirements.requirements,
        raw: cleaned,
        when: Date.now()
      };
      extracted = payload;
      try { localStorage.setItem('tf_extracted_jd', JSON.stringify(payload)); } catch {}
      try {
        const actions = JSON.parse(localStorage.getItem('tf_recent_actions') || '[]');
        const entry = { t: `Extracted job description${payload.title ? ` for "${payload.title}"` : ''}`, when: new Date().toISOString() };
        localStorage.setItem('tf_recent_actions', JSON.stringify([entry, ...actions].slice(0, 50)));
      } catch {}
      updatePipelineAfterExtract();
      // Recompute reference text with current config
      referenceText = buildReferenceText(payload, refConfig);
    } finally {
      extracting = false;
    }
  }

  function cleanJD() {
    job = formatJD(job);
  }

  $: referenceText = buildReferenceText(extracted, refConfig);

  async function generate() {
    error = '';
    result = null;
    loading = true;
    try {
      if (!hasReference) {
        throw new Error('No JD reference found. Go to Extract to build a reference first.');
      }
      const payload = { job: referenceText, prompt };
      const res = await fetch('/api/mock/generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      result = await res.json();
      localStorage.setItem('tf_last_generated_at', new Date().toISOString());
      // Prebuild PDF for the PDF tab
      buildPdf();
  previewUpdatedAt = Date.now();
      // Save to recent resumes and recent actions
      saveRecentResume();
      try {
        const actions = JSON.parse(localStorage.getItem('tf_recent_actions') || '[]');
        const name = deriveResumeName();
  const entry = { t: `Generated resume \"${name}\" (with JD reference)`, when: new Date().toISOString() };
        localStorage.setItem('tf_recent_actions', JSON.stringify([entry, ...actions].slice(0, 50)));
      } catch {}
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally { loading = false; }
  }

  function deriveResumeName() {
    const base = (job || '').split('\n').map(s => s.trim()).filter(Boolean)[0] || '';
    const trimmed = base.length ? base.slice(0, 60) : '';
    const dt = new Date();
    const stamp = dt.toLocaleDateString() + ' ' + dt.toLocaleTimeString();
    return trimmed ? `${trimmed}` : `Resume ${stamp}`;
  }

  function saveRecentResume() {
    try {
      if (!result) return;
      const item: SavedResume = {
        id: crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
        name: deriveResumeName(),
        when: Date.now(),
        job,
        result: { summary: result.summary, skills: result.skills, experience: result.experience }
      };
      const list = JSON.parse(localStorage.getItem('tf_recent_resumes') || '[]');
      const updated = [item, ...list].slice(0, 25);
      localStorage.setItem('tf_recent_resumes', JSON.stringify(updated));
    } catch {}
  }

  function buildPdf() {
    try {
      if (!result) return;
      const doc = new jsPDF();
      const lineHeight = 7;
      let y = 15;
      doc.setFontSize(16);
      doc.text('Resume Preview', 15, y);
      y += 10;
      doc.setFontSize(12);
      // Summary
      doc.setFont(undefined, 'bold');
      doc.text('Summary', 15, y); y += 6;
      doc.setFont(undefined, 'normal');
      const summaryLines = doc.splitTextToSize(String(result.summary || ''), 180);
      summaryLines.forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += 6; });
      y += 4;
      // Skills
      doc.setFont(undefined, 'bold');
      doc.text('Skills', 15, y); y += 6;
      doc.setFont(undefined, 'normal');
      const skills = (result.skills || []).join(', ');
      const skillLines = doc.splitTextToSize(skills, 180);
      skillLines.forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += 6; });
      y += 4;
      // Experience
      doc.setFont(undefined, 'bold');
      doc.text('Experience Highlights', 15, y); y += 6;
      doc.setFont(undefined, 'normal');
      (result.experience || []).forEach((e: string) => {
        const bullet = `• ${e}`;
        const lines = doc.splitTextToSize(bullet, 180);
        lines.forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += lineHeight; });
      });

      // Create object URL for embed
      const blob = doc.output('blob');
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      pdfUrl = URL.createObjectURL(blob);
    } catch (e) {
      console.error('PDF build failed', e);
    }
  }

  function exportPDF() {
    if (!result) return;
    const doc = new jsPDF();
    // Simple re-run to export; could share the same instance
    const lineHeight = 7;
    let y = 15;
    doc.setFontSize(16);
    doc.text('Resume Preview', 15, y);
    y += 10;
    doc.setFontSize(12);
    doc.setFont(undefined, 'bold');
    doc.text('Summary', 15, y); y += 6;
    doc.setFont(undefined, 'normal');
    doc.splitTextToSize(String(result.summary || ''), 180).forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += 6; });
    y += 4;
    doc.setFont(undefined, 'bold');
    doc.text('Skills', 15, y); y += 6;
    doc.setFont(undefined, 'normal');
    doc.splitTextToSize((result.skills || []).join(', '), 180).forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += 6; });
    y += 4;
    doc.setFont(undefined, 'bold');
    doc.text('Experience Highlights', 15, y); y += 6;
    doc.setFont(undefined, 'normal');
    (result.experience || []).forEach((e: string) => {
      const bullet = `• ${e}`;
      const lines = doc.splitTextToSize(bullet, 180);
      lines.forEach((ln: string) => { if (y > 280) { doc.addPage(); y = 15; } doc.text(ln, 15, y); y += lineHeight; });
    });
    doc.save('resume.pdf');
  }

  async function sendChat() {
    const text = chatInput.trim();
    if (!text) return;
  messages = [...messages, { role: 'user', text, when: Date.now() }];
    prompt = text;
    chatInput = '';
    await generate();
    messages = [...messages, { role: 'assistant', text: 'Updated the draft based on your prompt. Check the preview on the right.', when: Date.now() }];
  }

  function startResize(e: MouseEvent) {
    e.preventDefault();
    const rect = containerEl.getBoundingClientRect();
    const onMove = (ev: MouseEvent) => {
      const p = ((ev.clientX - rect.left) / rect.width) * 100;
      leftWidth = Math.max(20, Math.min(80, p));
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  function openResumeModal() {
    try { savedResumeName = localStorage.getItem('tf_user_resume_name'); } catch {}
    resumeFile = null;
    showResumeModal = true;
  }

  function saveResume() {
    if (!resumeFile) {
      showResumeModal = false;
      return;
    }
    try {
      localStorage.setItem('tf_user_resume_name', resumeFile.name);
      localStorage.setItem('tf_user_resume_type', resumeFile.type || '');
      localStorage.setItem('tf_user_resume_size', String(resumeFile.size));
    } catch {}
    savedResumeName = resumeFile.name;
    showResumeModal = false;
    messages = [
      ...messages,
      { role: 'assistant', text: `Attached your resume: ${resumeFile.name}`, when: Date.now() }
    ];
  }

  // note: Edit · Ask labels are decorative only (non-interactive)

  function clearChat() {
    messages = [];
  }
</script>

<svelte:window />

<section class="space-y-4 h-[calc(100dvh-120px)]">
  <h1 class="text-xl font-semibold flex items-center gap-2"><Icon name="sparkles"/> Generate Resume</h1>

  <div class="flex gap-3 items-stretch h-full min-h-0" bind:this={containerEl}>
    <!-- Left: Chat & Compose -->
    <div class="border rounded-xl bg-white/80 dark:bg-slate-800/70 supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:backdrop-blur-md border-slate-200/70 dark:border-slate-700/60 shadow-sm flex flex-col h-full min-h-0" style={`width:${leftWidth}%`}>
      <div class="px-3 py-2 border-b border-slate-200/70 dark:border-slate-700/60 text-sm text-gray-600 dark:text-gray-400 bg-white/40 dark:bg-slate-800/40 supports-[backdrop-filter]:bg-transparent">Prompt & Chat</div>
      <div class="p-4 space-y-4 overflow-auto min-h-0 flex-1 pb-16">
        <div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium text-gray-700 dark:text-gray-200">JD reference</label>
            <a href="/app/extract" class="text-xs text-blue-600 hover:underline">Edit in Extract</a>
          </div>
          {#if hasReference}
            <div class="mt-1 relative">
              <textarea class="w-full text-xs border rounded p-2 bg-gray-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700 min-h-[120px]" readonly>{referenceText}</textarea>
              <div class="absolute bottom-1 right-1 text-[10px] text-gray-500">{referenceText.length}</div>
            </div>
          {:else}
            <div class="mt-1 text-xs text-gray-600 dark:text-gray-300">No reference yet. Go to Extract to build one.</div>
          {/if}
        </div>
        <div class="space-y-2">
          <div class="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between">
            <span>Conversation</span>
            {#if messages.length}
              <button type="button" class="text-[11px] underline decoration-slate-300 hover:decoration-slate-500 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" on:click={clearChat} aria-label="Clear chat">Clear</button>
            {/if}
          </div>
          <div class={`border rounded-md p-3 h-full max-h-[60vh] overflow-auto space-y-3 tf-scroll ${messages.length ? 'bg-gray-50 dark:bg-slate-900/40' : 'bg-transparent'}`} role="log" aria-live="polite">
            {#each messages as m}
              <div class={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div class="max-w-[75%] lg:max-w-[66%]">
                  <div class={`px-3 py-1.5 rounded-2xl whitespace-normal break-words leading-relaxed text-sm ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-200'}`}>{m.text}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>
      <!-- Fixed prompt input at the bottom -->
      <form class="p-3 border-t border-slate-200/70 dark:border-slate-700/60 flex items-center gap-2 bg-gray-50/70 dark:bg-slate-900/40 supports-[backdrop-filter]:bg-white/40 supports-[backdrop-filter]:backdrop-blur-md" on:submit|preventDefault={sendChat}>
        <div class="relative flex-1">
          <input class="w-full text-sm px-3 py-2 pr-10 border rounded bg-white/90 dark:bg-slate-800/80 supports-[backdrop-filter]:bg-white/70 supports-[backdrop-filter]:backdrop-blur border-slate-200/70 dark:border-slate-700/60 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900/40" bind:value={chatInput} bind:this={chatInputEl} placeholder="Type a prompt and press Enter" />
        </div>
        <button type="submit" class="text-sm px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-600/95 shadow-sm hover:shadow transition disabled:opacity-50" disabled={!chatInput.trim()}>Send</button>
      </form>
    </div>

    <!-- Divider -->
  <div class="w-1 self-stretch bg-slate-200/70 dark:bg-slate-700/60 rounded cursor-col-resize" on:mousedown={startResize} title="Drag to resize"></div>

    <!-- Right: Preview -->
    <div class="flex-1 border rounded-xl bg-white/80 dark:bg-slate-800/70 supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:backdrop-blur-md border-slate-200/70 dark:border-slate-700/60 shadow-sm flex flex-col h-full min-h-0">
      <div class="px-3 py-2 border-b border-slate-200/70 dark:border-slate-700/60 flex items-center gap-2 bg-white/40 dark:bg-slate-800/40 supports-[backdrop-filter]:bg-transparent">
        <button class={`text-xs px-2 py-1 rounded ${activeTab === 'html' ? 'bg-blue-600 text-white' : 'border border-slate-200 dark:border-slate-700'}`} on:click={() => activeTab = 'html'}>HTML</button>
        <button class={`text-xs px-2 py-1 rounded ${activeTab === 'pdf' ? 'bg-blue-600 text-white' : 'border border-slate-200 dark:border-slate-700'}`} on:click={() => activeTab = 'pdf'}>PDF</button>
        <div class="ml-auto flex items-center gap-2">
          {#if previewUpdatedAt}
            <div class="text-[11px] text-emerald-700 dark:text-emerald-400 flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>Up to date</div>
          {/if}
          <button class="text-xs px-2 py-1 rounded border border-slate-200/70 dark:border-slate-700/60 hover:bg-white/50 dark:hover:bg-slate-700/40 transition" on:click={exportPDF}>Export</button>
        </div>
      </div>
  <div class="flex-1 p-4 overflow-auto min-h-0">
        {#if error}
          <div class="text-sm text-red-700 dark:text-red-400">{error}</div>
        {/if}
        {#if result}
          {#if activeTab === 'html'}
            <div class="max-w-[800px] mx-auto bg-white/95 dark:bg-slate-800/90 supports-[backdrop-filter]:bg-white/80 supports-[backdrop-filter]:backdrop-blur rounded-lg shadow p-6 space-y-3 border border-slate-200/70 dark:border-slate-700/60">
              <div>
                <div class="font-medium">Summary</div>
                <p class="text-sm text-gray-700 dark:text-gray-200">{result.summary}</p>
              </div>
              <div>
                <div class="font-medium">Skills</div>
                <div class="flex flex-wrap gap-2">
                  {#each result.skills as s}
                    <span class="px-2 py-1 rounded border text-xs bg-gray-50/80 dark:bg-slate-700/70 border-slate-200/70 dark:border-slate-600/60">{s}</span>
                  {/each}
                </div>
              </div>
              <div>
                <div class="font-medium">Experience Highlights</div>
                <ul class="list-disc pl-5 text-sm text-gray-700 dark:text-gray-200">
                  {#each result.experience as e}
                    <li>{e}</li>
                  {/each}
                </ul>
              </div>
            </div>
          {:else}
            <!-- PDF live preview -->
            {#if pdfUrl}
              <object data={pdfUrl} type="application/pdf" class="w-full h-full min-h-[300px] rounded-lg border border-slate-200/70 dark:border-slate-700/60 bg-white/70 supports-[backdrop-filter]:bg-white/40 supports-[backdrop-filter]:backdrop-blur" aria-label="Resume PDF preview">
                <iframe src={pdfUrl} class="w-full h-full" title="Resume PDF preview"></iframe>
              </object>
            {:else}
              <div class="h-full min-h-[300px] border border-dashed rounded flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">Generate to build the PDF</div>
            {/if}
          {/if}
        {:else}
          <div class="h-full min-h-[300px] flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">Generate to see the preview</div>
        {/if}
      </div>
    </div>
  </div>
</section>

{#if showResumeModal}
  <div class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" on:click={() => showResumeModal = false}>
    <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 w-[min(90vw,640px)] p-4" on:click|stopPropagation>
      <div class="text-sm font-medium mb-2">Attach your resume</div>
      <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">Supported: PDF, DOCX, TXT. We store only name/type/size locally.</div>
      <label class="block border border-dashed rounded p-4 text-center cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/30">
        <input type="file" class="hidden" accept=".pdf,.doc,.docx,.txt" on:change={(e: Event) => { const t = e.target as HTMLInputElement; resumeFile = t.files && t.files[0] ? t.files[0] : null; }} />
        <div class="text-sm">Click to choose a file</div>
        <div class="text-xs text-gray-500">or drop it here</div>
      </label>
      {#if resumeFile}
        <div class="mt-3 text-sm">
          Selected: <span class="font-medium">{resumeFile.name}</span>
          <span class="text-xs text-gray-500 ml-1">({resumeFile.type || 'unknown'}, {(resumeFile.size/1024).toFixed(1)} KB)</span>
        </div>
      {:else if savedResumeName}
        <div class="mt-3 text-sm text-gray-600 dark:text-gray-300">Previously saved: <span class="font-medium">{savedResumeName}</span></div>
      {/if}
      <div class="mt-3 flex justify-end gap-2">
        <button class="px-3 py-1.5 text-sm rounded border border-slate-200 dark:border-slate-700" on:click={() => showResumeModal = false}>Cancel</button>
        <button class="px-3 py-1.5 text-sm rounded bg-blue-600 text-white disabled:opacity-50" on:click={saveResume} disabled={!resumeFile}>Save</button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Scoped chat scroll styling */
  .tf-scroll::-webkit-scrollbar {
    width: 10px;
  }
  .tf-scroll::-webkit-scrollbar-thumb {
    background-color: rgba(100,116,139,0.5); /* slate-500 */
    border-radius: 8px;
    border: 2px solid transparent;
    background-clip: content-box;
  }
  .tf-scroll::-webkit-scrollbar-track {
    background: transparent;
  }
</style>
