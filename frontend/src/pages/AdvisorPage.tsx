import { FormEvent, ChangeEvent } from "react";
import { useAdvisor } from "../hooks/useAdvisor";
import { MessageItem } from "../components/chat/MessageItem";
import { programOptions, starterPrompts } from "../constants";

export function AdvisorPage() {
  const {
    program,
    setProgram,
    courseFilter,
    setCourseFilter,
    question,
    setQuestion,
    loading,
    messages,
    submitQuery
  } = useAdvisor();

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
          {messages.map((message) => (
            <MessageItem key={message.id} message={message} />
          ))}
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
