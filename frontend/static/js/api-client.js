/* Same-origin frontend client. Mutations use the server session and CSRF token. */
let csrfToken = null;

export async function api(path, {
  method = 'GET',
  body
} = {}) {
  const url = new URL(path, window.location.origin);
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/v1/')) {
    throw new Error('Use a same-origin /api/v1/ URL.');
  }
  const headers = {
    Accept: 'application/json'
  };
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
    if (!csrfToken) {
      const prepared = await fetch('/api/v1/csrf', {
        credentials: 'same-origin'
      });
      if (!prepared.ok) throw new Error('Unable to prepare a secure request. Reload the page.');
      csrfToken = (await prepared.json()).csrf_token;
    }
    headers['X-CSRFToken'] = csrfToken;
  }
  const multipart = body instanceof FormData;
  if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json';
  const response = await fetch(url, {
    method,
    credentials: 'same-origin',
    headers,
    body: body === undefined ? undefined : multipart ? body : JSON.stringify(body)
  });
  if (response.status === 204) {
    csrfToken = null;
    return null;
  }
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error?.message || 'The request could not be completed.');
    error.status = response.status;
    error.fields = data.error?.fields || {};
    if (response.status === 400) csrfToken = null;
    throw error;
  }
  if (data.csrf_token) csrfToken = data.csrf_token;
  return data;
}

export function forgetCsrfToken() {
  csrfToken = null;
}
