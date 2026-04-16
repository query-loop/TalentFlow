<script lang="ts">
  import { user } from '../../../stores/auth';
</script>

<div class="dashboard-container">
  <div class="welcome-section">
    <h1>Welcome, {$user?.full_name || $user?.email || 'User'}!</h1>
    <p>Manage your talent recruitment and candidate pipelines</p>
  </div>

  <div class="dashboard-grid">
    <a href="/app/my-pipelines" class="dashboard-card">
      <div class="card-icon">📊</div>
      <h3>My Pipelines</h3>
      <p>View and manage all your recruitment pipelines</p>
    </a>

    <a href="/app/pipelines-v2" class="dashboard-card">
      <div class="card-icon">➕</div>
      <h3>Create Pipeline</h3>
      <p>Start a new recruitment pipeline with job descriptions</p>
    </a>

    <a href="/app/profile" class="dashboard-card">
      <div class="card-icon">👤</div>
      <h3>My Profile</h3>
      <p>Update your account information and preferences</p>
    </a>

    <a href="/app" class="dashboard-card">
      <div class="card-icon">📚</div>
      <h3>Resources</h3>
      <p>Access guides, templates, and learning materials</p>
    </a>
  </div>
</div>

<style>
  .dashboard-container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 40px 20px;
  }

  .welcome-section {
    margin-bottom: 50px;
    text-align: center;
  }

  .welcome-section h1 {
    margin: 0 0 10px;
    font-size: 32px;
    color: #333;
  }

  .welcome-section p {
    margin: 0;
    color: #666;
    font-size: 16px;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
  }

  .dashboard-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px 20px;
    background: white;
    border: 2px solid #f0f0f0;
    border-radius: 8px;
    text-decoration: none;
    color: inherit;
    transition: all 0.3s ease;
    cursor: pointer;
    text-align: center;
  }

  .dashboard-card:hover {
    border-color: #667eea;
    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.15);
    transform: translateY(-4px);
  }

  .card-icon {
    font-size: 40px;
    margin-bottom: 15px;
  }

  .dashboard-card h3 {
    margin: 0 0 10px;
    font-size: 18px;
    color: #333;
  }

  .dashboard-card p {
    margin: 0;
    color: #666;
    font-size: 14px;
  }

  @media (max-width: 600px) {
    .dashboard-container {
      padding: 20px;
    }

    .welcome-section h1 {
      font-size: 24px;
    }

    .dashboard-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
