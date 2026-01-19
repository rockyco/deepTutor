import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function getSubjectColor(subject: string): string {
  const colors: Record<string, string> = {
    english: "bg-english-500",
    maths: "bg-maths-500",
    verbal_reasoning: "bg-verbal-500",
    non_verbal_reasoning: "bg-nonverbal-500",
  };
  return colors[subject] || "bg-gray-500";
}

export function getSubjectBgColor(subject: string): string {
  const colors: Record<string, string> = {
    english: "bg-english-50",
    maths: "bg-maths-50",
    verbal_reasoning: "bg-verbal-50",
    non_verbal_reasoning: "bg-nonverbal-50",
  };
  return colors[subject] || "bg-gray-50";
}

export function getSubjectDisplayName(subject: string): string {
  const names: Record<string, string> = {
    english: "English",
    maths: "Maths",
    verbal_reasoning: "Verbal Reasoning",
    non_verbal_reasoning: "Non-verbal Reasoning",
  };
  return names[subject] || subject;
}

export function getQuestionTypeDisplayName(type: string): string {
  const names: Record<string, string> = {
    // English
    comprehension: "Comprehension",
    grammar: "Grammar",
    spelling: "Spelling",
    vocabulary: "Vocabulary",
    sentence_completion: "Sentence Completion",
    // Maths
    number_operations: "Number Operations",
    fractions: "Fractions",
    decimals: "Decimals",
    percentages: "Percentages",
    geometry: "Geometry",
    measurement: "Measurement",
    data_handling: "Data Handling",
    word_problems: "Word Problems",
    algebra: "Algebra",
    ratio: "Ratio",
    // Verbal Reasoning
    vr_synonyms: "Synonyms",
    vr_hidden_word: "Hidden Word",
    vr_number_series: "Number Series",
    vr_letter_series: "Letter Series",
    vr_alphabet_code: "Alphabet Code",
    vr_odd_ones_out: "Odd Ones Out",
    vr_word_pairs: "Word Pairs",
    vr_compound_words: "Compound Words",
    vr_anagrams: "Anagrams",
    // Non-verbal Reasoning
    nvr_sequences: "Sequences",
    nvr_odd_one_out: "Odd One Out",
    nvr_analogies: "Analogies",
    nvr_rotation: "Rotation",
    nvr_reflection: "Reflection",
    nvr_matrices: "Matrices",
    nvr_spatial_3d: "3D Spatial",
    nvr_codes: "Codes",
  };
  return names[type] || type.replace(/_/g, " ").replace(/^(vr|nvr) /, "");
}

export function getDifficultyLabel(level: number): string {
  const labels = ["Very Easy", "Easy", "Medium", "Hard", "Very Hard"];
  return labels[level - 1] || "Unknown";
}

export function getDifficultyColor(level: number): string {
  const colors = [
    "text-green-600",
    "text-lime-600",
    "text-yellow-600",
    "text-orange-600",
    "text-red-600",
  ];
  return colors[level - 1] || "text-gray-600";
}
