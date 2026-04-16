import { writable } from 'svelte/store';

export const token = writable<string | null>(null);
export const user = writable<any>(null);
export const isAuthenticated = writable(false);
export const loading = writable(false);
export const error = writable<string | null>(null);

// Subscribe to token and persist to localStorage
token.subscribe((value) => {
  if (typeof window !== 'undefined') {
    if (value) {
      localStorage.setItem('authToken', value);
    } else {
      localStorage.removeItem('authToken');
    }
  }
});

// API base URL - use relative path for proxy in dev
const API_BASE = import.meta.env.VITE_API_URL || '';

export async function sendMagicLink(email: string) {
  loading.set(true);
  error.set(null);

  try {
    const response = await fetch(`${API_BASE}/api/auth/send-magic-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to send magic link');
    }

    return await response.json();
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'An error occurred';
    error.set(errorMessage);
    throw err;
  } finally {
    loading.set(false);
  }
}

export async function verifyMagicLink(magicToken: string) {
  loading.set(true);
  error.set(null);

  try {
    const response = await fetch(`${API_BASE}/api/auth/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ token: magicToken })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to verify magic link');
    }

    const data = await response.json();
    
    // Set auth state
    if (data.access_token) {
      token.set(data.access_token);
      isAuthenticated.set(true);
    }
    
    if (data.user) {
      user.set(data.user);
    }

    return data;
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'An error occurred';
    error.set(errorMessage);
    throw err;
  } finally {
    loading.set(false);
  }
}

export function logout() {
  token.set(null);
  user.set(null);
  isAuthenticated.set(false);
  error.set(null);
}
