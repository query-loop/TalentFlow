<script lang="ts">
  import { onMount } from 'svelte';
  import { user, token } from '../../../stores/auth';

  const API_BASE = 'http://localhost:9002';

  interface Pipeline {
    id: number;
    name: string;
    company: string;
    created_at: string;
    status: string;
  }

  let pipelines: Pipeline[] = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    try {
      const authToken = localStorage.getItem('authToken');
      if (!authToken) {
        error = 'Not authenticated';
        return;
      }

      const response = await fetch(`${API_BASE}/api/pipelines-v2`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch pipelines');
      }

      const data = await response.json();
      pipelines = data.pipelines || [];
    } catch (err) {
      error = 'Error loading pipelines';
      console.error(err);
    } finally {
      loading = false;
    }
  });

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString();
  }
</script>

<div class="pipelines-container">
  <div class="pipelines-header">
    <h1>My Pipelines</h1>
    <p>Manage your recruitment pipelines and track candidate progress</p>
  </div>

  {#if loading}
    <div class="loading">Loading pipelines...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if pipelines.length === 0}
    <div class="no-pipelines">
      <p>No pipelines yet</p>
      <a href="/app/pipelines-v2" class="create-button">Create Your First Pipeline</a>
    </div>
  {:else}
    <div class="pipelines-grid">
      {#each pipelines as pipeline}
        <div class="pipeline-card">
          <div class="pipeline-header">
            <h3>{pipeline.name}</h3>
            <span class="status-badge" class:active={pipeline.status === 'active'}>
              {pipeline.status}
            </span>
          </div>
          <div class="pipeline-details">
            <p><strong>Company:</strong> {pipeline.company || 'N/A'}</p>
            <p><strong>Created:</strong> {formatDate(pipeline.created_at)}</p>
          </div>
          <div class="pipeline-actions">
            <a href={`/app/pipelines-v2?id=${pipeline.id}`} class="action-link">
              View Details
            </a>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .pipelines-container {
    max-width: 1000px;
    margin: 0 auto;
  }

  .pipelines-header {
    margin-bottom: 40px;
  }

  .pipelines-header h1 {
    margin: 0 0 10px;
    font-size: 28px;
    color: #333;
  }

  .pipelines-header p {
    margin: 0;
    color: #666;
    font-size: 14px;
  }

  .loading,
  .error {
    padding: 30px;
    text-align: center;
    background: white;
    border-radius: 8px;
    border: 1px solid #ddd;
  }

  .error {
    color: #d32f2f;
    background: #ffebee;
    border-color: #ef5350;
  }

  .no-pipelines {
    text-align: center;
    padding: 60px 30px;
    background: white;
    border-radius: 8px;
    border: 2px dashed #ddd;
  }

  .no-pipelines p {
    color: #999;
    margin: 0 0 20px;
    font-size: 16px;
  }

  .create-button {
    display: inline-block;
    padding: 12px 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 600;
    transition: transform 0.2s;
  }

  .create-button:hover {
    transform: translateY(-2px);
  }

  .pipelines-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
  }

  .pipeline-card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    transition: all 0.3s;
  }

  .pipeline-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    border-color: #667eea;
  }

  .pipeline-header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 15px;
  }

  .pipeline-header h3 {
    margin: 0;
    font-size: 18px;
    color: #333;
  }

  .status-badge {
    display: inline-block;
    padding: 4px 12px;
    background: #f0f0f0;
    color: #666;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .status-badge.active {
    background: #e8f5e9;
    color: #2e7d32;
  }

  .pipeline-details {
    margin-bottom: 15px;
  }

  .pipeline-details p {
    margin: 8px 0;
    font-size: 14px;
    color: #666;
  }

  .pipeline-details strong {
    color: #333;
  }

  .pipeline-actions {
    display: flex;
    gap: 10px;
  }

  .action-link {
    flex: 1;
    padding: 8px 12px;
    background: #f5f5f5;
    color: #667eea;
    text-align: center;
    text-decoration: none;
    border-radius: 4px;
    font-size: 12px;
    transition: background 0.3s;
  }

  .action-link:hover {
    background: #667eea;
    color: white;
  }

  @media (max-width: 600px) {
    .pipelines-grid {
      grid-template-columns: 1fr;
    }

    .pipelines-header h1 {
      font-size: 24px;
    }
  }
</style>
