<script lang="ts">
  export let jdData: {
    title?: string;
    company?: string;
    description?: string;
    url?: string;
    location?: string;
  } | null = null;
  
  export let compact = false;
  
  function formatJobDescription(text: string): string {
    if (!text) return '';
    
    // Clean up the text first
    let cleaned = text
      .replace(/\r\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    
    // Split into sections and format
    const sections = cleaned.split(/\n\s*\n/);
    const formatted = sections.map(section => {
      const lines = section.split('\n').map(line => line.trim()).filter(Boolean);
      if (lines.length === 0) return '';
      
      // Check if this looks like a section header
      const firstLine = lines[0];
      if (firstLine.length < 100 && (
        firstLine.match(/^[A-Z][a-z\s]+:?\s*$/) ||
        firstLine.includes('Requirements') ||
        firstLine.includes('Responsibilities') ||
        firstLine.includes('Qualifications') ||
        firstLine.includes('Benefits') ||
        firstLine.includes('About') ||
        firstLine.includes('Skills') ||
        firstLine.includes('Experience')
      )) {
        const content = lines.slice(1).join('\n');
        return `<h3 class="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-3 mt-6">${firstLine.replace(/:$/, '')}</h3>\n${formatContent(content)}`;
      }
      
      return formatContent(lines.join('\n'));
    }).filter(Boolean);
    
    return formatted.join('\n\n');
  }
  
  function formatContent(text: string): string {
    if (!text) return '';
    
    // Handle bullet points
    const lines = text.split('\n');
    let formatted = '';
    let inList = false;
    
    for (let line of lines) {
      line = line.trim();
      if (!line) {
        if (inList) {
          formatted += '</ul>\n';
          inList = false;
        }
        formatted += '\n';
        continue;
      }
      
      // Check if this is a bullet point
      if (line.match(/^[-•*]\s+/) || line.match(/^\d+\.\s+/)) {
        if (!inList) {
          formatted += '<ul class="list-disc pl-6 space-y-1 mb-4">\n';
          inList = true;
        }
        const content = line.replace(/^[-•*]\s+/, '').replace(/^\d+\.\s+/, '');
        formatted += `<li class="text-gray-700 dark:text-gray-300">${escapeHtml(content)}</li>\n`;
      } else {
        if (inList) {
          formatted += '</ul>\n';
          inList = false;
        }
        formatted += `<p class="text-gray-700 dark:text-gray-300 mb-4 leading-relaxed">${escapeHtml(line)}</p>\n`;
      }
    }
    
    if (inList) {
      formatted += '</ul>\n';
    }
    
    return formatted;
  }
  
  function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  function extractSummary(description: string): string {
    if (!description) return '';
    const sentences = description.split(/[.!?]+/).filter(s => s.trim().length > 10);
    return sentences.slice(0, 2).join('. ').trim() + (sentences.length > 2 ? '...' : '');
  }
  
  $: formattedDescription = jdData?.description ? formatJobDescription(jdData.description) : '';
</script>

{#if jdData}
  <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
    <!-- Header -->
    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            {jdData.title || 'Job Posting'}
          </h2>
          <div class="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
            {#if jdData.company}
              <div class="flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clip-rule="evenodd"/>
                </svg>
                <span class="font-medium">{jdData.company}</span>
              </div>
            {/if}
            {#if jdData.location}
              <div class="flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/>
                </svg>
                <span>{jdData.location}</span>
              </div>
            {/if}
            {#if jdData.url}
              <div class="flex items-center gap-1">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clip-rule="evenodd"/>
                </svg>
                <a href={jdData.url} target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 hover:underline">
                  View Original
                </a>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
    
    <!-- Content -->
    <div class="px-6 py-4">
      {#if compact && jdData.description}
        <div class="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
          {extractSummary(jdData.description)}
        </div>
        <button class="mt-2 text-xs text-blue-600 hover:text-blue-800 hover:underline" on:click={() => compact = false}>
          View Full Description
        </button>
      {:else if formattedDescription}
        <div class="prose prose-sm max-w-none dark:prose-invert">
          {@html formattedDescription}
        </div>
        {#if !compact}
          <button class="mt-4 text-xs text-gray-500 hover:text-gray-700 hover:underline" on:click={() => compact = true}>
            Collapse
          </button>
        {/if}
      {:else}
        <div class="text-gray-500 dark:text-gray-400 italic text-center py-8">
          No job description available
        </div>
      {/if}
    </div>
  </div>
{:else}
  <div class="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center">
    <svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clip-rule="evenodd"/>
    </svg>
    <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No Job Description</h3>
    <p class="text-gray-500 dark:text-gray-400">Job description will appear here once extracted.</p>
  </div>
{/if}

<style>
  :global(.prose h3) {
    @apply font-semibold text-lg text-gray-900 dark:text-gray-100 mb-3 mt-6;
  }
  :global(.prose p) {
    @apply text-gray-700 dark:text-gray-300 mb-4 leading-relaxed;
  }
  :global(.prose ul) {
    @apply list-disc pl-6 space-y-1 mb-4;
  }
  :global(.prose li) {
    @apply text-gray-700 dark:text-gray-300;
  }
</style>