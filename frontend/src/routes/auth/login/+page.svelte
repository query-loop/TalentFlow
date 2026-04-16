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
  <div class="auth-wrapper">
    <div class="auth-card">
      <div class="auth-header">
        <div class="logo">✨</div>
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
            autofocus
          />
        </div>

        {#if $error}
          <div class="error-message">
            <span class="error-icon">⚠️</span>
            {$error}
          </div>
        {/if}

        <button type="submit" disabled={$loading || !email} class="submit-button">
          {#if $loading}
            <span class="spinner"></span>
            Sending...
          {:else}
            <span>✉️</span>
            Send Magic Link
          {/if}
        </button>

        <div class="divider">
          <span>or</span>
        </div>

        <a href="/" class="back-link">Back to Home</a>
      </form>

      <div class="auth-footer">
        <p>🔐 No password needed</p>
        <p>We'll send a secure magic link to your email that expires in 15 minutes</p>
      </div>
    </div>

    <div class="auth-info">
      <div class="info-card">
        <div class="info-icon">🚀</div>
        <h3>Quick Setup</h3>
        <p>Log in in seconds with just your email</p>
      </div>
      <div class="info-card">
        <div class="info-icon">🔒</div>
        <h3>Secure</h3>
        <p>Industry-leading security and encryption</p>
      </div>
      <div class="info-card">
        <div class="info-icon">📧</div>
        <h3>Email Only</h3>
        <p>No passwords to remember or manage</p>
      </div>
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
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  }

  .auth-wrapper {
    width: 100%;
    max-width: 1000px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    align-items: center;
  }

  @media (max-width: 768px) {
    .auth-wrapper {
      grid-template-columns: 1fr;
      gap: 20px;
    }

    .auth-info {
      display: none;
    }
  }

  .auth-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    padding: 50px;
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

  .auth-header {
    text-align: center;
    margin-bottom: 40px;
  }

  .logo {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .auth-header h1 {
    margin: 0 0 8px 0;
    font-size: 32px;
    font-weight: 700;
    color: #1a202c;
    letter-spacing: -0.5px;
  }

  .auth-header p {
    margin: 0;
    color: #718096;
    font-size: 15px;
    font-weight: 500;
  }

  form {
    width: 100%;
  }

  .form-group {
    margin-bottom: 24px;
  }

  label {
    display: block;
    margin-bottom: 8px;
    color: #2d3748;
    font-weight: 600;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 15px;
    box-sizing: border-box;
    transition: all 0.3s ease;
    background: #f7fafc;
  }

  input:focus {
    outline: none;
    border-color: #667eea;
    background: white;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  input:disabled {
    background: #edf2f7;
    cursor: not-allowed;
    opacity: 0.7;
  }

  input::placeholder {
    color: #a0aec0;
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: #fff5f5;
    border: 1px solid #feb2b2;
    border-radius: 8px;
    margin-bottom: 20px;
    color: #c53030;
    font-size: 14px;
    animation: shake 0.3s ease-in-out;
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-5px); }
    75% { transform: translateX(5px); }
  }

  .error-icon {
    font-size: 18px;
    flex-shrink: 0;
  }

  .submit-button {
    width: 100%;
    padding: 14px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    margin-bottom: 16px;
  }

  .submit-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  }

  .submit-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .submit-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 24px 0;
    color: #a0aec0;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .divider::before,
  .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e2e8f0;
  }

  .back-link {
    display: block;
    text-align: center;
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    padding: 12px;
    border-radius: 8px;
    transition: all 0.3s ease;
    background: #f7fafc;
  }

  .back-link:hover {
    background: #edf2f7;
    color: #764ba2;
  }

  .auth-footer {
    text-align: center;
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid #e2e8f0;
  }

  .auth-footer p {
    margin: 6px 0;
    color: #718096;
    font-size: 13px;
    line-height: 1.6;
  }

  .auth-footer p:first-child {
    font-weight: 600;
    color: #2d3748;
  }

  .auth-info {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .info-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    color: white;
    animation: fadeIn 0.6s ease-out 0.2s both;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .info-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }

  .info-card h3 {
    margin: 0 0 8px 0;
    font-size: 18px;
    font-weight: 700;
  }

  .info-card p {
    margin: 0;
    font-size: 14px;
    opacity: 0.9;
    line-height: 1.5;
  }
</style>
