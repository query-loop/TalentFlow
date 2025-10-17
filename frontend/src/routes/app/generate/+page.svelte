<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  import jsPDF from 'jspdf';
  import { onMount } from 'svelte';
  import { normalizeText, extractMeta, extractExperienceYears, guessSeniority, findSkills, extractSections, buildReferenceText, formatJD } from '$lib/jd';
  import { PUBLIC_API_BASE } from '$env/static/public';
  import StepFooter from '$lib/components/StepFooter.svelte';
  import { getPipeline, type Pipeline } from '$lib/pipelines';
  import { getActivePipelineId } from '$lib/pipelineTracker';
  import { goto } from '$app/navigation';
  let job = '';
  // Theme removed; use default styling
  let loading = false;
  let result: any = null;
  let error = '';
  let activeTab: 'html' | 'pdf' = 'html';
  let prompt = '';
  let pdfUrl: string | null = null;
  // Resume library
  type ResumeOption = { id: string; label: string; text: string };
  let resumeOptions: ResumeOption[] = [];
  let selectedResumeId: string = '';
  let resumeText: string | null = null;
  // Chat state
  type ChatMsg = { role: 'user' | 'assistant'; text: string; when: number; provider?: string };
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
  const SHOW_JD_REF = false; // Hide JD reference UI and usage

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

  // Active pipeline context for header suffix
  let activePipeline: Pipeline | null = null;
  let pipelineHeaderName = '';

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
    topSkills: 6,
    topRequirements: 3,
    topResponsibilities: 2,
    maxChars: 240
  };
  let referenceText = '';
  $: hasReference = Boolean(referenceText && referenceText.trim().length);

  // JD selection for reference
  type JDItem = { id: string; company?: string; role?: string; location?: string; jd: string; extracted?: ExtractedJD | null; reference?: string | null };
  let jdOptions: JDItem[] = [];
  let selectedJDId: string = '';
  $: selectedJD = (jdOptions || []).find((x) => x.id === selectedJDId) || null;
  $: selectedCompany = selectedJD?.company || '';
  let displayedCompany: string = '';
  $: displayedCompany = (selectedCompany || (extracted?.company || '')).trim();
  // Company dropdown options (deduped by company name)
  type CompanyOption = { id: string; company: string };
  let companyOptions: CompanyOption[] = [];
  $: companyOptions = (() => {
    const seen = new Set<string>();
    const out: CompanyOption[] = [];
    for (const it of jdOptions) {
      const c = (it.company || '').trim();
      if (!c || seen.has(c)) continue;
      seen.add(c);
      out.push({ id: it.id, company: c });
    }
    return out;
  })();

  function loadJDOptions() {
    try { jdOptions = JSON.parse(localStorage.getItem('tf_jd_items') || '[]'); } catch { jdOptions = []; }
  }

  function labelFor(it: JDItem) {
    const a = it.company || '—';
    const b = it.role || 'Untitled';
    const c = it.location ? ` (${it.location})` : '';
    return `${a} — ${b}${c}`;
  }

  function computeExtractedFromJD(text: string): ExtractedJD {
    const cleaned = formatJD(text || '');
    const meta = extractMeta(cleaned);
    const rr = extractSections(cleaned);
    const experienceYears = extractExperienceYears(cleaned);
    const seniority = guessSeniority(cleaned);
    const skills = findSkills(cleaned);
    return {
      ...meta,
      location: meta.location,
      experienceYears,
      seniority,
      skills,
      responsibilities: rr.responsibilities,
      requirements: rr.requirements,
      raw: cleaned,
      when: Date.now()
    };
  }

  function loadSelectedJD(id: string) {
    if (!id) return;
    try {
      const list: JDItem[] = JSON.parse(localStorage.getItem('tf_jd_items') || '[]');
      const it = list.find(x => x.id === id);
      if (!it) return;
      // Prefer stored extracted; else compute
      const ex = it.extracted || computeExtractedFromJD(it.jd || '');
      extracted = ex;
      // Persist extracted for reuse
      localStorage.setItem('tf_extracted_jd', JSON.stringify(ex));
      // Do not build or persist JD reference, as this UI is disabled
      localStorage.removeItem('tf_generate_reference_text');
      localStorage.setItem('tf_generate_use_reference', 'false');
      localStorage.setItem('tf_generate_selected_jd', id);
    } catch {}
  }

  function apiBase(): string {
    const base = (PUBLIC_API_BASE || '').replace(/\/$/, '') || '';
    if (typeof window !== 'undefined') {
      // In the browser, prefer relative URLs when PUBLIC_API_BASE is not set
      return (PUBLIC_API_BASE && PUBLIC_API_BASE.length) ? base : '';
    }
    return base;
  }

  function trimWords(text: string, maxWords: number): string {
    const words = (text || '').split(/\s+/).filter(Boolean);
    if (words.length <= maxWords) return (text || '').trim();
    return words.slice(0, maxWords).join(' ') + '…';
  }

  // Saved resume shape for dashboard overview
  type SavedResume = {
    id: string;
    name: string;
    when: number;
    job?: string;
    result: { summary?: string; skills?: string[]; experience?: string[] };
  };

  // Redirect global Generate to the active pipeline's scoped page
  onMount(() => {
    try {
      const pid = getActivePipelineId();
      if (pid) {
        goto(`/app/pipeline/${pid}/generate`, { replaceState: true });
      } else {
        goto('/app/pipelines', { replaceState: true });
      }
    } catch {}
  });

  onMount(async () => {
    // Load active pipeline name for header context
    try {
      const pid = getActivePipelineId();
      if (pid) {
        activePipeline = await getPipeline(pid);
        pipelineHeaderName = (activePipeline?.name || activePipeline?.company || '').trim();
      }
    } catch {}

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
    // Load JD options and selected JD
    loadJDOptions();
    try {
      const savedSel = localStorage.getItem('tf_generate_selected_jd');
      if (savedSel) { selectedJDId = savedSel; loadSelectedJD(savedSel); }
    } catch {}
  // Load resume options
  await loadResumeOptions();
    try {
      const savedResSel = localStorage.getItem('tf_generate_selected_resume');
      if (savedResSel) {
        selectedResumeId = savedResSel;
        const found = resumeOptions.find(o => o.id === savedResSel);
        resumeText = found ? found.text : null;
      } else if (resumeOptions[0]) {
        selectedResumeId = resumeOptions[0].id; resumeText = resumeOptions[0].text;
      }
    } catch {}
  });

  // Refresh JD options when localStorage changes (e.g., after importing in Extract)
  onMount(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'tf_jd_items') loadJDOptions();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
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

  $: referenceText = SHOW_JD_REF ? buildReferenceText(extracted, refConfig) : '';

  async function generate() {
    error = '';
    result = null;
    loading = true;
    try {
      const payload: any = { job: (job || '').slice(0, 400), prompt, agentic: true, resumeText };
  const base = apiBase();
  const res = await fetch(`${base}/api/generate`, {
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
      // Also persist to backend library as a draft and select it
      try {
  const base2 = apiBase();
        const draftName = deriveResumeName();
        const fullText = result.fullText || `${result.summary || ''}\n\nSkills: ${(result.skills||[]).join(', ')}\n\n${(result.experience||[]).map((e:string)=>`• ${e}`).join('\n')}`;
  const resp = await fetch(`${base2}/api/library/draft`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name: draftName, text: fullText, meta: { from: 'generate' } }) });
        if (resp.ok) {
          const item = await resp.json();
          await loadResumeOptions();
          selectedResumeId = `lib_${item.id}`;
          localStorage.setItem('tf_generate_selected_resume', selectedResumeId);
        }
      } catch {}
      try {
        const actions = JSON.parse(localStorage.getItem('tf_recent_actions') || '[]');
        const name = deriveResumeName();
        const entry = { t: `Generated resume \"${name}\"`, when: new Date().toISOString() };
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
    chatInput = '';
    try {
  const base = apiBase();
      const ctxParts: string[] = [];
      // Include short conversation history for better continuity
      const recent = messages.slice(-8);
      if (recent.length) {
        const convo = recent.map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.text}`).join('\n');
        ctxParts.push(`Conversation so far:\n${convo}`);
      }
  // JD reference removed from context
      if (resumeText && resumeText.trim()) ctxParts.push(`Resume:\n${resumeText.slice(0, 2000)}`);
      const body: any = { question: text };
      if (ctxParts.length) body.context = ctxParts.join('\n\n');
      const res = await fetch(`${base}/api/qa`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      if (!res.ok) {
        messages = [...messages, { role: 'assistant', text: `Error: HTTP ${res.status}`, when: Date.now() }];
        return;
      }
  const data = await res.json();
  const answer = (data && data.answer) ? String(data.answer) : '(no answer)';
  const provider = (data && data.provider) ? String(data.provider) : undefined;
  messages = [...messages, { role: 'assistant', text: answer, when: Date.now(), provider }];
    } catch (e: any) {
      messages = [...messages, { role: 'assistant', text: `Error: ${e?.message || String(e)}`, when: Date.now() }];
    }
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
    // Upload to backend for text extraction
    (async () => {
      const fd = new FormData();
      fd.set('file', resumeFile!);
  const base = apiBase();
      const res = await fetch(`${base}/api/resume/parse-file`, { method: 'POST', body: fd });
      if (res.ok) {
        const data = await res.json();
        resumeText = data.text || null;
        try {
          localStorage.setItem('tf_user_resume_name', resumeFile!.name);
          localStorage.setItem('tf_user_resume_type', resumeFile!.type || '');
          localStorage.setItem('tf_user_resume_size', String(resumeFile!.size));
          if (resumeText) localStorage.setItem('tf_user_resume_text', resumeText);
        } catch {}
        savedResumeName = resumeFile!.name;
        messages = [
          ...messages,
          { role: 'assistant', text: `Attached your resume: ${resumeFile!.name}`, when: Date.now() }
        ];
        // Save to backend library as 'uploaded'
        try {
          const add = await fetch(`${base}/api/library/uploaded`, {
            method: 'POST', headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ name: resumeFile!.name, text: resumeText, meta: { size: resumeFile!.size, type: resumeFile!.type } })
          });
          if (add.ok) {
            await loadResumeOptions();
            try {
              const added = await add.json();
              const newId = `lib_${added.id}`;
              selectedResumeId = newId;
              localStorage.setItem('tf_generate_selected_resume', newId);
            } catch {}
          }
        } catch {}
      }
      showResumeModal = false;
    })();
  }

  // note: Edit · Ask labels are decorative only (non-interactive)

  function clearChat() {
    messages = [];
  }

  async function loadResumeOptions() {
    const opts: ResumeOption[] = [];
    // Backend library
    try {
  const base = apiBase();
      const res = await fetch(`${base}/api/library`);
      if (res.ok) {
        const data = await res.json();
        for (const it of data as Array<{id:number,name:string,kind:string,text:string}>) {
          const labelPrefix = it.kind === 'uploaded' ? 'Uploaded' : (it.kind === 'draft' ? 'Draft' : it.kind);
          opts.push({ id: `lib_${it.id}`, label: `${labelPrefix} — ${it.name}`, text: it.text });
        }
      }
    } catch {}
    // Local fallbacks
    try {
      const uploadedText = localStorage.getItem('tf_user_resume_text');
      const uploadedName = localStorage.getItem('tf_user_resume_name');
      if (uploadedText && uploadedText.trim()) {
        opts.push({ id: 'uploaded', label: uploadedName ? `Uploaded — ${uploadedName}` : 'Uploaded resume', text: uploadedText });
      }
    } catch {}
    try {
      const recent = JSON.parse(localStorage.getItem('tf_recent_resumes') || '[]');
      for (const it of recent) {
        if (it?.result?.fullText) {
          opts.push({ id: `draft_${it.id}`, label: `Draft — ${it.name || 'Resume'}`, text: String(it.result.fullText) });
        }
      }
    } catch {}
    resumeOptions = opts;
  }
  $: resumePreview = (() => {
    const t = (resumeText || '').trim();
    if (!t) return '';
    const lines = t.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const head = (lines[0] || '') + (lines[1] ? ` — ${lines[1]}` : '');
    return head.replace(/\s+/g, ' ');
  })();
</script>

<section class="space-y-4 h-[calc(100dvh-120px)]">
  <h1 class="text-xl font-semibold flex items-center gap-2">
    <Icon name="sparkles"/> Generate Resume
    {#if pipelineHeaderName}
      <span class="text-sm text-gray-500">— {pipelineHeaderName}</span>
    {/if}
  </h1>

  <div class="flex gap-3 items-stretch h-full min-h-0" bind:this={containerEl}>
    <!-- Left: Chat & Compose -->
    <div class="border rounded-xl bg-white/80 dark:bg-slate-800/70 supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:backdrop-blur-md border-slate-200/70 dark:border-slate-700/60 shadow-sm flex flex-col h-full min-h-0" style={`width:${leftWidth}%`}>
      <div class="px-3 py-2 border-b border-slate-200/70 dark:border-slate-700/60 text-sm text-gray-600 dark:text-gray-400 bg-white/40 dark:bg-slate-800/40 supports-[backdrop-filter]:bg-transparent">Prompt & Chat</div>
      <div class="p-4 space-y-4 overflow-auto min-h-0 flex-1 pb-16">
        <div class="space-y-3">
          <!-- Resume selector -->
          <div>
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-200">Resume</label>
              <button type="button" class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700" on:click={openResumeModal}>{savedResumeName ? 'Upload new' : 'Upload'}</button>
            </div>
            <div class="mt-1 flex items-center gap-2">
              <select class="flex-1 text-sm border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700"
                      bind:value={selectedResumeId}
                      on:change={(e) => {
                        const id = (e.target as HTMLSelectElement).value;
                        localStorage.setItem('tf_generate_selected_resume', id);
                        const found = resumeOptions.find(o => o.id === id);
                        resumeText = found ? found.text : null;
                      }}>
                <option value="">Select a resume…</option>
                {#each resumeOptions as opt}
                  <option value={opt.id}>{opt.label.length > 40 ? opt.label.slice(0,40) + '…' : opt.label}</option>
                {/each}
              </select>
            </div>
            {#if resumePreview}
              <div class="mt-2 text-[11px] text-gray-600 dark:text-gray-300 border rounded px-2 py-1 bg-gray-50/70 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700">
                <span class="font-medium">Using resume:</span>
                <span class="ml-1">{resumePreview.slice(0, 80)}{resumePreview.length > 80 ? '…' : ''}</span>
              </div>
            {:else}
              <div class="mt-2 text-[11px] text-gray-600 dark:text-gray-300">Choose or upload a resume to guide generation.</div>
            {/if}
            <!-- JD Company dropdown -->
            <div class="mt-2 flex items-end gap-2">
              <div class="flex-1">
                <label class="block text-[11px] text-gray-600 dark:text-gray-300 mb-1">Company (JD)</label>
                <select class="w-full text-sm border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700"
                        bind:value={selectedJDId}
                        on:change={(e) => { const id = (e.target as HTMLSelectElement).value; if (id) loadSelectedJD(id); }}>
                  <option value="">Select a company…</option>
                  {#each companyOptions as opt}
                    <option value={opt.id}>{opt.company}</option>
                  {/each}
                </select>
              </div>
              {#if selectedJDId}
                <button type="button"
                        class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700"
                        title="Clear selection"
                        on:click={() => { selectedJDId=''; try { localStorage.removeItem('tf_generate_selected_jd'); } catch {}; }}>
                  ×
                </button>
              {/if}
              <button type="button"
                      class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700"
                      title="Refresh JD list"
                      on:click={() => loadJDOptions()}>⟳</button>
            </div>
          </div>

          {#if SHOW_JD_REF}
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-200">JD reference</label>
              <a href="/app/extract" class="text-xs text-blue-600 hover:underline">Edit in Extract</a>
            </div>
            <div class="mt-1 flex items-center gap-2">
              <select class="flex-1 text-sm border rounded px-2 py-1.5 bg-white dark:bg-slate-900/40 border-slate-200 dark:border-slate-700"
                      bind:value={selectedJDId}
                      on:change={(e) => loadSelectedJD((e.target as HTMLSelectElement).value)}>
                <option value="">Select a JD…</option>
                {#each jdOptions as it}
                  <option value={it.id}>{labelFor(it)}</option>
                {/each}
              </select>
              <button type="button" class="text-xs px-2 py-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50" on:click={() => loadSelectedJD(selectedJDId)} disabled={!selectedJDId}>Refresh</button>
            </div>
            {#if hasReference}
              <div class="mt-2 text-[11px] text-gray-600 dark:text-gray-300 border rounded px-2 py-1 bg-gray-50/70 dark:bg-slate-900/40 border-slate-200 dark:border-slate-700">
                <span class="font-medium">Company:</span>
                <span class="ml-1">{selectedCompany || '—'}</span>
              </div>
            {:else}
              <div class="mt-2 text-[11px] text-gray-600 dark:text-gray-300">Choose a JD to build reference text automatically.</div>
            {/if}
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
              <div class={m.role === 'user' ? 'flex justify-start' : 'flex justify-end'}>
                <div class="max-w-[75%] lg:max-w-[66%]">
                  <div class={`px-3 py-1.5 rounded-2xl whitespace-normal break-words leading-relaxed text-sm ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-gray-800 dark:text-gray-200'}`}>{m.text}</div>
                  {#if m.role === 'assistant' && m.provider}
                    <div class="mt-1 text-[10px] text-gray-500 dark:text-gray-400">via {m.provider}</div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>
      <!-- Fixed prompt input at the bottom -->
      <form class="p-3 border-t border-slate-200/70 dark:border-slate-700/60 flex items-center gap-2 bg-gray-50/70 dark:bg-slate-900/40 supports-[backdrop-filter]:bg-white/40 supports-[backdrop-filter]:backdrop-blur-md" on:submit|preventDefault={sendChat}>
        <button type="submit" class="text-sm px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-600/95 shadow-sm hover:shadow transition disabled:opacity-50" disabled={!chatInput.trim()}>Send</button>
        <div class="relative flex-1">
          <input class="w-full text-sm px-3 py-2 pr-10 border rounded bg-white/90 dark:bg-slate-800/80 supports-[backdrop-filter]:bg-white/70 supports-[backdrop-filter]:backdrop-blur border-slate-200/70 dark:border-slate-700/60 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900/40" bind:value={chatInput} bind:this={chatInputEl} placeholder="Ask a question and press Enter" />
        </div>
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
          <div class="text-[11px] text-gray-500 dark:text-gray-400">Preview format: <span class="font-medium">{activeTab.toUpperCase()}</span></div>
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
              {#if result.plan?.length}
              <div>
                <div class="font-medium">Agent plan</div>
                <ul class="list-disc pl-5 text-sm text-gray-700 dark:text-gray-200">
                  {#each result.plan as p}
                    <li>{p}</li>
                  {/each}
                </ul>
              </div>
              {/if}
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
              {#if result.fullText}
              <div>
                <div class="font-medium">Full resume draft</div>
                <pre class="text-xs whitespace-pre-wrap bg-gray-50/80 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700 rounded p-3">{result.fullText}</pre>
              </div>
              {/if}
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

<StepFooter current="generate" canComplete={() => Boolean(result)} />

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
