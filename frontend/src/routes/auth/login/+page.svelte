<script lang="ts">
  import { goto } from '$app/navigation';
  import { sendMagicLink, error, loading } from '../../../stores/auth';

  let email = '';
  let submitted = false;

  async function handleSubmit(e: Event) {
    e.preventDefault();
    submitted = true;

    if (!email) {
      return;
    }

    try {
      await sendMagicLink(email);
      // Show success message
      submitted = false;
      email = '';
      alert('Magic link sent! Check your email to log in.');
    } catch (err) {
      // Error is handled in the store
    }
  }
</script>

<div class="auth-container">
  <div class="auth-card">
    <div class="auth-header">
      <h1>TalentFlow</h1>
      <p>Sign in with magic link</p>
    </div>

    <form on:submit={handleSubmit}>
      <div class="form-group">
        <label for="email">Email Address</label>
        <input
          type="email"
          id="email"
          bind:value={email}
          placeholder="you@example.com"
          required
          disabled={$loading}
        />
      </div>

      {#if $error}
        <div class="error-message">
          {$error}
        </div>
      {/if}

      <button type="submit" disabled={$loading || !email}>
        {$loading ? 'Sending...' : 'Send Magic Link'}
      </button>
    </form>

    <div class="auth-footer">
      <p>No account needed. We'll send a magic link to your email!</p>
    </div>
  </div>
</div>

<style>
  .auth-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
  }

  .auth-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 400px;
    padding: 40px;
  }

  .auth-header {
    text-align: center;
    margin-bottom: 30px;
  }

  .auth-header h1 {
    margin: 0 0 10px 0;
    font-size: 28px;
    color: #333;
  }

  .auth-header p {
    margin: 0;
    color: #666;
    font-size: 14px;
  }

  .form-group {
    margin-bottom: 20px;
  }

  label {
    display: block;
    margin-bottom: 8px;
    color: #333;
    font-weight: 500;
    font-size: 14px;
  }

  input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    box-sizing: border-box;
    transition: border-color 0.3s;
  }

  input:focus {
    outline: none;
    border-color: #667eea;
  }

  input:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }

  button {
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s;
    margin-top: 10px;
  }

  button:hover:not(:disabled) {
    transform: translateY(-2px);
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error-message {
    color: #d32f2f;
    background: #ffebee;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 15px;
    font-size: 14px;
  }

  .auth-footer {
    text-align: center;
    margin-top: 20px;
    color: #999;
    font-size: 12px;
  }

  .auth-footer p {
    margin: 0;
  }
</style>
