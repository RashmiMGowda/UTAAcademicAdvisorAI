const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(sessionToken) {
  return sessionToken
    ? {
        Authorization: `Bearer ${sessionToken}`
      }
    : {};
}

async function parseJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function loginWithGoogle(credential) {
  const response = await fetch(`${apiBase}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential })
  });

  return parseJson(response);
}

export async function loginWithPassword(username, password) {
  const response = await fetch(`${apiBase}/auth/local`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });

  return parseJson(response);
}

export async function fetchCurrentUser(sessionToken) {
  const response = await fetch(`${apiBase}/auth/me`, {
    headers: {
      ...authHeaders(sessionToken)
    }
  });

  return parseJson(response);
}

export async function logout(sessionToken) {
  const response = await fetch(`${apiBase}/auth/logout`, {
    method: "POST",
    headers: {
      ...authHeaders(sessionToken)
    }
  });

  return parseJson(response);
}

export async function fetchHistory(sessionToken) {
  const response = await fetch(`${apiBase}/advisor/history`, {
    headers: {
      ...authHeaders(sessionToken)
    }
  });

  return parseJson(response);
}

export async function askAdvisor({ program, question, courseFilter, sessionToken }) {
  const response = await fetch(`${apiBase}/advisor/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(sessionToken)
    },
    body: JSON.stringify({ program, question, course_filter: courseFilter })
  });

  return parseJson(response);
}
