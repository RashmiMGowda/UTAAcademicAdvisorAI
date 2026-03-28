import { useState } from "react";
import { askAdvisor } from "../lib/api";
import { Message } from "../types";

export function useAdvisor(initialProgram: string = "CSE") {
  const [program, setProgram] = useState<string>(initialProgram);
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

  return {
    program,
    setProgram,
    courseFilter,
    setCourseFilter,
    question,
    setQuestion,
    loading,
    messages,
    submitQuery
  };
}
