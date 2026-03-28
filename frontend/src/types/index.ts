export interface Recommendation {
  course: string;
  title: string;
  hours: number;
}

export interface AdvisorResponse {
  summary: string;
  recommendations: Recommendation[];
  notes: string[];
  sources: string[];
  mode?: string;
}

export interface AdvisorQueryParams {
  program: string;
  question: string;
  courseFilter: string;
}

export interface Message {
  id: string;
  role: "assistant" | "user";
  summary?: string;
  text?: string;
  recommendations?: Recommendation[];
  notes?: string[];
  sources?: string[];
}

export interface User {
  id: string;
  email: string;
  name: string;
}
