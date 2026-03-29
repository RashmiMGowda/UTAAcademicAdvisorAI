import { useEffect, useState } from "react";
import {
  askAdvisor,
  fetchCurrentUser,
  fetchHistory,
  loginWithPassword,
  logout
} from "./lib/api";

const programOptions = [
  { value: "CSE", label: "Computer Science" },
  { value: "SE", label: "Software Engineering" },
  { value: "CompE", label: "Computer Engineering" },
  { value: "EE", label: "Electrical Engineering" },
  { value: "ME", label: "Mechanical Engineering" },
  { value: "IE", label: "Industrial Engineering" },
  { value: "CivilE", label: "Civil Engineering" },
  { value: "AREN", label: "Architectural Engineering" }
];

const starterPrompts = [
  "What are the recommended spring courses for a third-year Computer Science student?",
  "If I take CSE 4344 in fall, what should I take in spring?",
  "What courses need CSE 3318 as a prerequisite?",
  "Give me a smart junior-year plan for Software Engineering."
];

function AssistantMessage({ message }) {
  return (
    <div className="message message-assistant">
      <div className="message-label">Advisor</div>
      <p className="message-summary">{message.summary}</p>

      {message.recommendations?.length ? (
        <div className="recommendation-grid">
          {message.recommendations.map((item) => (
            <article className="course-card" key={`${item.course}-${item.title}`}>
              <div className="course-code">{item.course}</div>
              <div className="course-title">{item.title}</div>
              <div className="course-hours">{item.hours} hrs</div>
            </article>
          ))}
        </div>
      ) : null}

      {message.notes?.length ? (
        <div className="notes-block">
          <div className="section-kicker">Helpful Notes</div>
          <ul>
            {message.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function UserMessage({ message }) {
  return (
    <div className="message message-user">
      <div className="message-label">You</div>
      <p>{message.text}</p>
    </div>
  );
}

const SESSION_KEY = "uta_rag_session_token";

function LoginScreen({ error, onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="login-shell">
      <section className="login-card">
        <div className="login-brand">UTA</div>
        <p className="section-kicker">Advisor Login</p>
        <h1>Sign in to your advisor workspace</h1>
        <p className="login-copy">
          Use the demo login to open the advisor chat and save your conversation history.
        </p>
        <form
          className="login-form"
          onSubmit={(event) => {
            event.preventDefault();
            onLogin(username, password);
          }}
        >
          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
            />
          </label>
          <button className="send-button login-button" type="submit">
            Login
          </button>
        </form>
        <p className="login-hint">
          Demo credentials: username <code>aiproj</code> and password <code>333</code>
        </p>
        {error ? <p className="login-error">{error}</p> : null}
      </section>
    </div>
  );
}

export default function App() {
  const [program, setProgram] = useState("");
  const [courseFilter, setCourseFilter] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [sessionToken, setSessionToken] = useState(
    () => window.localStorage.getItem(SESSION_KEY) || ""
  );
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      summary:
        "Ask about a semester plan, prerequisites, or what to take next. I’ll answer from the extracted UTA advising PDFs.",
      recommendations: [],
      notes: [
        "Program selection is optional, so you can just ask naturally.",
        "Use a course code like CSE 3318 or CSE 4344 when you want a more precise answer."
      ],
      sources: []
    }
  ]);

  useEffect(() => {
    async function bootstrap() {
      if (!sessionToken) {
        setAuthLoading(false);
        return;
      }

      try {
        const [{ user: currentUser }, { messages: history }] = await Promise.all([
          fetchCurrentUser(sessionToken),
          fetchHistory(sessionToken)
        ]);
        setUser(currentUser);
        if (history?.length) {
          setMessages(
            history.map((message, index) => ({
              id: `${message.role}-${index}-${message.created_at || Date.now()}`,
              ...message
            }))
          );
        }
      } catch (error) {
        window.localStorage.removeItem(SESSION_KEY);
        setSessionToken("");
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    bootstrap();
  }, [sessionToken]);

  async function handleLogin(username, password) {
    setAuthError("");
    try {
      const result = await loginWithPassword(username, password);
      window.localStorage.setItem(SESSION_KEY, result.session_token);
      setSessionToken(result.session_token);
      setUser(result.user);
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          summary: `Hi ${result.user.name.split(" ")[0]}! Ask about degree plans, prerequisites, or course sequencing and I’ll search the advising PDFs for you.`,
          recommendations: [],
          notes: [
            "Program selection is optional.",
            "Questions like 'third-year spring for CSE' work well."
          ],
          sources: []
        }
      ]);
    } catch (error) {
      setAuthError(String(error.message || error));
    }
  }

  async function handleLogout() {
    try {
      if (sessionToken) {
        await logout(sessionToken);
      }
    } catch (error) {
      // Best effort logout.
    }
    window.localStorage.removeItem(SESSION_KEY);
    setSessionToken("");
    setUser(null);
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        summary:
          "Ask about a semester plan, prerequisites, or what to take next. I’ll answer from the extracted UTA advising PDFs.",
        recommendations: [],
        notes: [
          "Program selection is optional, so you can just ask naturally.",
          "Use a course code like CSE 3318 or CSE 4344 when you want a more precise answer."
        ],
        sources: []
      }
    ]);
  }

  async function submitQuery(nextQuestion) {
    const text = (nextQuestion ?? question).trim();
    if (!text || loading || !sessionToken) {
      return;
    }

    const userEntry = {
      id: `user-${Date.now()}`,
      role: "user",
      text
    };

    setMessages((current) => [...current, userEntry]);
    setQuestion("");
    setLoading(true);

    try {
      const result = await askAdvisor({
        program,
        question: text,
        courseFilter,
        sessionToken
      });

      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          summary: result.summary,
          recommendations: result.recommendations || [],
          notes: result.notes || [],
          sources: result.sources || []
        }
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          summary:
            "I could not fetch a response right now. Please check the backend or try again.",
            recommendations: [],
            notes: [String(error.message || error)],
            sources: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (authLoading) {
    return (
      <div className="login-shell">
        <section className="login-card">
          <div className="login-brand">UTA</div>
          <h1>Loading your advisor workspace...</h1>
        </section>
      </div>
    );
  }

  if (!sessionToken || !user) {
    return <LoginScreen error={authError} onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <aside className="hero-panel">
        <div className="brand-mark">UTA</div>
        <h1>RAG Advisor</h1>
        <p className="hero-copy">
          A smarter student-facing planner for degree-path questions, semester
          choices, and course-sequence guidance.
        </p>

        <div className="control-card">
          <label className="field">
            <span>Program</span>
            <select value={program} onChange={(event) => setProgram(event.target.value)}>
              <option value="">Search all programs</option>
              {programOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Course Filter</span>
            <input
              value={courseFilter}
              onChange={(event) => setCourseFilter(event.target.value)}
              placeholder="Example: CSE 4344"
            />
          </label>
        </div>

        <div className="prompt-card">
          <div className="section-kicker">Quick Starts</div>
          {starterPrompts.map((prompt) => (
            <button
              className="prompt-chip"
              key={prompt}
              type="button"
              onClick={() => submitQuery(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </aside>

      <main className="chat-panel">
        <div className="chat-header">
          <div>
            <div className="section-kicker">Advisor Chat</div>
            <h2>Plan smarter, ask naturally</h2>
          </div>
          <div className="chat-header-actions">
            <div className="user-pill">{user.name}</div>
            <div className="status-pill">{loading ? "Thinking..." : "Ready"}</div>
            <button className="ghost-button" type="button" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </div>

        <div className="chat-feed">
          {messages.map((message) =>
            message.role === "assistant" ? (
              <AssistantMessage key={message.id} message={message} />
            ) : (
              <UserMessage key={message.id} message={message} />
            )
          )}
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            submitQuery();
          }}
        >
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about a semester plan, prerequisites, or what to take after a specific course."
            rows={4}
          />
          <button className="send-button" type="submit" disabled={loading}>
            {loading ? "Working..." : "Ask Advisor"}
          </button>
        </form>
      </main>
    </div>
  );
}
