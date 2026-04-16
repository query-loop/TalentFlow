<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { verifyMagicLink, error, loading } from '../../../stores/auth';
  import { onMount } from 'svelte';

  let verifying = true;
  let success = false;

  onMount(async () => {
    const token = $page.url.searchParams.get('token');

    if (!token) {
      error.set('No token provided');
      verifying = false;
      return;
    }

    try {
      const result = await verifyMagicLink(token);
      success = true;
      verifying = false;
      
      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        goto('/app');
      }, 2000);
    } catch (err) {
      verifying = false;
    }
  });
</script>

<div class="verify-container">
  <div class="verify-card">
    {#if verifying}
      <div class="verifying">
        <div class="spinner"></div>
        <h2>✨ Verifying your magic link...</h2>
        <p>Please wait while we authenticate you.</p>
      </div>
    {:else if success}
      <div class="success">
        <div class="success-icon">✓</div>
        <h2>🎉 Login Successful!</h2>
        <p>Welcome to TalentFlow</p>
        <p class="redirect-text">Redirecting you to the dashboard...</p>
      </div>
    {:else}
      <div class="error-state">
        <div class="error-icon">✕</div>
        <h2>⚠️ Login Failed</h2>
        <p class="error-detail">{$error || 'The magic link is invalid or has expired.'}</p>
        <a href="/auth/login" class="retry-link">Try Again</a>
        <p class="error-footer">Magic links expire after 15 minutes for security</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .verify-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  }

  .verify-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    width: 100%;
    max-width: 450px;
    padding: 50px;
    text-align: center;
    animation: slideIn 0.5s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .verifying,
  .success,
  .error-state {
    text-align: center;
  }

  .spinner {
    width: 50px;
    height: 50px;
    border: 4px solid #e2e8f0;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 24px;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  h2 {
    margin: 16px 0 12px 0;
    font-size: 26px;
    color: #1a202c;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  p {
    margin: 8px 0;
    color: #718096;
    font-size: 15px;
    line-height: 1.6;
  }

  .success-icon {
    font-size: 60px;
    color: #48bb78;
    margin-bottom: 16px;
    animation: scaleIn 0.5s ease-out;
  }

  @keyframes scaleIn {
    from {
      opacity: 0;
      transform: scale(0.5);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .success .redirect-text {
    color: #a0aec0;
    font-size: 13px;
    margin-top: 12px;
  }

  .error-icon {
    font-size: 60px;
    color: #f56565;
    margin-bottom: 16px;
    animation: shake 0.5s ease-in-out;
  }

  @keyframes shake {
    0%, 100% {
      transform: translateX(0);
    }
    25% {
      transform: translateX(-8px);
    }
    75% {
      transform: translateX(8px);
    }
  }

  .error-detail {
    color: #e53e3e;
    background: #fff5f5;
    padding: 14px;
    border-radius: 8px;
    margin: 16px 0;
    border-left: 4px solid #e53e3e;
    text-align: left;
    font-size: 14px;
  }

  .retry-link {
    display: inline-block;
    margin-top: 24px;
    padding: 12px 32px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .retry-link:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  }

  .error-footer {
    font-size: 12px;
    color: #a0aec0;
    margin-top: 16px;
  }
</style>
