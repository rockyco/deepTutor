/**
 * API client for the 11+ Deep Tutor backend.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://deeptutor-backend-400481200537.us-central1.run.app";

if (typeof window !== "undefined" && !API_BASE && window.location.hostname !== "localhost") {
  console.warn("⚠️ API_BASE is empty. Set NEXT_PUBLIC_API_URL environment variable.");
}

/**
 * Get the full URL for an image path.
 * Handles both absolute URLs and relative paths from the API.
 */
export function getImageUrl(path: string | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http") || path.startsWith("data:")) return path;
  return `${API_BASE}${path}`;
}

/**
 * Check if a string is an image URL (SVG, PNG, JPG, or data URI).
 */
export function isImageUrl(str: string): boolean {
  if (!str) return false;
  return (
    str.startsWith("data:image/") ||
    str.startsWith("/images/") ||
    str.endsWith(".svg") ||
    str.endsWith(".png") ||
    str.endsWith(".jpg") ||
    str.endsWith(".jpeg")
  );
}

// Types matching backend models
export type Subject = "english" | "maths" | "verbal_reasoning" | "non_verbal_reasoning";

export type QuestionType =
  | "comprehension"
  | "grammar"
  | "spelling"
  | "vocabulary"
  | "sentence_completion"
  | "number_operations"
  | "fractions"
  | "decimals"
  | "percentages"
  | "geometry"
  | "measurement"
  | "data_handling"
  | "word_problems"
  | "algebra"
  | "ratio"
  | "vr_insert_letter"
  | "vr_odd_ones_out"
  | "vr_alphabet_code"
  | "vr_synonyms"
  | "vr_hidden_word"
  | "vr_missing_word"
  | "vr_number_series"
  | "vr_letter_series"
  | "vr_number_connections"
  | "vr_word_pairs"
  | "vr_multiple_meaning"
  | "vr_letter_relationships"
  | "vr_number_codes"
  | "vr_compound_words"
  | "vr_word_shuffling"
  | "vr_anagrams"
  | "vr_logic_problems"
  | "vr_explore_facts"
  | "vr_solve_riddle"
  | "vr_rhyming_synonyms"
  | "vr_shuffled_sentences"
  | "nvr_sequences"
  | "nvr_odd_one_out"
  | "nvr_analogies"
  | "nvr_matrices"
  | "nvr_rotation"
  | "nvr_reflection"
  | "nvr_spatial_3d"
  | "nvr_codes"
  | "nvr_visual";

export interface QuestionContent {
  text: string;
  passage?: string;
  options?: string[];
  option_images?: string[];
  image_url?: string;
  images?: string[];
  items?: string[];
  pairs?: Record<string, string>;
  context?: Record<string, unknown>;
  multi_select?: boolean;
}

export interface Answer {
  value: string | string[] | Record<string, string>;
  accept_variations?: string[];
  case_sensitive?: boolean;
  order_matters?: boolean;
}

export interface Hint {
  level: number;
  text: string;
  penalty: number;
}

export interface Question {
  id: string;
  subject: Subject;
  question_type: QuestionType;
  format: string;
  difficulty: number;
  content: QuestionContent;
  answer: Answer;
  explanation: string;
  hints: Hint[];
  tags: string[];
  source?: string;
  created_at: string;
}

export interface AnswerResult {
  is_correct: boolean;
  correct_answer: string | string[] | Record<string, string>;
  explanation: string;
  score: number;
  feedback: string;
}

export interface User {
  id: string;
  name: string;
  year_group: number;
  target_schools: string[];
  total_questions_attempted: number;
  total_correct: number;
  current_streak: number;
  longest_streak: number;
  total_practice_time_minutes: number;
  ai_settings?: {
    ai_provider?: string;
    model_name?: string;
    api_key?: string;
  };
}

export interface PracticeSession {
  id: string;
  user_id: string;
  subject?: Subject;
  question_type?: QuestionType;
  is_timed: boolean;
  time_limit_minutes?: number;
  started_at: string;
  completed_at?: string;
  question_ids: string[];
  answers: UserAnswer[];
}

export interface UserAnswer {
  id: string;
  session_id: string;
  question_id: string;
  user_answer: string | string[] | Record<string, string>;
  is_correct: boolean;
  time_taken_seconds: number;
  hints_used: number;
  score: number;
}

export interface PracticeSessionResult {
  session_id: string;
  subject?: Subject;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  total_score: number;
  time_taken_minutes: number;
  questions_by_type: Record<string, { attempted: number; correct: number }>;
  strengths: string[];
  areas_to_improve: string[];
}

export interface ProgressSummary {
  user_id: string;
  overall_mastery: number;
  subjects: Record<string, SubjectProgress>;
  weak_areas: WeakArea[];
  strong_areas: WeakArea[];
  recent_activity: RecentActivity[];
  recommended_next: Recommendation[];
}

export interface SubjectProgress {
  mastery: number;
  accuracy?: number;
  total_attempted: number;
  total_correct: number;
  types: Record<string, TypeProgress>;
}

export interface TypeProgress {
  mastery: number;
  attempted: number;
  correct: number;
  level: number;
}

export interface WeakArea {
  subject: string;
  type: string;
  accuracy: number;
  attempted: number;
}

export interface RecentActivity {
  date: string;
  subject: string;
  questions: number;
  correct: number;
}

export interface Recommendation {
  subject: string;
  type: string;
  reason: string;
}

// API Functions

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    fetchAPI<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      // OAuth2PasswordRequestForm expects form data, not JSON
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }).toString(),
    }),

  register: (email: string, password: string, name: string, yearGroup: number) =>
    fetchAPI<{ access_token: string; token_type: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name, year_group: yearGroup }),
    }),

  getMe: () => fetchAPI<User & { ai_settings?: any }>("/api/auth/me"),

  updateSettings: (settings: { ai_provider?: string; model_name?: string; api_key?: string }) =>
    fetchAPI<{ status: string }>("/api/auth/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
};

// Questions API
export const questionsAPI = {
  getQuestions: (params?: {
    subject?: Subject;
    question_type?: QuestionType;
    difficulty?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.subject) searchParams.set("subject", params.subject);
    if (params?.question_type)
      searchParams.set("question_type", params.question_type);
    if (params?.difficulty)
      searchParams.set("difficulty", String(params.difficulty));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    // Add cache-busting parameter to ensure fresh randomized questions each request
    searchParams.set("_t", String(Date.now()));
    return fetchAPI<Question[]>(`/api/questions?${searchParams}`, {
      cache: "no-store",
    });
  },

  getQuestion: (id: string) => fetchAPI<Question>(`/api/questions/${id}`),

  checkAnswer: (questionId: string, userAnswer: string, hintsUsed: number = 0) =>
    fetchAPI<AnswerResult>("/api/questions/check", {
      method: "POST",
      body: JSON.stringify({
        question_id: questionId,
        user_answer: userAnswer,
        hints_used: hintsUsed,
      }),
    }),

  getHints: (questionId: string, level: number = 1) =>
    fetchAPI<Hint[]>(`/api/questions/${questionId}/hints?level=${level}`),

  getTuition: (question: string, topic: string) =>
    fetchAPI<{ mermaid: string; explanation: string }>("/api/visualize/tuition", {
      method: "POST",
      body: JSON.stringify({ question, topic }),
    }),
};

// Practice API
export const practiceAPI = {
  startSession: (
    userId: string,
    config: {
      subject?: Subject;
      question_type?: QuestionType;
      num_questions?: number;
      difficulty?: number;
      is_timed?: boolean;
      time_limit_minutes?: number;
    }
  ) =>
    fetchAPI<PracticeSession>("/api/practice/start", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, config }),
    }),

  getSession: (sessionId: string) =>
    fetchAPI<PracticeSession>(`/api/practice/${sessionId}`),

  getNextQuestion: (sessionId: string) =>
    fetchAPI<Question | null>(`/api/practice/${sessionId}/next`),

  submitAnswer: (
    sessionId: string,
    questionId: string,
    userAnswer: string,
    timeTakenSeconds: number,
    hintsUsed: number = 0
  ) =>
    fetchAPI<UserAnswer>(`/api/practice/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({
        question_id: questionId,
        user_answer: userAnswer,
        time_taken_seconds: timeTakenSeconds,
        hints_used: hintsUsed,
      }),
    }),

  completeSession: (sessionId: string) =>
    fetchAPI<PracticeSessionResult>(`/api/practice/${sessionId}/complete`, {
      method: "POST",
    }),
};

// Users API
export const usersAPI = {
  createUser: (name: string, yearGroup: number = 5, targetSchools: string[] = []) =>
    fetchAPI<User>("/api/users", {
      method: "POST",
      body: JSON.stringify({
        name,
        year_group: yearGroup,
        target_schools: targetSchools,
      }),
    }),

  getUser: (userId: string) => fetchAPI<User>(`/api/users/${userId}`),

  listUsers: () => fetchAPI<User[]>("/api/users"),
};

// Progress API
export const progressAPI = {
  getSummary: (userId: string) =>
    fetchAPI<ProgressSummary>(`/api/progress/${userId}`),

  getWeakAreas: (userId: string, limit: number = 5) =>
    fetchAPI<WeakArea[]>(`/api/progress/${userId}/weaknesses?limit=${limit}`),

  getRecommendations: (userId: string) =>
    fetchAPI<Recommendation[]>(`/api/progress/${userId}/recommendations`),
};
