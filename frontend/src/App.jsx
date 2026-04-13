import { useEffect, useState } from "react";
import { LoginPage } from "./components/auth/LoginPage";
import { useAuth } from "./context/AuthContext";
import { askAdvisor } from "./lib/api";
import {
  createChatSession,
  deleteChatSession,
  listChatMessages,
  listChatSessions,
  saveChatMessage,
  updateChatSession,
} from "./lib/chatHistory";

const starterPrompts = [
  "What are the admission criteria for MSCS?",
  "What can I take after CSE 4344?",
  "What are AI-related courses in MSCS?",
  "What courses need CSE 3318 as a prerequisite?",
];

const defaultWelcomeMessage = {
  id: "welcome",
  role: "assistant",
  summary:
    "I can help with UTA degree planning, prerequisites, graduate course options, and semester guidance using the advising PDFs in this project.",
  recommendations: [],
  notes: [
    "Your chat history is saved to your Supabase account, so you can come back to it later.",
    "Try 'What are the admission criteria for MSCS?', 'What can I take after CSE 4344?', or 'What are AI-related courses in MSCS?'.",
  ],
  sources: [],
};

function createSessionTitle(question) {
  const cleaned = question.trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return "New chat";
  }
  if (cleaned.length <= 52) {
    return cleaned;
  }
  return `${cleaned.slice(0, 52).trimEnd()}...`;
}

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
              {item.prereq ? <div className="course-prereq">Prerequisite: {item.prereq}</div> : null}
              {item.hours ? <div className="course-hours">{item.hours} hrs</div> : null}
            </article>
          ))}
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

export default function App() {
  const { user, isAuthenticated, initializing, logout } = useAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([defaultWelcomeMessage]);

  useEffect(() => {
    if (!isAuthenticated || !user) {
      return undefined;
    }

    let cancelled = false;

    async function loadInitialHistory() {
      setHistoryLoading(true);
      setHistoryError("");
      try {
        const savedSessions = await listChatSessions(user.id);
        if (cancelled) {
          return;
        }
        setSessions(savedSessions);

        if (!savedSessions.length) {
          setActiveSessionId(null);
          setMessages([defaultWelcomeMessage]);
          return;
        }

        const firstSession = savedSessions[0];
        setActiveSessionId(firstSession.id);
        const savedMessages = await listChatMessages(firstSession.id);
        if (cancelled) {
          return;
        }
        setMessages(savedMessages.length ? savedMessages : [defaultWelcomeMessage]);
      } catch (error) {
        if (!cancelled) {
          setHistoryError(String(error.message || error));
          setMessages([defaultWelcomeMessage]);
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    loadInitialHistory();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, user]);

  async function handleLogout() {
    await logout();
    setActiveSessionId(null);
    setSessions([]);
    setMessages([defaultWelcomeMessage]);
    setHistoryError("");
  }

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([defaultWelcomeMessage]);
    setQuestion("");
    setHistoryError("");
  }

  async function openSession(session) {
    if (!session?.id) {
      return;
    }
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const savedMessages = await listChatMessages(session.id);
      setActiveSessionId(session.id);
      setMessages(savedMessages.length ? savedMessages : [defaultWelcomeMessage]);
    } catch (error) {
      setHistoryError(String(error.message || error));
    } finally {
      setHistoryLoading(false);
    }
  }

  function upsertSession(updatedSession) {
    setSessions((current) => {
      const remaining = current.filter((session) => session.id !== updatedSession.id);
      return [updatedSession, ...remaining];
    });
  }

  async function handleDeleteSession(sessionId, event) {
    event.stopPropagation();
    if (!sessionId) {
      return;
    }

    setHistoryError("");
    try {
      await deleteChatSession(sessionId);
      setSessions((current) => current.filter((session) => session.id !== sessionId));

      if (activeSessionId !== sessionId) {
        return;
      }

      const remainingSessions = sessions.filter((session) => session.id !== sessionId);
      const nextSession = remainingSessions[0];

      if (nextSession) {
        await openSession(nextSession);
      } else {
        startNewChat();
      }
    } catch (error) {
      setHistoryError(String(error.message || error));
    }
  }

  async function ensureSession(questionText) {
    if (activeSessionId) {
      const updated = await updateChatSession({
        sessionId: activeSessionId,
        program: "",
        courseFilter: "",
      });
      upsertSession(updated);
      return updated.id;
    }

    const created = await createChatSession({
      userId: user.id,
      title: createSessionTitle(questionText),
      program: "",
      courseFilter: "",
    });
    setActiveSessionId(created.id);
    upsertSession(created);
    return created.id;
  }

  async function submitQuery(nextQuestion) {
    const text = (nextQuestion ?? question).trim();
    if (!text || loading || historyLoading || !user) {
      return;
    }

    setHistoryError("");
    setQuestion("");
    setLoading(true);

    try {
      const sessionId = await ensureSession(text);

      const savedUserMessage = await saveChatMessage({
        sessionId,
        userId: user.id,
        role: "user",
        content: text,
      });
      setMessages((current) => [...current.filter((message) => message.id !== "welcome"), savedUserMessage]);

      const result = await askAdvisor({
        program: "",
        question: text,
        courseFilter: "",
      });

      const savedAssistantMessage = await saveChatMessage({
        sessionId,
        userId: user.id,
        role: "assistant",
        content: result.summary,
        payload: {
          recommendations: result.recommendations || [],
          notes: result.notes || [],
          sources: result.sources || [],
        },
      });

      setMessages((current) => [...current, savedAssistantMessage]);

      const refreshedSession = await updateChatSession({
        sessionId,
        title: createSessionTitle(text),
        program: "",
        courseFilter: "",
      });
      upsertSession(refreshedSession);
    } catch (error) {
      setHistoryError(String(error.message || error));
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          summary:
            "I could not complete that request right now. Your login worked, but saving or retrieving this chat hit an error.",
          recommendations: [],
          notes: [String(error.message || error)],
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (initializing) {
    return (
      <div className="auth-page">
        <section className="auth-card">
          <div className="brand-mark">UTA</div>
          <h1>Loading your advisor workspace...</h1>
        </section>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <LoginPage />;
  }

  return (
    <div className="app-shell">
      <aside className="hero-panel">
        <div className="brand-mark">UTA</div>
        <h1>RAG Advisor</h1>
        <p className="hero-copy">Ask focused UTA advising questions and get PDF-grounded answers.</p>

        {/* <div className="control-card">
          <p className="control-copy">
          </p>
          <button className="ghost-button full-width" type="button" onClick={startNewChat}>
            New Chat
          </button>
        </div> */}

        <div className="history-card">
          <div className="history-header">
            <div className="section-kicker">Saved Chats</div>
            <span className="history-count">{sessions.length}</span>
          </div>
          {historyError ? <div className="error-message">{historyError}</div> : null}
          <div className="history-list">
            {sessions.length ? (
              sessions.map((session) => (
                <div
                  className={`history-item ${session.id === activeSessionId ? "is-active" : ""}`}
                  key={session.id}
                >
                  <button className="history-open" type="button" onClick={() => openSession(session)}>
                    <strong>{session.title || "New chat"}</strong>
                    <span>
                      PDF-grounded advisor chat
                    </span>
                  </button>
                  <button
                    className="history-delete"
                    type="button"
                    aria-label={`Delete ${session.title || "chat"}`}
                    onClick={(event) => handleDeleteSession(session.id, event)}
                  >
                    Delete
                  </button>
                </div>
              ))
            ) : (
              <p className="history-empty">No saved chats yet. Start a question and this panel will fill in.</p>
            )}
          </div>
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
            <button
              className="ghost-button"
              type="button"
              onClick={startNewChat}
            >
              New Chat
            </button>
            {/* <div className="status-pill">
              {historyLoading ? "Loading history..." : loading ? "Thinking..." : "Ready"}
            </div> */}
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
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submitQuery();
              }
            }}
            placeholder="Ask about a UTA course, program, semester plan, prerequisite, or admissions detail."
            rows={4}
          />
          <button className="send-button" type="submit" disabled={loading || historyLoading}>
            {loading ? "Working..." : "Ask Advisor"}
          </button>
        </form>
      </main>
    </div>
  );
}
