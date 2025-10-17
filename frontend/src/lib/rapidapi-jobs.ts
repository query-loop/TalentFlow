/**
 * JavaScript/TypeScript client for RapidAPI job search endpoints
 * Provides frontend integration for real-time job data retrieval
 */

interface JobSearchQuery {
  query: string;
  location?: string;
  jobType?: string;
  remoteOnly?: boolean;
  datePosted?: string;
  limit?: number;
  providers?: string[];
}

interface StandardizedJob {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  salaryMin?: number;
  salaryMax?: number;
  currency?: string;
  jobType?: string;
  remote: boolean;
  postedDate?: string;
  applyUrl?: string;
  source: string;
}

interface JobSearchResponse {
  jobs: StandardizedJob[];
  totalFound: number;
  providersUsed: string[];
  queryInfo: any;
}

interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  freeTierLimit: number;
  rateLimit: number;
  features: string[];
}

class RapidAPIJobClient {
  private baseUrl: string;
  private headers: HeadersInit;

  constructor(baseUrl: string = '/api/rapidapi-jobs') {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Search for jobs using GET request
   */
  async searchJobs(params: JobSearchQuery): Promise<JobSearchResponse> {
    const url = new URL(`${this.baseUrl}/search`, window.location.origin);
    
    // Add query parameters
    url.searchParams.append('query', params.query);
    if (params.location) url.searchParams.append('location', params.location);
    if (params.jobType) url.searchParams.append('job_type', params.jobType);
    if (params.remoteOnly) url.searchParams.append('remote_only', 'true');
    if (params.datePosted) url.searchParams.append('date_posted', params.datePosted);
    if (params.limit) url.searchParams.append('limit', params.limit.toString());
    if (params.providers) url.searchParams.append('providers', params.providers.join(','));

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Search for jobs using POST request (supports more complex queries)
   */
  async searchJobsAdvanced(query: JobSearchQuery): Promise<JobSearchResponse> {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        query: query.query,
        location: query.location,
        job_type: query.jobType,
        remote_only: query.remoteOnly || false,
        date_posted: query.datePosted,
        limit: query.limit || 10,
        providers: query.providers,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Get details for a specific job
   */
  async getJobDetails(jobId: string, provider: string = 'jsearch'): Promise<StandardizedJob> {
    const url = `${this.baseUrl}/job/${jobId}?provider=${provider}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: this.headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.job;
  }

  /**
   * Get available providers and their information
   */
  async getProviders(): Promise<{ availableProviders: ProviderInfo[]; recommendations: any }> {
    const response = await fetch(`${this.baseUrl}/providers`, {
      method: 'GET',
      headers: this.headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Check service health
   */
  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`, {
      method: 'GET',
      headers: this.headers,
    });

    if (!response.ok) {
      throw new Error(`Health check failed: HTTP ${response.status}`);
    }

    return response.json();
  }
}

// Usage examples
class JobSearchExamples {
  private client: RapidAPIJobClient;

  constructor() {
    this.client = new RapidAPIJobClient();
  }

  /**
   * Basic job search example
   */
  async basicSearch(): Promise<void> {
    try {
      const results = await this.client.searchJobs({
        query: 'software engineer',
        location: 'San Francisco, CA',
        jobType: 'full-time',
        limit: 20,
      });

      console.log(`Found ${results.totalFound} jobs from providers: ${results.providersUsed.join(', ')}`);
      
      results.jobs.forEach((job, index) => {
        console.log(`${index + 1}. ${job.title} at ${job.company}`);
        console.log(`   Location: ${job.location}`);
        console.log(`   Remote: ${job.remote ? 'Yes' : 'No'}`);
        if (job.salaryMin && job.salaryMax) {
          console.log(`   Salary: ${job.salaryMin} - ${job.salaryMax} ${job.currency || 'USD'}`);
        }
        console.log(`   Apply: ${job.applyUrl}`);
        console.log('---');
      });
    } catch (error) {
      console.error('Job search failed:', error);
    }
  }

  /**
   * Advanced search with multiple providers
   */
  async advancedSearch(): Promise<void> {
    try {
      const results = await this.client.searchJobsAdvanced({
        query: 'python developer',
        location: 'Remote',
        jobType: 'full-time',
        remoteOnly: true,
        datePosted: 'week',
        limit: 30,
        providers: ['jsearch', 'jobs-api'],
      });

      // Group jobs by source
      const jobsBySource = results.jobs.reduce((acc, job) => {
        if (!acc[job.source]) acc[job.source] = [];
        acc[job.source].push(job);
        return acc;
      }, {} as Record<string, StandardizedJob[]>);

      Object.entries(jobsBySource).forEach(([source, jobs]) => {
        console.log(`\n${source}: ${jobs.length} jobs`);
        jobs.slice(0, 5).forEach(job => {
          console.log(`  - ${job.title} at ${job.company}`);
        });
      });
    } catch (error) {
      console.error('Advanced search failed:', error);
    }
  }

  /**
   * Get detailed job information
   */
  async getJobDetails(jobId: string): Promise<void> {
    try {
      const job = await this.client.getJobDetails(jobId);
      
      console.log('Job Details:');
      console.log(`Title: ${job.title}`);
      console.log(`Company: ${job.company}`);
      console.log(`Location: ${job.location}`);
      console.log(`Type: ${job.jobType}`);
      console.log(`Remote: ${job.remote ? 'Yes' : 'No'}`);
      console.log(`Posted: ${job.postedDate}`);
      console.log(`Description: ${job.description.substring(0, 200)}...`);
      console.log(`Apply URL: ${job.applyUrl}`);
    } catch (error) {
      console.error('Failed to get job details:', error);
    }
  }

  /**
   * Check available providers
   */
  async listProviders(): Promise<void> {
    try {
      const providers = await this.client.getProviders();
      
      console.log('Available Providers:');
      providers.availableProviders.forEach(provider => {
        console.log(`\n${provider.name} (${provider.id})`);
        console.log(`  Description: ${provider.description}`);
        console.log(`  Free Tier: ${provider.freeTierLimit} requests/month`);
        console.log(`  Rate Limit: ${provider.rateLimit} requests/minute`);
        console.log(`  Features: ${provider.features.join(', ')}`);
      });

      console.log('\nRecommendations:');
      Object.entries(providers.recommendations).forEach(([category, info]: [string, any]) => {
        console.log(`\n${category}: ${info.provider}`);
        console.log(`  Reason: ${info.reason}`);
        console.log(`  Features: ${info.features.join(', ')}`);
      });
    } catch (error) {
      console.error('Failed to get providers:', error);
    }
  }
}

// React Hook example
function useJobSearch() {
  const [jobs, setJobs] = React.useState<StandardizedJob[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const client = React.useMemo(() => new RapidAPIJobClient(), []);

  const searchJobs = React.useCallback(async (query: JobSearchQuery) => {
    setLoading(true);
    setError(null);
    
    try {
      const results = await client.searchJobs(query);
      setJobs(results.jobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, [client]);

  return { jobs, loading, error, searchJobs };
}

// Export for use in applications
export {
  RapidAPIJobClient,
  JobSearchExamples,
  useJobSearch,
  type JobSearchQuery,
  type StandardizedJob,
  type JobSearchResponse,
  type ProviderInfo,
};

// Example usage in browser console:
// const examples = new JobSearchExamples();
// examples.basicSearch();
// examples.advancedSearch();
// examples.listProviders();