<script lang="ts">
  import Icon from '$lib/Icon.svelte';
  
  export let resumeText: string = '';
  export let filename: string = 'Resume';
  export let score: any = null;
  export let onReanalyze: (() => void) | null = null;
  
  let showFullText = false;
  
  function getScoreColor(score: number): string {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  }
  
  function getScoreBgColor(score: number): string {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/20';
    if (score >= 60) return 'bg-yellow-100 dark:bg-yellow-900/20';
    return 'bg-red-100 dark:bg-red-900/20';
  }
</script>

<div class="space-y-4">
  <!-- Resume Header -->
  <div class="flex items-center justify-between p-3 bg-white/80 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 rounded-lg">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
        <Icon name="file-text" size={20} class="text-blue-600 dark:text-blue-400" />
      </div>
      <div>
        <div class="font-medium text-sm">{filename}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">
          {resumeText.length} characters
        </div>
      </div>
    </div>
    <button
      on:click={() => showFullText = !showFullText}
      class="text-xs px-3 py-1.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
    >
      {showFullText ? 'Hide' : 'Show'} Full Text
    </button>
  </div>

  <!-- Resume Text (Collapsible) -->
  {#if showFullText}
    <div class="p-4 bg-white/50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg max-h-96 overflow-y-auto">
      <pre class="text-xs whitespace-pre-wrap font-mono text-gray-700 dark:text-gray-300">{resumeText}</pre>
    </div>
  {/if}

  <!-- Scoring Section -->
  {#if score}
    <div class="space-y-3">
      <!-- Overall Score -->
      <div class="p-4 bg-white/80 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 rounded-lg">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-sm">Match Analysis</h3>
          {#if onReanalyze}
            <button
              on:click={onReanalyze}
              class="text-xs px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition"
            >
              <Icon name="refresh-cw" size={12} class="inline mr-1" />
              Reanalyze
            </button>
          {/if}
        </div>
        
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <div class="text-center p-3 rounded-lg {getScoreBgColor(score.overall_score)}">
            <div class="text-2xl font-bold {getScoreColor(score.overall_score)}">{score.overall_score}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">Overall</div>
          </div>
          <div class="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{score.skills_score}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">Skills</div>
          </div>
          <div class="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{score.keywords_score}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">Keywords</div>
          </div>
          <div class="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{score.experience_score}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">Experience</div>
          </div>
          <div class="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{score.education_score}%</div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">Education</div>
          </div>
        </div>

        <!-- Matched Skills -->
        {#if score.matched_skills && score.matched_skills.length > 0}
          <div class="mb-3">
            <div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
              <Icon name="check-circle" size={14} class="text-green-600 dark:text-green-400" />
              Matched Skills ({score.matched_skills.length})
            </div>
            <div class="flex flex-wrap gap-1.5">
              {#each score.matched_skills as skill}
                <span class="text-xs px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800">
                  {skill}
                </span>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Missing Skills -->
        {#if score.missing_skills && score.missing_skills.length > 0}
          <div class="mb-3">
            <div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
              <Icon name="alert-circle" size={14} class="text-orange-600 dark:text-orange-400" />
              Missing Skills ({score.missing_skills.length})
            </div>
            <div class="flex flex-wrap gap-1.5">
              {#each score.missing_skills.slice(0, 10) as skill}
                <span class="text-xs px-2 py-1 rounded-full bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800">
                  {skill}
                </span>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Strengths -->
        {#if score.strengths && score.strengths.length > 0}
          <div class="mb-3">
            <div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
              <Icon name="star" size={14} class="text-blue-600 dark:text-blue-400" />
              Strengths
            </div>
            <ul class="space-y-1">
              {#each score.strengths as strength}
                <li class="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                  <span class="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                  <span>{strength}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        <!-- Gaps -->
        {#if score.gaps && score.gaps.length > 0}
          <div class="mb-3">
            <div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
              <Icon name="x-circle" size={14} class="text-red-600 dark:text-red-400" />
              Gaps to Address
            </div>
            <ul class="space-y-1">
              {#each score.gaps as gap}
                <li class="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                  <span class="text-red-600 dark:text-red-400 mt-0.5">•</span>
                  <span>{gap}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        <!-- Recommendations -->
        {#if score.recommendations && score.recommendations.length > 0}
          <div>
            <div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
              <Icon name="lightbulb" size={14} class="text-purple-600 dark:text-purple-400" />
              Recommendations
            </div>
            <ul class="space-y-1.5">
              {#each score.recommendations as rec}
                <li class="text-xs text-gray-600 dark:text-gray-400 p-2 rounded bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800">
                  {rec}
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="p-4 bg-white/50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg text-center text-sm text-gray-500 dark:text-gray-400">
      No scoring analysis available yet
    </div>
  {/if}
</div>
