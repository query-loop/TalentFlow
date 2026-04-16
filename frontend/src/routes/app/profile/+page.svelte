<script lang="ts">
  import { user } from '../../../stores/auth';

  const API_BASE = 'http://localhost:9002';

  let fullName = '';
  let email = '';
  let saving = false;
  let message = '';

  $: if ($user) {
    email = $user.email;
    fullName = $user.full_name || '';
  }

  async function updateProfile() {
    saving = true;
    message = '';

    try {
      // Call profile update API
      const token = localStorage.getItem('authToken');
      const response = await fetch(`${API_BASE}/api/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ full_name: fullName })
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      const data = await response.json();
      user.set(data);
      message = 'Profile updated successfully!';
    } catch (err) {
      message = 'Error updating profile';
    } finally {
      saving = false;
    }
  }
</script>

<div class="profile-container">
  <div class="profile-card">
    <h1>My Profile</h1>

    <div class="form-group">
      <label for="email">Email</label>
      <input type="email" id="email" value={email} disabled />
    </div>

    <div class="form-group">
      <label for="fullName">Full Name</label>
      <input
        type="text"
        id="fullName"
        bind:value={fullName}
        placeholder="Enter your full name"
      />
    </div>

    {#if message}
      <div class="message" class:success={message.includes('successfully')}>
        {message}
      </div>
    {/if}

    <button on:click={updateProfile} disabled={saving} class="save-button">
      {saving ? 'Saving...' : 'Save Changes'}
    </button>
  </div>
</div>

<style>
  .profile-container {
    display: flex;
    justify-content: center;
    padding: 40px 20px;
  }

  .profile-card {
    background: white;
    border-radius: 8px;
    padding: 40px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    width: 100%;
    max-width: 500px;
  }

  h1 {
    margin-top: 0;
    color: #333;
    margin-bottom: 30px;
  }

  .form-group {
    margin-bottom: 20px;
  }

  label {
    display: block;
    margin-bottom: 8px;
    color: #333;
    font-weight: 500;
  }

  input {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    box-sizing: border-box;
  }

  input:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }

  .save-button {
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
    margin-top: 20px;
  }

  .save-button:hover:not(:disabled) {
    transform: translateY(-2px);
  }

  .save-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .message {
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 15px;
    font-size: 14px;
  }

  .message.success {
    background: #e8f5e9;
    color: #2e7d32;
  }

  .message:not(.success) {
    background: #ffebee;
    color: #c62828;
  }
</style>
