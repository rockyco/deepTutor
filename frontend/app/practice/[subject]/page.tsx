"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  Lightbulb,
  ChevronRight,
  RotateCcw,
  Trophy,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getSubjectDisplayName,
  getSubjectColor,
  getSubjectBgColor,
  getQuestionTypeDisplayName,
  getDifficultyLabel,
  formatTime,
} from "@/lib/utils";
import type { Question, AnswerResult, Hint } from "@/lib/api";
import { questionsAPI } from "@/lib/api";

interface PracticeState {
  questions: Question[];
  currentIndex: number;
  answers: Map<string, { answer: string; result: AnswerResult }>;
  hintsUsed: Map<string, number>;
  startTime: number;
  currentQuestionTime: number;
}

export default function PracticePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const subject = params.subject as string;
  const questionType = searchParams.get("type");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [practice, setPractice] = useState<PracticeState | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [currentResult, setCurrentResult] = useState<AnswerResult | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [currentHints, setCurrentHints] = useState<Hint[]>([]);
  const [timer, setTimer] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);

  // Load questions
  useEffect(() => {
    async function loadQuestions() {
      try {
        setLoading(true);
        const questions = await questionsAPI.getQuestions({
          subject: subject as any,
          question_type: questionType as any,
          limit: 10,
        });

        if (questions.length === 0) {
          setError("No questions available for this subject yet.");
          return;
        }

        setPractice({
          questions,
          currentIndex: 0,
          answers: new Map(),
          hintsUsed: new Map(),
          startTime: Date.now(),
          currentQuestionTime: 0,
        });
      } catch (err) {
        setError("Failed to load questions. Is the backend running?");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadQuestions();
  }, [subject, questionType]);

  // Timer
  useEffect(() => {
    if (!practice || sessionComplete) return;

    const interval = setInterval(() => {
      setTimer((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [practice, sessionComplete]);

  const currentQuestion = practice?.questions[practice.currentIndex];

  const handleSelectAnswer = (answer: string) => {
    if (showResult) return;
    setSelectedAnswer(answer);
  };

  const handleSubmitAnswer = async () => {
    if (!selectedAnswer || !currentQuestion || !practice) return;

    try {
      const hintsUsed = practice.hintsUsed.get(currentQuestion.id) || 0;
      const result = await questionsAPI.checkAnswer(
        currentQuestion.id,
        selectedAnswer,
        hintsUsed
      );

      setCurrentResult(result);
      setShowResult(true);

      // Save answer
      setPractice((prev) => {
        if (!prev) return prev;
        const newAnswers = new Map(prev.answers);
        newAnswers.set(currentQuestion.id, { answer: selectedAnswer, result });
        return { ...prev, answers: newAnswers };
      });
    } catch (err) {
      console.error("Failed to check answer:", err);
    }
  };

  const handleGetHint = async () => {
    if (!currentQuestion || !practice) return;

    const currentLevel = (practice.hintsUsed.get(currentQuestion.id) || 0) + 1;
    if (currentLevel > 3) return;

    try {
      const hints = await questionsAPI.getHints(currentQuestion.id, currentLevel);
      setCurrentHints(hints);
      setShowHint(true);

      setPractice((prev) => {
        if (!prev) return prev;
        const newHintsUsed = new Map(prev.hintsUsed);
        newHintsUsed.set(currentQuestion.id, currentLevel);
        return { ...prev, hintsUsed: newHintsUsed };
      });
    } catch (err) {
      console.error("Failed to get hints:", err);
    }
  };

  const handleNextQuestion = () => {
    if (!practice) return;

    if (practice.currentIndex >= practice.questions.length - 1) {
      setSessionComplete(true);
      return;
    }

    setPractice((prev) => {
      if (!prev) return prev;
      return { ...prev, currentIndex: prev.currentIndex + 1 };
    });
    setSelectedAnswer(null);
    setShowResult(false);
    setCurrentResult(null);
    setShowHint(false);
    setCurrentHints([]);
  };

  const handleRestart = useCallback(async () => {
    // Fetch new randomized questions from the backend
    setLoading(true);
    setSessionComplete(false);
    setSelectedAnswer(null);
    setShowResult(false);
    setCurrentResult(null);
    setShowHint(false);
    setCurrentHints([]);
    setTimer(0);

    try {
      const questions = await questionsAPI.getQuestions({
        subject: subject as any,
        question_type: questionType as any,
        limit: 10,
      });

      if (questions.length === 0) {
        setError("No questions available for this subject yet.");
        return;
      }

      setPractice({
        questions,
        currentIndex: 0,
        answers: new Map(),
        hintsUsed: new Map(),
        startTime: Date.now(),
        currentQuestionTime: 0,
      });
    } catch (err) {
      setError("Failed to load questions. Is the backend running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [subject, questionType]);

  // Calculate results
  const getResults = () => {
    if (!practice) return { correct: 0, total: 0, accuracy: 0 };
    const answers = Array.from(practice.answers.values());
    const correct = answers.filter((a) => a.result.is_correct).length;
    return {
      correct,
      total: answers.length,
      accuracy: answers.length > 0 ? (correct / answers.length) * 100 : 0,
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading questions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Unable to Load Questions
          </h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  // Session Complete Screen
  if (sessionComplete && practice) {
    const results = getResults();
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-12">
          <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
            <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Trophy className="w-10 h-10 text-indigo-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Practice Complete!
            </h1>
            <p className="text-gray-600 mb-8">
              Great job on completing this practice session.
            </p>

            <div className="grid grid-cols-3 gap-4 mb-8">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-gray-900">
                  {results.correct}/{results.total}
                </div>
                <div className="text-sm text-gray-500">Correct</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-gray-900">
                  {Math.round(results.accuracy)}%
                </div>
                <div className="text-sm text-gray-500">Accuracy</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-3xl font-bold text-gray-900">
                  {formatTime(timer)}
                </div>
                <div className="text-sm text-gray-500">Time</div>
              </div>
            </div>

            {results.accuracy >= 80 ? (
              <p className="text-green-600 mb-6">
                Excellent work! You've mastered this topic.
              </p>
            ) : results.accuracy >= 50 ? (
              <p className="text-yellow-600 mb-6">
                Good effort! Keep practicing to improve.
              </p>
            ) : (
              <p className="text-orange-600 mb-6">
                Keep practicing! Review the explanations to learn from mistakes.
              </p>
            )}

            <div className="flex gap-4 justify-center">
              <button
                onClick={handleRestart}
                className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <RotateCcw className="w-4 h-4" />
                Practice Again
              </button>
              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!currentQuestion || !practice) return null;

  const hintsUsedCount = practice.hintsUsed.get(currentQuestion.id) || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </Link>
            <div className="flex items-center gap-4">
              <span
                className={cn(
                  "px-3 py-1 rounded-full text-sm font-medium",
                  getSubjectBgColor(subject),
                  "text-gray-700"
                )}
              >
                {getSubjectDisplayName(subject)}
              </span>
              <div className="flex items-center gap-2 text-gray-600">
                <Clock className="w-4 h-4" />
                <span className="font-mono">{formatTime(timer)}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
            <span>
              Question {practice.currentIndex + 1} of {practice.questions.length}
            </span>
            <span>{getResults().correct} correct so far</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-600 transition-all duration-300"
              style={{
                width: `${((practice.currentIndex + 1) / practice.questions.length) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Question Card */}
        <div
          className={cn(
            "bg-white rounded-2xl shadow-lg p-8 mb-6",
            showResult && currentResult?.is_correct && "ring-2 ring-green-500",
            showResult && !currentResult?.is_correct && "ring-2 ring-red-500"
          )}
        >
          {/* Question Type Badge */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              {getQuestionTypeDisplayName(currentQuestion.question_type)}
            </span>
            <span className="text-xs text-gray-400">
              - {getDifficultyLabel(currentQuestion.difficulty)}
            </span>
          </div>

          {/* Passage (for comprehension) */}
          {currentQuestion.content.passage && (
            <div className="bg-gray-50 rounded-lg p-4 mb-6 border-l-4 border-sky-500">
              <p className="text-gray-700 whitespace-pre-line">
                {currentQuestion.content.passage}
              </p>
            </div>
          )}

          {/* Question Text */}
          <h2 className="text-lg font-medium text-gray-900 mb-6 whitespace-pre-line">
            {currentQuestion.content.text}
          </h2>

          {/* Answer Options */}
          {currentQuestion.content.options ? (
            <div className="space-y-3">
              {currentQuestion.content.options.map((option, index) => {
                const isSelected = selectedAnswer === option;
                const isCorrect =
                  showResult && String(currentResult?.correct_answer) === option;
                const isWrong = showResult && isSelected && !currentResult?.is_correct;

                return (
                  <button
                    key={index}
                    onClick={() => handleSelectAnswer(option)}
                    disabled={showResult}
                    className={cn(
                      "w-full text-left p-4 rounded-lg border-2 transition-all",
                      !showResult && !isSelected && "border-gray-200 hover:border-gray-300",
                      !showResult && isSelected && "border-indigo-500 bg-indigo-50",
                      isCorrect && "border-green-500 bg-green-50",
                      isWrong && "border-red-500 bg-red-50"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                          !showResult && !isSelected && "bg-gray-100 text-gray-600",
                          !showResult && isSelected && "bg-indigo-500 text-white",
                          isCorrect && "bg-green-500 text-white",
                          isWrong && "bg-red-500 text-white"
                        )}
                      >
                        {String.fromCharCode(65 + index)}
                      </span>
                      <span className="flex-1">{option}</span>
                      {isCorrect && <CheckCircle2 className="w-5 h-5 text-green-600" />}
                      {isWrong && <XCircle className="w-5 h-5 text-red-600" />}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            // Fill in the blank
            <div>
              <input
                type="text"
                value={selectedAnswer || ""}
                onChange={(e) => setSelectedAnswer(e.target.value)}
                disabled={showResult}
                placeholder="Type your answer here..."
                className={cn(
                  "w-full p-4 border-2 rounded-lg text-lg",
                  !showResult && "border-gray-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200",
                  showResult && currentResult?.is_correct && "border-green-500 bg-green-50",
                  showResult && !currentResult?.is_correct && "border-red-500 bg-red-50"
                )}
              />
              {showResult && !currentResult?.is_correct && (
                <p className="mt-2 text-sm text-gray-600">
                  Correct answer:{" "}
                  <span className="font-medium text-green-600">
                    {String(currentResult?.correct_answer)}
                  </span>
                </p>
              )}
            </div>
          )}

          {/* Hint Section */}
          {showHint && currentHints.length > 0 && (
            <div className="mt-6 bg-yellow-50 rounded-lg p-4 border border-yellow-200">
              <h3 className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Hint {hintsUsedCount}
              </h3>
              {currentHints.map((hint, i) => (
                <p key={i} className="text-yellow-700">
                  {hint.text}
                </p>
              ))}
            </div>
          )}

          {/* Result Explanation */}
          {showResult && currentResult && (
            <div
              className={cn(
                "mt-6 rounded-lg p-4",
                currentResult.is_correct ? "bg-green-50" : "bg-blue-50"
              )}
            >
              <h3
                className={cn(
                  "font-medium mb-2",
                  currentResult.is_correct ? "text-green-800" : "text-blue-800"
                )}
              >
                {currentResult.feedback}
              </h3>
              <p className="text-gray-700">{currentResult.explanation}</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleGetHint}
            disabled={showResult || hintsUsedCount >= 3}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
              hintsUsedCount >= 3 || showResult
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
            )}
          >
            <Lightbulb className="w-4 h-4" />
            Get Hint ({3 - hintsUsedCount} left)
          </button>

          <div className="flex gap-3">
            {!showResult ? (
              <button
                onClick={handleSubmitAnswer}
                disabled={!selectedAnswer}
                className={cn(
                  "inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium",
                  selectedAnswer
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                )}
              >
                Check Answer
              </button>
            ) : (
              <button
                onClick={handleNextQuestion}
                className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium"
              >
                {practice.currentIndex >= practice.questions.length - 1
                  ? "See Results"
                  : "Next Question"}
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
