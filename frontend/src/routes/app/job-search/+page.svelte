/**
 * Svelte component for RapidAPI job search integration
 * Professional job search interface with multiple provider support
 */

<script lang="ts">
  import { onMount } from 'svelte';
  import { RapidAPIJobClient, type StandardizedJob, type JobSearchQuery } from '$lib/rapidapi-jobs';
  import Icon from '$lib/Icon.svelte';

  let searchQuery = '';
  let location = '';
  let jobType = '';
  let remoteOnly = false;
  let jobs: StandardizedJob[] = [];
  let loading = false;
  let error: string | null = null;
  let totalFound = 0;
  let providersUsed: string[] = [];
  let selectedProviders: string[] = ['jsearch'];
  let availableProviders: any[] = [];

  const client = new RapidAPIJobClient('/api/rapidapi-jobs');

  const jobTypes = [
    { value: '', label: 'Any' },
    { value: 'full-time', label: 'Full-time' },
    { value: 'part-time', label: 'Part-time' },
    { value: 'contract', label: 'Contract' },
    { value: 'internship', label: 'Internship' }
  ];

  onMount(async () => {
    try {
      const providers = await client.getProviders();
      availableProviders = providers.availableProviders;
    } catch (err) {
      console.warn('Failed to load providers:', err);
    }
  });

  async function handleSearch() {
    if (!searchQuery.trim()) {
      error = 'Please enter a search query';
      return;
    }

    loading = true;
    error = null;
    jobs = [];

    try {
      const searchParams: JobSearchQuery = {
        query: searchQuery.trim(),
        location: location.trim() || undefined,
        jobType: jobType || undefined,
        remoteOnly,
        limit: 25,
        providers: selectedProviders.length > 0 ? selectedProviders : undefined
      };

      const results = await client.searchJobs(searchParams);
      
      jobs = results.jobs;
      totalFound = results.totalFound;
      providersUsed = results.providersUsed;
      
    } catch (err: any) {
      error = err.message || 'Search failed';
      jobs = [];
      totalFound = 0;
      providersUsed = [];
    } finally {
      loading = false;
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  function formatSalary(job: StandardizedJob): string {
    if (job.salaryMin && job.salaryMax) {
      const currency = job.currency || 'USD';
      return `${job.salaryMin.toLocaleString()} - ${job.salaryMax.toLocaleString()} ${currency}`;
    } else if (job.salaryMin) {
      const currency = job.currency || 'USD';
      return `${job.salaryMin.toLocaleString()}+ ${currency}`;
    }
    return 'Salary not specified';
  }

  function formatDate(dateString: string | undefined): string {
    if (!dateString) return 'Date not available';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch {
      return dateString;
    }
  }

  function truncateDescription(description: string, maxLength: number = 200): string {
    if (description.length <= maxLength) return description;
    return description.substring(0, maxLength) + '...';
  }
</script>

<div class="p-6 max-w-6xl mx-auto">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
      Job Search
    </h1>
    <p class="text-slate-600 dark:text-slate-400">
      Search for jobs across multiple providers using RapidAPI
    </p>
  </div>

  <!-- Search Form -->
  <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6 mb-6">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      <div>
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Search Query
        </label>
        <input
          type="text"
          bind:value={searchQuery}
          on:keypress={handleKeyPress}
          placeholder="e.g., software engineer, data scientist"
          class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Location
        </label>
        <input
          type="text"
          bind:value={location}
          on:keypress={handleKeyPress}
          placeholder="e.g., San Francisco, CA"
          class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Job Type
        </label>
        <select
          bind:value={jobType}
          class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {#each jobTypes as type}
            <option value={type.value}>{type.label}</option>
          {/each}
        </select>
      </div>

      <div class="flex items-end">
        <label class="flex items-center space-x-2">
          <input
            type="checkbox"
            bind:checked={remoteOnly}
            class="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm text-slate-700 dark:text-slate-300">Remote only</span>
        </label>
      </div>
    </div>

    <!-- Provider Selection -->
    {#if availableProviders.length > 0}
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Data Providers
        </label>
        <div class="flex flex-wrap gap-3">
          {#each availableProviders as provider}
            <label class="flex items-center space-x-2">
              <input
                type="checkbox"
                value={provider.id}
                bind:group={selectedProviders}
                class="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
              />
              <span class="text-sm text-slate-700 dark:text-slate-300">
                {provider.name}
                <span class="text-xs text-slate-500">({provider.freeTierLimit}/month)</span>
              </span>
            </label>
          {/each}
        </div>
      </div>
    {/if}

    <button
      on:click={handleSearch}
      disabled={loading || !searchQuery.trim()}
      class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
    >
      {#if loading}
        <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
        </svg>
        Searching...
      {:else}
        <Icon name="search" size={16} />
        Search Jobs
      {/if}
    </button>
  </div>

  <!-- Results Summary -->
  {#if totalFound > 0 || providersUsed.length > 0}
    <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-medium text-blue-800 dark:text-blue-200">
            Search Results
          </h3>
          <p class="text-sm text-blue-700 dark:text-blue-300">
            Found {totalFound} jobs from {providersUsed.join(', ')}
          </p>
        </div>
        <Icon name="info" size={20} class="text-blue-600" />
      </div>
    </div>
  {/if}

  <!-- Error Display -->
  {#if error}
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
      <div class="flex items-center gap-2">
        <Icon name="alert-circle" size={16} class="text-red-600" />
        <span class="text-sm font-medium text-red-800 dark:text-red-200">Error</span>
      </div>
      <p class="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
    </div>
  {/if}

  <!-- Jobs List -->
  {#if jobs.length > 0}
    <div class="space-y-4">
      {#each jobs as job}
        <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6 hover:shadow-md transition-shadow">
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                {job.title}
              </h3>
              <div class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 mb-2">
                <span class="font-medium">{job.company}</span>
                <span>•</span>
                <span>{job.location}</span>
                {#if job.remote}
                  <span class="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded text-xs">
                    Remote
                  </span>
                {/if}
              </div>
              <div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                <span>{formatSalary(job)}</span>
                <span>•</span>
                <span>Posted: {formatDate(job.postedDate)}</span>
                <span>•</span>
                <span class="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded">
                  {job.source}
                </span>
              </div>
            </div>
          </div>

          <p class="text-sm text-slate-700 dark:text-slate-300 mb-4 leading-relaxed">
            {truncateDescription(job.description)}
          </p>

          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              {#if job.jobType}
                <span class="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded text-xs">
                  {job.jobType}
                </span>
              {/if}
            </div>

            <div class="flex items-center gap-2">
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm flex items-center gap-1 transition-colors"
              >
                Apply Now
                <Icon name="external-link" size={14} />
              </a>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else if !loading && searchQuery && !error}
    <div class="text-center py-12">
      <Icon name="search" size={48} class="mx-auto text-slate-400 mb-4" />
      <h3 class="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
        No jobs found
      </h3>
      <p class="text-slate-600 dark:text-slate-400">
        Try adjusting your search terms or filters
      </p>
    </div>
  {/if}

  <!-- Loading State -->
  {#if loading}
    <div class="text-center py-12">
      <svg class="animate-spin h-8 w-8 mx-auto text-blue-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
      </svg>
      <p class="text-slate-600 dark:text-slate-400">Searching for jobs...</p>
    </div>
  {/if}
</div>