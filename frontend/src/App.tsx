import { useState, FormEvent, ChangeEvent } from "react";
import { askAdvisor, Recommendation } from "./lib/api";

interface ProgramOption {
  value: string;
  label: string;
}

const programOptions: ProgramOption[] = [
  { value: "CSE", label: "Computer Science" },
  { value: "SE", label: "Software Engineering" },
  { value: "CompE", label: "Computer Engineering" },
  { value: "EE", label: "Electrical Engineering" },
  { value: "ME", label: "Mechanical Engineering" },
  { value: "IE", label: "Industrial Engineering" },
  { value: "CivilE", label: "Civil Engineering" },
  { value: "AREN", label: "Architectural Engineering" }
];

const starterPrompts: string[] = [
  "What are the recommended spring courses for a third-year Computer Science student?",
  "If I take CSE 4344 in fall, what should I take in spring?",
  "What courses need CSE 3318 as a prerequisite?",
  "Give me a smart junior-year plan for Software Engineering."
];

interface Message {
  id: string;
  role: "assistant" | "user";
  summary?: string;
  text?: string;
  recommendations?: Recommendation[];
  notes?: string[];
  sources?: string[];
}

interface AssistantMessageProps {
  message: Message;
}

function AssistantMessage({ message }: AssistantMessageProps) {
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

      {message.sources?.length ? (
        <div className="source-row">
          {message.sources.map((source) => (
            <span className="source-chip" key={source}>
              {source}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

interface UserMessageProps {
  message: Message;
}

function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="message message-user">
      <div className="message-label">You</div>
      <p>{message.text}</p>
    </div>
  );
}

export default function App() {
  const [program, setProgram] = useState<string>("CSE");
  const [courseFilter, setCourseFilter] = useState<string>("");
  const [question, setQuestion] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      summary:
        "Ask for a semester plan, a course path, or a prerequisite-based suggestion. I will keep the answer clean and student-friendly.",
      recommendations: [],
      notes: [
        "Pick the right UTA program first.",
        "Use a course code like CSE 3318 or CSE 4344 when you want a more precise answer."
      ],
      sources: []
    }
  ]);

  async function submitQuery(nextQuestion?: string) {
    const text = (nextQuestion ?? question).trim();
    if (!text || loading) {
      return;
    }

    const userEntry: Message = {
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
        courseFilter
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
            "I could not fetch a response right now. Please try again or connect the React UI to your backend API.",
          recommendations: [],
          notes: [String(error instanceof Error ? error.message : error)],
          sources: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  const handleProgramChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setProgram(event.target.value);
  };

  const handleCourseFilterChange = (event: ChangeEvent<HTMLInputElement>) => {
    setCourseFilter(event.target.value);
  };

  const handleQuestionChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(event.target.value);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submitQuery();
  };

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
            <select value={program} onChange={handleProgramChange}>
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
              onChange={handleCourseFilterChange}
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
          <div className="status-pill">{loading ? "Thinking..." : "Ready"}</div>
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

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={question}
            onChange={handleQuestionChange}
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
