import { useState } from "react";
import { submitFeedback } from "./api";

export default function FeedbackBar({ sessionId, team, query, onDone }) {
  const [sent, setSent] = useState(false);

  const handle = async (helpful) => {
    if (sent) return;
    await submitFeedback({ sessionId, team, query, helpful });
    setSent(true);
    onDone?.(helpful);
  };

  if (sent) {
    return <span className="feedback-thanks">Thanks — I&apos;ll remember that.</span>;
  }

  return (
    <div className="feedback-bar">
      <span className="feedback-label">Helpful?</span>
      <button className="feedback-btn" type="button" onClick={() => handle(true)}>yes</button>
      <button className="feedback-btn feedback-btn--no" type="button" onClick={() => handle(false)}>no</button>
    </div>
  );
}
