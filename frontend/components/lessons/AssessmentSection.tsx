"use client";

import { useState, useCallback } from "react";
import { CheckCircle2, XCircle, Trophy, ArrowRight, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Question, AnswerResult } from "@/lib/api";
import { questionsAPI, getImageUrl, isImageUrl } from "@/lib/api";
import Link from "next/link";

interface AssessmentSectionProps {
  heading: string;
  questions: Question[];
  subject: string;
  questionType: string;
}

export function AssessmentSection({ heading, questions, subject, questionType }: AssessmentSectionProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [scores, setScores] = useState<boolean[]>([]);

  const question = questions[currentIndex];
  const isComplete = currentIndex >= questions.length;

  const hasImageOptions = !isComplete && (
    (question?.content.option_images?.length ?? 0) > 0
    || (question?.content.options || []).some((opt) => isImageUrl(opt))
  );

  const checkAnswer = useCallback(async () => {
    if (!selectedAnswer || !question) return;
    setChecking(true);
    try {
      const res = await questionsAPI.checkAnswer(question.id, selectedAnswer);
      setResult(res);
      setScores((prev) => [...prev, res.is_correct]);
    } catch {
      setResult({
        is_correct: false,
        correct_answer: "",
        explanation: "Could not check answer.",
        score: 0,
        feedback: "",
      });
    }
    setChecking(false);
  }, [selectedAnswer, question]);

  const nextQuestion = () => {
    setCurrentIndex((i) => i + 1);
    setSelectedAnswer(null);
    setResult(null);
  };

  const restart = () => {
    setCurrentIndex(0);
    setSelectedAnswer(null);
    setResult(null);
    setScores([]);
  };

  if (questions.length === 0) {
    return (
      <div>
        <h2 className="text-2xl font-heading font-bold text-slate-900 mb-4">{heading}</h2>
        <p className="text-slate-500 italic">Assessment questions will be available soon.</p>
      </div>
    );
  }

  if (isComplete) {
    const correct = scores.filter(Boolean).length;
    const percentage = Math.round((correct / scores.length) * 100);
    const passed = percentage >= 60;

    return (
      <div>
        <h2 className="text-2xl font-heading font-bold text-slate-900 mb-4">{heading}</h2>
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <div className={cn("w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center", passed ? "bg-green-100" : "bg-amber-100")}>
            <Trophy className={cn("w-8 h-8", passed ? "text-green-600" : "text-amber-600")} />
          </div>
          <div className="text-5xl font-bold mb-2">
            <span className={passed ? "text-green-600" : "text-amber-600"}>{correct}</span>
            <span className="text-slate-300">/{scores.length}</span>
          </div>
          <p className="text-lg font-medium text-slate-700 mb-1">
            {passed ? "Well done!" : "Keep going!"}
          </p>
          <p className="text-sm text-slate-500 mb-6">
            {percentage === 100
              ? "Perfect score - you've nailed this question type!"
              : passed
                ? "Great work! Try a full practice session to build even more confidence."
                : "Review the lesson sections above and try again."}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={restart}
              className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Try Again
            </button>
            <Link
              href={`/practice/${subject}?type=${questionType}`}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              Full Practice
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-heading font-bold text-slate-900 mb-2">{heading}</h2>
      <p className="text-sm text-slate-500 mb-4">
        Question {currentIndex + 1} of {questions.length}
      </p>

      <div className="bg-white rounded-xl border-2 border-primary-100 p-6">
        <div className="text-slate-800 whitespace-pre-line leading-relaxed mb-4 font-medium">
          {question.content.text}
        </div>

        {question.content.image_url && (
          <div className="mb-4">
            <img
              src={getImageUrl(question.content.image_url)}
              alt="Question"
              className="max-h-48 rounded-lg"
            />
          </div>
        )}

        <div className={cn(
          hasImageOptions
            ? "grid grid-cols-2 sm:grid-cols-5 gap-4 mb-4"
            : "space-y-2 mb-4"
        )}>
          {(question.content.options || []).map((opt, i) => {
            const letter = String.fromCharCode(65 + i);
            const isSelected = selectedAnswer === opt;
            const isCorrectAnswer = result && String(result.correct_answer) === opt;
            const isWrongSelection = result && isSelected && !result.is_correct;

            let optClass = "bg-slate-50 border-slate-100 hover:border-primary-300 cursor-pointer";
            if (result) {
              if (isCorrectAnswer) optClass = "bg-green-50 border-green-300";
              else if (isWrongSelection) optClass = "bg-red-50 border-red-300";
              else optClass = "bg-slate-50 border-slate-100 opacity-60";
            } else if (isSelected) {
              optClass = "bg-primary-50 border-primary-300 ring-2 ring-primary-200";
            }

            const optionImage = question.content.option_images?.[i];
            const isImgOpt = !!optionImage || isImageUrl(opt);
            const displayImage = optionImage ? getImageUrl(optionImage) : getImageUrl(opt);

            return (
              <button
                key={i}
                onClick={() => !result && setSelectedAnswer(opt)}
                disabled={!!result}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-200 w-full text-left",
                  optClass
                )}
              >
                <span className="w-7 h-7 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {letter}
                </span>
                {isImgOpt ? (
                  <img src={displayImage} alt={`Option ${letter}`} className="max-h-24 object-contain" />
                ) : (
                  <span className="text-sm text-slate-700">{opt}</span>
                )}
                {result && isCorrectAnswer && <CheckCircle2 className="w-5 h-5 text-green-500 ml-auto" />}
                {result && isWrongSelection && <XCircle className="w-5 h-5 text-red-500 ml-auto" />}
              </button>
            );
          })}
        </div>

        {!result ? (
          <button
            onClick={checkAnswer}
            disabled={!selectedAnswer || checking}
            className={cn(
              "px-5 py-2.5 rounded-lg text-sm font-medium transition-colors",
              selectedAnswer
                ? "bg-primary-600 text-white hover:bg-primary-700"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            )}
          >
            {checking ? "Checking..." : "Check Answer"}
          </button>
        ) : (
          <button
            onClick={nextQuestion}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            {currentIndex < questions.length - 1 ? "Next Question" : "See Results"}
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
