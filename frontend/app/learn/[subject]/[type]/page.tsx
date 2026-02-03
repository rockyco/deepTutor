import LessonClient from "./LessonClient";

// All question types per subject for static export
const LESSON_TYPES: Record<string, string[]> = {
  english: [
    "comprehension", "grammar", "spelling", "vocabulary",
    "sentence_completion", "punctuation",
  ],
  maths: [
    "number_operations", "fractions", "decimals", "percentages",
    "geometry", "measurement", "data_handling", "word_problems",
    "algebra", "ratio",
  ],
  verbal_reasoning: [
    "vr_synonyms", "vr_odd_ones_out", "vr_hidden_word", "vr_missing_word",
    "vr_number_series", "vr_letter_series", "vr_number_connections",
    "vr_word_pairs", "vr_multiple_meaning", "vr_letter_relationships",
    "vr_number_codes", "vr_compound_words", "vr_word_shuffling",
    "vr_anagrams", "vr_logic_problems", "vr_explore_facts",
    "vr_solve_riddle", "vr_rhyming_synonyms", "vr_shuffled_sentences",
    "vr_insert_letter", "vr_alphabet_code",
  ],
  non_verbal_reasoning: [
    "nvr_sequences", "nvr_odd_one_out", "nvr_analogies", "nvr_matrices",
    "nvr_rotation", "nvr_reflection", "nvr_spatial_3d", "nvr_codes",
    "nvr_visual",
  ],
};

export function generateStaticParams() {
  const params: { subject: string; type: string }[] = [];
  for (const [subject, types] of Object.entries(LESSON_TYPES)) {
    for (const type of types) {
      params.push({ subject, type });
    }
  }
  return params;
}

export default function LessonPage() {
  return <LessonClient />;
}
