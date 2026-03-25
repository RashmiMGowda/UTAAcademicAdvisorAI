const demoReplies = {
  CSE: {
    summary:
      "For a typical junior spring in Computer Science, a balanced plan often includes core systems, software, math, and communication requirements.",
    recommendations: [
      { course: "CSE 3380", title: "Linear Algebra for CSE", hours: 3 },
      { course: "CSE 3310", title: "Introduction to Software Engineering", hours: 3 },
      { course: "CSE 3320", title: "Operating Systems", hours: 3 },
      { course: "MATH 2326", title: "Calculus III", hours: 3 },
      { course: "COMS 2302", title: "Professional and Technical Communication", hours: 3 }
    ],
    notes: [
      "This plan looks like a full 15-hour spring schedule.",
      "If you already know one target course, ask a follow-up like 'If I take CSE 4344 in fall, what should I take in spring?'",
      "Always verify prerequisites and advising notes before registration."
    ],
    sources: ["2025-CSE.pdf"]
  },
  SE: {
    summary:
      "For Software Engineering, the best plan usually mixes software design, systems foundations, and degree requirements for the selected semester.",
    recommendations: [
      { course: "CSE 3311", title: "Object-Oriented Software Engineering", hours: 3 },
      { course: "CSE 3320", title: "Operating Systems", hours: 3 },
      { course: "CSE 3330", title: "Database Systems", hours: 3 }
    ],
    notes: [
      "You can narrow the answer by semester, year, or a specific course code.",
      "Try asking: 'What are the spring courses for third-year Software Engineering?'"
    ],
    sources: ["2025-SE.pdf"]
  }
};

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function askAdvisor({ program, question, courseFilter }) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  if (apiBase) {
    try {
      const response = await fetch(`${apiBase}/advisor/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ program, question, course_filter: courseFilter })
      });

      if (response.ok) {
        return response.json();
      }
    } catch (error) {
      // Fall through to demo mode when the lightweight backend is not running.
    }
  }

  await delay(650);
  const selected = demoReplies[program] || demoReplies.CSE;

  return {
    summary: selected.summary,
    recommendations: selected.recommendations,
    notes: selected.notes,
    sources: selected.sources,
    mode: "demo"
  };
}
