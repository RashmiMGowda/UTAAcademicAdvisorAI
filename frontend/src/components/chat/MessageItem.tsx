import { Message } from "../../types";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  if (message.role === "user") {
    return (
      <div className="message message-user">
        <div className="message-label">You</div>
        <p>{message.text}</p>
      </div>
    );
  }

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
