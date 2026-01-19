"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Trophy,
  BookOpen,
  Calculator,
  Brain,
  Shapes,
  Clock,
  ChevronLeft,
  ChevronRight,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Flag,
} from "lucide-react";
import {
  practiceAPI,
  questionsAPI,
  usersAPI,
  Question,
  Subject,
  PracticeSessionResult,
} from "@/lib/api";

interface ExamConfig {
  subject: Subject;
  name: string;
  icon: typeof BookOpen;
  color: string;
  bgColor: string;
  questions: number;
  timeMinutes: number;
}

const examConfigs: ExamConfig[] = [
  {
    subject: "english",
    name: "English",
    icon: BookOpen,
    color: "text-sky-600",
    bgColor: "bg-sky-100",
    questions: 20,
    timeMinutes: 25,
  },
  {
    subject: "maths",
    name: "Maths",
    icon: Calculator,
    color: "text-emerald-600",
    bgColor: "bg-emerald-100",
    questions: 20,
    timeMinutes: 25,
  },
  {
    subject: "verbal_reasoning",
    name: "Verbal Reasoning",
    icon: Brain,
    color: "text-purple-600",
    bgColor: "bg-purple-100",
    questions: 20,
    timeMinutes: 25,
  },
  {
    subject: "non_verbal_reasoning",
    name: "Non-verbal Reasoning",
    icon: Shapes,
    color: "text-orange-600",
    bgColor: "bg-orange-100",
    questions: 15,
    timeMinutes: 20,
  },
];

type ExamState = "select" | "ready" | "in-progress" | "completed";

export default function MockExamPage() {
  const [examState, setExamState] = useState<ExamState>("select");
  const [selectedExam, setSelectedExam] = useState<ExamConfig | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<PracticeSessionResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Timer effect
  useEffect(() => {
    if (examState !== "in-progress" || timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          // Time's up - auto submit
          handleSubmitExam();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [examState, timeRemaining]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const startExam = async (config: ExamConfig) => {
    setSelectedExam(config);
    setLoading(true);

    try {
      // Get or create user
      let users = await usersAPI.listUsers();
      let user = users[0];
      if (!user) {
        user = await usersAPI.createUser("Student", 5, []);
      }

      // Start practice session
      const session = await practiceAPI.startSession(user.id, {
        subject: config.subject,
        num_questions: config.questions,
        is_timed: true,
        time_limit_minutes: config.timeMinutes,
      });

      setSessionId(session.id);

      // Load all questions for the exam
      const examQuestions = await questionsAPI.getQuestions({
        subject: config.subject,
        limit: config.questions,
      });

      setQuestions(examQuestions);
      setTimeRemaining(config.timeMinutes * 60);
      setAnswers({});
      setFlagged(new Set());
      setCurrentIndex(0);
      setExamState("ready");
    } catch (err) {
      console.error("Failed to start exam:", err);
      alert("Failed to start exam. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const beginExam = () => {
    setExamState("in-progress");
  };

  const handleAnswer = (questionId: string, answer: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: answer,
    }));
  };

  const toggleFlag = (questionId: string) => {
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(questionId)) {
        next.delete(questionId);
      } else {
        next.add(questionId);
      }
      return next;
    });
  };

  const handleSubmitExam = async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      // Submit all answers
      for (const question of questions) {
        const userAnswer = answers[question.id] || "";
        await practiceAPI.submitAnswer(
          sessionId,
          question.id,
          userAnswer,
          Math.floor((selectedExam?.timeMinutes || 0) * 60 - timeRemaining) / questions.length,
          0
        );
      }

      // Complete session
      const sessionResult = await practiceAPI.completeSession(sessionId);
      setResult(sessionResult);
      setExamState("completed");
    } catch (err) {
      console.error("Failed to submit exam:", err);
      // Still show results with local calculation
      const correct = questions.filter(
        (q) => answers[q.id]?.toLowerCase() === String(q.answer.value).toLowerCase()
      ).length;
      setResult({
        session_id: sessionId,
        subject: selectedExam?.subject,
        total_questions: questions.length,
        correct_answers: correct,
        accuracy: correct / questions.length,
        total_score: correct,
        time_taken_minutes: (selectedExam?.timeMinutes || 0) - timeRemaining / 60,
        questions_by_type: {},
        strengths: [],
        areas_to_improve: [],
      });
      setExamState("completed");
    } finally {
      setLoading(false);
    }
  };

  const currentQuestion = questions[currentIndex];

  // Select exam screen
  if (examState === "select") {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </Link>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Mock Exam</h1>
                <p className="text-sm text-gray-500">Timed exam simulation</p>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-xl border p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Choose an Exam Paper
            </h2>
            <p className="text-gray-600 mb-6">
              Select a subject to begin a timed mock exam. Questions are presented
              in exam format with a countdown timer.
            </p>

            <div className="grid sm:grid-cols-2 gap-4">
              {examConfigs.map((config) => {
                const Icon = config.icon;
                return (
                  <button
                    key={config.subject}
                    onClick={() => startExam(config)}
                    disabled={loading}
                    className={`p-6 rounded-xl border-2 text-left transition-all hover:shadow-lg hover:-translate-y-1 disabled:opacity-50 disabled:cursor-not-allowed ${config.bgColor} border-transparent hover:border-current ${config.color}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`p-3 bg-white rounded-xl shadow-sm`}>
                        <Icon className={`w-6 h-6 ${config.color}`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {config.name}
                        </h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                          <span className="flex items-center gap-1">
                            <BookOpen className="w-4 h-4" />
                            {config.questions} questions
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {config.timeMinutes} mins
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <div className="flex gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-amber-800">Exam Conditions</h3>
                <ul className="mt-2 text-sm text-amber-700 space-y-1">
                  <li>- The timer will start once you begin the exam</li>
                  <li>- You can flag questions to review later</li>
                  <li>- Navigate between questions using the question navigator</li>
                  <li>- The exam will auto-submit when time runs out</li>
                </ul>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Ready screen
  if (examState === "ready" && selectedExam) {
    const Icon = selectedExam.icon;
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-xl border p-8 max-w-md text-center">
          <div className={`w-16 h-16 ${selectedExam.bgColor} rounded-full flex items-center justify-center mx-auto mb-4`}>
            <Icon className={`w-8 h-8 ${selectedExam.color}`} />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {selectedExam.name} Mock Exam
          </h2>
          <p className="text-gray-600 mb-6">
            {questions.length} questions in {selectedExam.timeMinutes} minutes
          </p>

          <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
            <h3 className="font-medium text-gray-900 mb-2">Before you begin:</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Find a quiet place without distractions</li>
              <li>- Have a pen and paper ready for working out</li>
              <li>- The timer cannot be paused once started</li>
            </ul>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setExamState("select")}
              className="flex-1 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Go Back
            </button>
            <button
              onClick={beginExam}
              className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" />
              Start Exam
            </button>
          </div>
        </div>
      </div>
    );
  }

  // In progress screen
  if (examState === "in-progress" && currentQuestion && selectedExam) {
    const isLowTime = timeRemaining < 300; // Less than 5 minutes

    return (
      <div className="min-h-screen bg-gray-50">
        {/* Exam header with timer */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <selectedExam.icon className={`w-5 h-5 ${selectedExam.color}`} />
                <span className="font-medium text-gray-900">
                  {selectedExam.name} Mock Exam
                </span>
              </div>

              <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${isLowTime ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-700"}`}>
                <Clock className="w-4 h-4" />
                <span className="font-mono font-medium">
                  {formatTime(timeRemaining)}
                </span>
              </div>

              <button
                onClick={() => {
                  if (confirm("Are you sure you want to submit your exam?")) {
                    handleSubmitExam();
                  }
                }}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                Submit Exam
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Question navigator */}
          <div className="bg-white rounded-xl border p-4 mb-6">
            <div className="flex flex-wrap gap-2">
              {questions.map((q, idx) => (
                <button
                  key={q.id}
                  onClick={() => setCurrentIndex(idx)}
                  className={`w-10 h-10 rounded-lg font-medium text-sm transition-colors ${
                    idx === currentIndex
                      ? "bg-indigo-600 text-white"
                      : answers[q.id]
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  } ${flagged.has(q.id) ? "ring-2 ring-amber-400" : ""}`}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-emerald-100 rounded" /> Answered
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-gray-100 rounded" /> Unanswered
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-gray-100 rounded ring-2 ring-amber-400" /> Flagged
              </span>
            </div>
          </div>

          {/* Current question */}
          <div className="bg-white rounded-xl border p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-500">
                Question {currentIndex + 1} of {questions.length}
              </span>
              <button
                onClick={() => toggleFlag(currentQuestion.id)}
                className={`flex items-center gap-1 px-3 py-1 rounded-lg text-sm ${
                  flagged.has(currentQuestion.id)
                    ? "bg-amber-100 text-amber-700"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <Flag className="w-4 h-4" />
                {flagged.has(currentQuestion.id) ? "Flagged" : "Flag"}
              </button>
            </div>

            {/* Question content */}
            {currentQuestion.content.passage && (
              <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm text-gray-700">
                {currentQuestion.content.passage}
              </div>
            )}

            <p className="text-lg text-gray-900 mb-6">
              {currentQuestion.content.text}
            </p>

            {/* Options */}
            {currentQuestion.content.options && (
              <div className="space-y-3">
                {currentQuestion.content.options.map((option, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleAnswer(currentQuestion.id, option)}
                    className={`w-full p-4 rounded-lg border-2 text-left transition-colors ${
                      answers[currentQuestion.id] === option
                        ? "border-indigo-600 bg-indigo-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <span className="font-medium text-gray-500 mr-3">
                      {String.fromCharCode(65 + idx)}.
                    </span>
                    {option}
                  </button>
                ))}
              </div>
            )}

            {/* Text input for non-multiple choice */}
            {!currentQuestion.content.options && (
              <input
                type="text"
                value={answers[currentQuestion.id] || ""}
                onChange={(e) => handleAnswer(currentQuestion.id, e.target.value)}
                placeholder="Type your answer..."
                className="w-full p-4 border-2 border-gray-200 rounded-lg focus:border-indigo-600 focus:outline-none"
              />
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6 pt-6 border-t">
              <button
                onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                disabled={currentIndex === 0}
                className="flex items-center gap-1 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>

              <button
                onClick={() =>
                  setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))
                }
                disabled={currentIndex === questions.length - 1}
                className="flex items-center gap-1 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Completed screen
  if (examState === "completed" && result && selectedExam) {
    const percentage = Math.round(result.accuracy * 100);
    const passed = percentage >= 70;

    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Exam Complete</h1>
                <p className="text-sm text-gray-500">{selectedExam.name} Mock Exam</p>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-xl border p-8 text-center mb-6">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 ${passed ? "bg-emerald-100" : "bg-amber-100"}`}>
              {passed ? (
                <CheckCircle className="w-10 h-10 text-emerald-600" />
              ) : (
                <XCircle className="w-10 h-10 text-amber-600" />
              )}
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {passed ? "Great Work!" : "Keep Practising!"}
            </h2>

            <p className="text-gray-600 mb-6">
              You scored {result.correct_answers} out of {result.total_questions} questions
            </p>

            <div className="text-5xl font-bold mb-2">
              <span className={passed ? "text-emerald-600" : "text-amber-600"}>
                {percentage}%
              </span>
            </div>

            <p className="text-sm text-gray-500">
              Time taken: {Math.round(result.time_taken_minutes)} minutes
            </p>
          </div>

          {/* Stats breakdown */}
          <div className="bg-white rounded-xl border p-6 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">Performance Summary</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-emerald-50 rounded-lg p-4">
                <p className="text-2xl font-bold text-emerald-600">
                  {result.correct_answers}
                </p>
                <p className="text-sm text-gray-600">Correct</p>
              </div>
              <div className="bg-red-50 rounded-lg p-4">
                <p className="text-2xl font-bold text-red-600">
                  {result.total_questions - result.correct_answers}
                </p>
                <p className="text-sm text-gray-600">Incorrect</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-2xl font-bold text-gray-600">
                  {result.total_questions}
                </p>
                <p className="text-sm text-gray-600">Total</p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Link
              href="/"
              className="flex-1 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-center"
            >
              Back to Home
            </Link>
            <button
              onClick={() => {
                setExamState("select");
                setResult(null);
                setQuestions([]);
                setAnswers({});
              }}
              className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Try Another Exam
            </button>
          </div>
        </main>
      </div>
    );
  }

  // Loading state
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading exam...</p>
      </div>
    </div>
  );
}
