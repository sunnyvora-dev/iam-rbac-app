/**
 * IAM & RBAC Browser Demo Application
 * Vanilla JS OpenID Connect (OIDC) Authorization Code Flow with PKCE S256.
 *
 * Trade-off: sessionStorage survives page refresh, but is accessible by XSS scripts.
 */

// Global Application State
let appConfig = {
  keycloakUrl: 'http://localhost:8080',
  realm: 'company',
  clientId: 'company-app'
};

let countdownInterval = null;

// --- UTILITY & CRYPTOGRAPHY FUNCTIONS (Web Crypto API) ---

/**
 * Converts ArrayBuffer to Base64URL string per PKCE spec.
 */
function bufferToBase64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let string = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    string += String.fromCharCode(bytes[i]);
  }
  return btoa(string)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Generates random 64-character string for PKCE code_verifier.
 */
function generateCodeVerifier() {
  const array = new Uint8Array(48);
  window.crypto.getRandomValues(array);
  return bufferToBase64Url(array);
}

/**
 * Computes S256 code_challenge = Base64URL(SHA-256(code_verifier)).
 */
async function generateCodeChallenge(codeVerifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  return bufferToBase64Url(digest);
}

/**
 * Generates random hex string for state and nonce parameters.
 */
function generateRandomString(length = 32) {
  const array = new Uint8Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Safely decodes base64url payload string without external libraries.
 */
function parseJwtPayload(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

// --- DOM MANIPULATION HELPERS (Strict textContent - No innerHTML) ---

function showError(title, message) {
  const banner = document.getElementById('error-banner');
  const titleEl = document.getElementById('error-title');
  const msgEl = document.getElementById('error-message');
  
  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;
  if (banner) banner.classList.remove('hidden');
}

function clearError() {
  const banner = document.getElementById('error-banner');
  if (banner) banner.classList.add('hidden');
}

// --- PKCE LOGIN & AUTHENTICATION FLOW ---

/**
 * Initiates Keycloak OIDC Authorization Code Flow with PKCE S256.
 */
async function initiatePkceLogin() {
  clearError();
  try {
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    const state = generateRandomString(16);
    const nonce = generateRandomString(16);

    // Save PKCE parameters in sessionStorage
    sessionStorage.setItem('pkce_code_verifier', codeVerifier);
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_nonce', nonce);

    const redirectUri = `${window.location.origin}/`;
    const authUrl = new URL(`${appConfig.keycloakUrl}/realms/${appConfig.realm}/protocol/openid-connect/auth`);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('client_id', appConfig.clientId);
    authUrl.searchParams.set('redirect_uri', redirectUri);
    authUrl.searchParams.set('scope', 'openid profile email');
    authUrl.searchParams.set('code_challenge', codeChallenge);
    authUrl.searchParams.set('code_challenge_method', 'S256');
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('nonce', nonce);

    window.location.href = authUrl.toString();
  } catch (e) {
    showError('PKCE Initialization Error', 'Failed to generate PKCE cryptographic parameters.');
  }
}

/**
 * Processes returning OIDC Authorization Code redirect.
 */
async function handleOidcCallback(code, state) {
  clearError();
  const savedState = sessionStorage.getItem('oauth_state');
  const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
  const savedNonce = sessionStorage.getItem('oauth_nonce');

  // Verify State to prevent CSRF attacks
  if (!state || state !== savedState) {
    showError('State Mismatch Error', 'Invalid authorization state. Potential CSRF attempt detected.');
    return;
  }

  if (!codeVerifier) {
    showError('PKCE Error', 'Missing code verifier in session storage.');
    return;
  }

  const redirectUri = `${window.location.origin}/`;
  const tokenUrl = `${appConfig.keycloakUrl}/realms/${appConfig.realm}/protocol/openid-connect/token`;

  const bodyParams = new URLSearchParams();
  bodyParams.set('grant_type', 'authorization_code');
  bodyParams.set('client_id', appConfig.clientId);
  bodyParams.set('code', code);
  bodyParams.set('code_verifier', codeVerifier);
  bodyParams.set('redirect_uri', redirectUri);

  let res;
  try {
    res = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: bodyParams
    });
  } catch (e) {
    showError('Network Error', 'Failed to connect to Keycloak token endpoint.');
    return;
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    showError('Token Exchange Failed', errData.error_description || 'Failed to exchange authorization code for tokens.');
    return;
  }

  try {
    const tokenData = await res.json();
    
    // Verify id_token nonce claim
    if (tokenData.id_token) {
      const idPayload = parseJwtPayload(tokenData.id_token);
      if (idPayload && idPayload.nonce !== savedNonce) {
        showError('Nonce Verification Failed', 'ID token nonce claim does not match session nonce.');
        return;
      }
    }

    // Store tokens in sessionStorage
    sessionStorage.setItem('access_token', tokenData.access_token);
    if (tokenData.id_token) sessionStorage.setItem('id_token', tokenData.id_token);

    // Clean OIDC query params from address bar
    history.replaceState({}, document.title, window.location.pathname);

    renderAuthenticatedApp();
  } catch (e) {
    console.error('Callback handling error:', e);
    showError('Callback Processing Error', e.message || 'An error occurred while processing authentication.');
  }
}

/**
 * Initiates Keycloak Logout.
 */
function handleLogout() {
  const idToken = sessionStorage.getItem('id_token');
  sessionStorage.clear();

  const logoutUrl = new URL(`${appConfig.keycloakUrl}/realms/${appConfig.realm}/protocol/openid-connect/logout`);
  logoutUrl.searchParams.set('client_id', appConfig.clientId);
  if (idToken) logoutUrl.searchParams.set('id_token_hint', idToken);
  logoutUrl.searchParams.set('post_logout_redirect_uri', `${window.location.origin}/`);

  window.location.href = logoutUrl.toString();
}

// --- APP UI RENDERERS ---

/**
 * Renders authenticated UI view and starts expiration timer.
 */
function renderAuthenticatedApp() {
  const token = sessionStorage.getItem('access_token');
  if (!token) {
    renderUnauthenticatedApp();
    return;
  }

  const payload = parseJwtPayload(token);
  if (!payload) {
    sessionStorage.clear();
    renderUnauthenticatedApp();
    return;
  }

  document.getElementById('logged-out-view').classList.add('hidden');
  document.getElementById('logged-in-view').classList.remove('hidden');

  // Populate User Information Card safely with textContent
  const nameEl = document.getElementById('user-name');
  const usernameEl = document.getElementById('user-username');
  const emailEl = document.getElementById('user-email');
  const rolesContainer = document.getElementById('user-roles');

  const givenName = payload.given_name || '';
  const familyName = payload.family_name || '';
  const fullName = `${givenName} ${familyName}`.trim() || payload.preferred_username || 'User';

  if (nameEl) nameEl.textContent = fullName;
  if (usernameEl) usernameEl.textContent = `@${payload.preferred_username || 'user'}`;
  if (emailEl) emailEl.textContent = payload.email || 'No email';

  // Render Role Badges safely
  const roles = payload.realm_access?.roles || [];
  if (rolesContainer) {
    rolesContainer.textContent = ''; // Clear container
    const appRoles = roles.filter(r => ['admin', 'manager', 'employee'].includes(r));
    const displayRoles = appRoles.length > 0 ? appRoles : ['none'];

    displayRoles.forEach(role => {
      const badge = document.createElement('span');
      badge.className = `badge badge-${role}`;
      badge.textContent = role;
      rolesContainer.appendChild(badge);
    });
  }

  // Start Live Token Countdown
  startTokenCountdown(payload.exp, roles);
}

/**
 * Renders unauthenticated UI view.
 */
function renderUnauthenticatedApp() {
  if (countdownInterval) clearInterval(countdownInterval);
  document.getElementById('logged-in-view').classList.add('hidden');
  document.getElementById('logged-out-view').classList.remove('hidden');
}

/**
 * Starts live 1-second countdown timer.
 */
function startTokenCountdown(expTimestamp, userRoles) {
  if (countdownInterval) clearInterval(countdownInterval);

  const countdownEl = document.getElementById('token-countdown');
  const expiryAlert = document.getElementById('expiry-alert');

  function update() {
    const now = Math.floor(Date.now() / 1000);
    const remaining = expTimestamp - now;

    if (remaining <= 0) {
      if (countdownEl) countdownEl.textContent = 'Token expires in 0:00';
      if (expiryAlert) expiryAlert.classList.remove('hidden');
      clearInterval(countdownInterval);
      return;
    }

    if (expiryAlert) expiryAlert.classList.add('hidden');
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    const formatted = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    if (countdownEl) countdownEl.textContent = `Token expires in ${formatted}`;
  }

  update();
  countdownInterval = setInterval(update, 1000);
}

// --- INTERACTIVE ENDPOINT & SECURITY TESTING ---

/**
 * Calculates expected HTTP status for current user roles.
 */
function getExpectedStatus(endpoint, userRoles) {
  if (endpoint === '/api/public') return 200;
  if (endpoint === '/api/profile') {
    return userRoles.some(r => ['admin', 'manager', 'employee'].includes(r)) ? 200 : 403;
  }
  if (endpoint === '/api/reports') {
    return userRoles.some(r => ['admin', 'manager'].includes(r)) ? 200 : 403;
  }
  if (endpoint === '/api/admin/users') {
    return userRoles.includes('admin') ? 200 : 403;
  }
  return 200;
}

/**
 * Executes API call and updates result UI card.
 */
async function callEndpoint(cardElement, url, tokenOverride = null, isNoToken = false) {
  const badgeEl = cardElement.querySelector('.status-badge');
  const jsonEl = cardElement.querySelector('.response-json');
  const timeEl = cardElement.querySelector('.response-time');
  const resultEl = cardElement.querySelector('.expectation-result');

  if (badgeEl) {
    badgeEl.className = 'status-badge badge-grey';
    badgeEl.textContent = 'Calling...';
  }
  if (jsonEl) jsonEl.textContent = 'Loading response...';

  const startTime = performance.now();
  const headers = {};

  if (!isNoToken) {
    const token = tokenOverride !== null ? tokenOverride : sessionStorage.getItem('access_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(url, { headers });
    const endTime = performance.now();
    const durationMs = Math.round(endTime - startTime);

    const status = res.status;
    let jsonText = '';
    try {
      const data = await res.json();
      jsonText = JSON.stringify(data, null, 2);
    } catch (e) {
      jsonText = await res.text();
    }

    if (badgeEl) {
      if (status >= 200 && status < 300) {
        badgeEl.className = 'status-badge badge-green';
        badgeEl.textContent = `${status} OK`;
      } else {
        badgeEl.className = 'status-badge badge-red';
        badgeEl.textContent = `${status} Error`;
      }
    }

    if (timeEl) timeEl.textContent = `Time: ${durationMs}ms`;
    if (jsonEl) jsonEl.textContent = jsonText;

    // Check expectation match
    const token = sessionStorage.getItem('access_token');
    const payload = token ? parseJwtPayload(token) : null;
    const userRoles = payload?.realm_access?.roles || [];
    
    // For security tests, expectation is 401
    const expected = cardElement.dataset.sec ? 401 : getExpectedStatus(url, userRoles);

    if (resultEl) {
      if (status === expected) {
        resultEl.className = 'expectation-result exp-match';
        resultEl.textContent = '✓ as expected';
      } else {
        resultEl.className = 'expectation-result exp-mismatch';
        resultEl.textContent = `⚠ expected ${expected}`;
      }
    }
  } catch (err) {
    if (badgeEl) {
      badgeEl.className = 'status-badge badge-red';
      badgeEl.textContent = 'Network Err';
    }
    if (jsonEl) jsonEl.textContent = `Network Error: ${err.message}`;
  }
}

// --- INITIALIZATION ---

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Fetch Application Configuration
  try {
    const configRes = await fetch('/config.json');
    if (configRes.ok) {
      const data = await configRes.json();
      appConfig = { ...appConfig, ...data };
    }
  } catch (e) {
    // Fallback to defaults
  }

  // 2. Attach Event Listeners
  const loginBtn = document.getElementById('login-btn');
  if (loginBtn) loginBtn.addEventListener('click', initiatePkceLogin);

  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

  // Endpoint Card Call Buttons
  document.querySelectorAll('.call-endpoint-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.endpoint-card');
      const url = btn.dataset.url;
      callEndpoint(card, url);
    });
  });

  // Security Attack Test Buttons
  document.querySelectorAll('.sec-test-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.sec-test-card');
      const testType = btn.dataset.type;

      if (testType === 'no-token') {
        callEndpoint(card, '/api/profile', null, true);
      } else if (testType === 'fake-token') {
        callEndpoint(card, '/api/profile', 'abc.def.ghi');
      } else if (testType === 'tampered-token') {
        const realToken = sessionStorage.getItem('access_token') || 'ey...';
        const tampered = realToken.length > 10 ? realToken.slice(0, -4) + 'AAAA' : 'invalid.signature.AAAA';
        callEndpoint(card, '/api/admin/users', tampered);
      }
    });
  });

  // 3. Handle OIDC Callback Redirect or Render App State
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');

  if (code && state) {
    await handleOidcCallback(code, state);
  } else if (sessionStorage.getItem('access_token')) {
    renderAuthenticatedApp();
  } else {
    renderUnauthenticatedApp();
  }
});
