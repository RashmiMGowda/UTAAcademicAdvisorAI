export interface ProgramOption {
  value: string;
  label: string;
}

export const programOptions: ProgramOption[] = [
  { value: "CSE", label: "Computer Science" },
  { value: "SE", label: "Software Engineering" },
  { value: "CompE", label: "Computer Engineering" },
  { value: "EE", label: "Electrical Engineering" },
  { value: "ME", label: "Mechanical Engineering" },
  { value: "IE", label: "Industrial Engineering" },
  { value: "CivilE", label: "Civil Engineering" },
  { value: "AREN", label: "Architectural Engineering" }
];

export const starterPrompts: string[] = [
  "What are the recommended spring courses for a third-year Computer Science student?",
  "If I take CSE 4344 in fall, what should I take in spring?",
  "What courses need CSE 3318 as a prerequisite?",
  "Give me a smart junior-year plan for Software Engineering."
];
