const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function askAdvisor({ program, question, courseFilter }) {
  const response = await fetch(`${apiBase}/advisor/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ program, question, course_filter: courseFilter })
  });

  return parseJson(response);
}
