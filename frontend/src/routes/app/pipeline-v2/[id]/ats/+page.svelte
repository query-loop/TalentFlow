<script lang="ts">
  import StepFooterV2 from '$lib/components/StepFooterV2.svelte';
  import { page } from '$app/stores';
  import { getPipelineV2, recomputeAtsV2, type PipelineV2 } from '$lib/pipelinesV2';
  import AtsGauge from '$lib/components/AtsGauge.svelte';

  $: id = $page.params.id;
  let pipe: PipelineV2 | null = null;
  let loading = true;
  let error: string | null = null;
  let runBusy = false;
  let autoTried = false;

  let pct: number | null = null;
  let matched: string[] = [];
  let missing: string[] = [];
  let structureMissing: string[] = [];
  $: pct = getAtsPercent(pipe);
  $: matched = getMatched(pipe);
  $: missing = getMissing(pipe);
  $: structureMissing = getStructureMissing(pipe);

  async function load() {
    if (!id) return;
    try {
      loading = true; error = null; pipe = await getPipelineV2(id);

      // Show ATS immediately: if it's missing but we already have JD+resume, recompute ATS only.
      if (!autoTried && pipe && getAtsPercent(pipe) === null && canComputeAts(pipe)) {
        autoTried = true;
        await recomputeAts();
      }
    } catch (e:any) { error = e?.message || 'Failed to load pipeline'; }
    finally { loading = false; }
  }

  function canComputeAts(p: PipelineV2): boolean {
    const a: any = (p.artifacts || {}) as any;

    const jd = a.jd;
    const jdText = (jd && typeof jd === 'object')
      ? (jd.description || jd.descriptionRaw || (jd.extracted && (jd.extracted.description || jd.extracted.descriptionRaw || jd.extracted.raw || jd.extracted.text)))
      : null;
    const hasJd = Boolean((jdText && String(jdText).trim()) || (p.jdId && String(p.jdId).startsWith('manual:') && String(p.jdId).slice('manual:'.length).trim()));

    const hasProfile = Boolean(a.profile && typeof a.profile === 'object' && a.profile.parsed);
    const hasResume = Boolean(
      hasProfile ||
      (a.resume && typeof a.resume === 'object' && a.resume.text) ||
      (p.resumeId && String(p.resumeId).trim())
    );

    return hasJd && hasResume;
  }

  function getAtsPercent(p: PipelineV2 | null): number | null {
    const ats = p?.artifacts && (p.artifacts as any).ats;
    if (!ats || typeof ats !== 'object') return null;
    if (typeof ats.aggregate === 'number') return Math.max(0, Math.min(100, Math.round(ats.aggregate * 100)));
    if (typeof ats.coverage === 'number') return Math.max(0, Math.min(100, Math.round(ats.coverage)));
    if (typeof ats.percent === 'number') return Math.max(0, Math.min(100, Math.round(ats.percent)));
    if (typeof ats.score === 'number') {
      const v = ats.score;
      return Math.max(0, Math.min(100, Math.round(v <= 1 ? v * 100 : v)));
    }
    return null;
  }

  function getMatched(p: PipelineV2 | null): string[] {
    const a = p?.artifacts && (p.artifacts as any).ats;
    if (!a || typeof a !== 'object') return [];
    const mk = Array.isArray(a.matched_keywords) ? a.matched_keywords
      : Array.isArray(a.matched) ? a.matched
      : [];
    return mk.map((x: any) => String(x)).filter(Boolean);
  }

  function getMissing(p: PipelineV2 | null): string[] {
    const a = p?.artifacts && (p.artifacts as any).ats;
    if (!a || typeof a !== 'object') return [];
    const ms = Array.isArray(a.missing_keywords) ? a.missing_keywords
      : Array.isArray(a.missing) ? a.missing
      : [];
    return ms.map((x: any) => String(x)).filter(Boolean);
  }

  function getStructureMissing(p: PipelineV2 | null): string[] {
    const a = p?.artifacts && (p.artifacts as any).ats;
    const d = a && typeof a === 'object' ? a.structure_details : null;
    if (!d || typeof d !== 'object') return [];
    const out: string[] = [];
    if (d.has_skills === false) out.push('Skills section not detected');
    if (d.has_experience === false) out.push('Experience section not detected');
    if (d.has_education === false) out.push('Education section not detected');
    return out;
  }

  async function recomputeAts() {
    if (!pipe || runBusy) return;
    runBusy = true;
    try {
      pipe = await recomputeAtsV2(pipe.id);
    } catch (e: any) {
      error = e?.message || 'Failed to recompute ATS';
    } finally {
      runBusy = false;
    }
  }

  $: if (id) load();
</script>

{#if loading}
  <div class="p-4">
    <div class="animate-pulse space-y-3">
      <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
      <div class="h-24 bg-slate-200 dark:bg-slate-700 rounded"></div>
    </div>
  </div>
{:else if error}
  <div class="m-4 border border-red-200 bg-red-50 dark:bg-red-900/20 rounded p-3 text-sm text-red-800">{error}</div>
{:else}
  <div class="p-4 space-y-4">
    <div class="flex items-center justify-between">
      <div class="text-sm font-semibold">ATS Score</div>
      <button class="px-3 py-1.5 rounded bg-blue-600 text-white text-xs" on:click={recomputeAts} disabled={runBusy}>
        {runBusy ? 'Running…' : 'Recompute'}
      </button>
    </div>

    <div class="border rounded p-4 bg-white dark:bg-slate-800 flex items-center justify-center">
      <AtsGauge value={getAtsPercent(pipe)} size={220} label="ATS" />
    </div>

    <div class="border rounded p-4 bg-white dark:bg-slate-800">
      <div class="text-sm font-semibold">Summary</div>
      <div class="mt-1 text-sm text-slate-700 dark:text-slate-200">
        {#if pct === null}
          No ATS score yet. Click “Recompute” after JD + resume are attached.
        {:else if pct >= 80}
          Strong match. Your resume aligns well with this JD.
        {:else if pct >= 60}
          Good match. A few targeted additions could improve it.
        {:else if pct >= 40}
          Moderate match. Several JD requirements are missing or unclear.
        {:else}
          Low match. Consider tailoring skills/experience wording to the JD.
        {/if}
      </div>
      {#if structureMissing.length}
        <div class="mt-2 text-xs text-rose-700 dark:text-rose-300">Structure gaps: {structureMissing.join(' · ')}</div>
      {/if}
    </div>

    <div class="grid md:grid-cols-2 gap-4">
      <div class="border rounded p-4 bg-white dark:bg-slate-800">
        <div class="text-sm font-semibold">Strengths</div>
        {#if matched.length}
          <div class="mt-2 text-xs text-slate-600 dark:text-slate-300">Matched requirements ({matched.length})</div>
          <ul class="mt-2 list-disc pl-5 text-xs text-slate-700 dark:text-slate-200 space-y-1">
            {#each matched.slice(0, 12) as m}
              <li>{m}</li>
            {/each}
          </ul>
        {:else}
          <div class="mt-2 text-xs text-slate-500 dark:text-slate-400">No matched requirements found yet.</div>
        {/if}
      </div>
      <div class="border rounded p-4 bg-white dark:bg-slate-800">
        <div class="text-sm font-semibold">Weaknesses</div>
        {#if missing.length}
          <div class="mt-2 text-xs text-slate-600 dark:text-slate-300">Missing requirements ({missing.length})</div>
          <ul class="mt-2 list-disc pl-5 text-xs text-rose-700 dark:text-rose-300 space-y-1">
            {#each missing.slice(0, 12) as mm}
              <li>{mm}</li>
            {/each}
          </ul>
          <div class="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Tip: add only true experience/skills; keep wording consistent with the JD.</div>
        {:else}
          <div class="mt-2 text-xs text-slate-500 dark:text-slate-400">No missing requirements detected.</div>
        {/if}
      </div>
    </div>

    <StepFooterV2 current="ats" pipelineId={id} />
  </div>
{/if}
