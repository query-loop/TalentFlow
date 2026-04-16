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
        <div class="spinner" />
        <h2>Verifying your magic link...</h2>
        <p>Please wait while we authenticate you.</p>
      </div>
    {:else if success}
      <div class="success">
        <div class="success-icon">✓</div>
        <h2>Login Successful!</h2>
        <p>Redirecting you to the dashboard...</p>
      </div>
    {:else}
      <div class="error-state">
        <div class="error-icon">✕</div>
        <h2>Login Failed</h2>
        <p>{$error || 'The magic link is invalid or has expired.'}</p>
        <a href="/auth/login" class="retry-link">Try again</a>
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
  }

  .verify-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 400px;
    padding: 40px;
    text-align: center;
  }

  .verifying,
  .success,
  .error-state {
    text-align: center;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f0f0f0;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
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
    margin: 20px 0 10px;
    color: #333;
    font-size: 20px;
  }

  p {
    color: #666;
    font-size: 14px;
    margin: 0 0 15px;
  }

  .success-icon {
    font-size: 48px;
    color: #4caf50;
    margin-bottom: 10px;
  }

  .error-icon {
    font-size: 48px;
    color: #d32f2f;
    margin-bottom: 10px;
  }

  .retry-link {
    display: inline-block;
    margin-top: 20px;
    padding: 10px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 14px;
    transition: transform 0.2s;
  }

  .retry-link:hover {
    transform: translateY(-2px);
  }
</style>
