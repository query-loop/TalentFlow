<script lang="ts">
  export let value: number | null = null; // percent 0..100
  export let size = 140; // px
  export let label = 'ATS';

  const clamp = (n: number) => Math.max(0, Math.min(100, n));
  $: pct = value === null || Number.isNaN(value as any) ? null : clamp(Math.round(value));

  // Needle rotates from left (0%) -> up (50%) -> right (100%).
  $: needleDeg = pct === null ? 0 : (pct * 1.8);

  $: tone = pct === null ? 'muted' : (pct >= 70 ? 'good' : (pct >= 40 ? 'warn' : 'bad'));
  $: arcClass = tone === 'good'
    ? 'stroke-emerald-600 dark:stroke-emerald-400'
    : tone === 'warn'
      ? 'stroke-yellow-500 dark:stroke-yellow-400'
      : tone === 'bad'
        ? 'stroke-rose-600 dark:stroke-rose-400'
        : 'stroke-slate-300 dark:stroke-slate-600';
</script>

<div class="relative" style={`width:${size}px;height:${Math.round(size * 0.7)}px`} aria-label={label}>
  <svg viewBox="0 0 100 60" class="w-full h-full" role="img" aria-label={`${label} gauge`}>
    <!-- background arc -->
    <path
      d="M 10 50 A 40 40 0 0 1 90 50"
      fill="none"
      class="stroke-slate-200 dark:stroke-slate-700"
      stroke-width="10"
      stroke-linecap="round"
      pathLength="100"
    />

    <!-- foreground arc -->
    <path
      d="M 10 50 A 40 40 0 0 1 90 50"
      fill="none"
      class={arcClass}
      stroke-width="10"
      stroke-linecap="round"
      pathLength="100"
      stroke-dasharray={`${pct ?? 0} 100`}
    />

    <!-- ticks -->
    <g class="stroke-slate-300 dark:stroke-slate-600" stroke-width="1">
      <line x1="10" y1="50" x2="14" y2="50" />
      <line x1="30" y1="16" x2="32.5" y2="19" />
      <line x1="50" y1="10" x2="50" y2="14" />
      <line x1="70" y1="16" x2="67.5" y2="19" />
      <line x1="90" y1="50" x2="86" y2="50" />
    </g>

    <!-- needle -->
    <g transform={`rotate(${needleDeg} 50 50)`}>
      <line x1="50" y1="50" x2="16" y2="50" class="stroke-slate-900 dark:stroke-slate-100" stroke-width="2" stroke-linecap="round" />
    </g>
    <circle cx="50" cy="50" r="3" class="fill-slate-900 dark:fill-slate-100" />
  </svg>

  <div class="absolute inset-0 flex flex-col items-center justify-end pb-1">
    <div class="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</div>
    <div class="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-none">
      {pct === null ? '—' : `${pct}%`}
    </div>
  </div>
</div>
