"use client";

import { useState, useCallback } from "react";
import { CheckCircle2, XCircle, ArrowRight, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Question, AnswerResult } from "@/lib/api";
import { questionsAPI, getImageUrl, isImageUrl } from "@/lib/api";

interface PracticeSectionProps {
  heading: string;
  questions: Question[];
}

export function PracticeSection({ heading, questions }: PracticeSectionProps) {
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
        explanation: "Could not check answer. Try again.",
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

  if (questions.length === 0) {
    return (
      <div>
        <h2 className="text-2xl font-heading font-bold text-slate-900 mb-4">{heading}</h2>
        <p className="text-slate-500 italic">Practice questions will be available soon.</p>
      </div>
    );
  }

  if (isComplete) {
    const correct = scores.filter(Boolean).length;
    return (
      <div>
        <h2 className="text-2xl font-heading font-bold text-slate-900 mb-4">{heading}</h2>
        <div className="bg-white rounded-xl border border-slate-200 p-6 text-center">
          <div className="text-4xl font-bold text-primary-600 mb-2">
            {correct}/{scores.length}
          </div>
          <p className="text-slate-600">
            {correct === scores.length
              ? "Perfect score! You've mastered this."
              : correct >= scores.length / 2
                ? "Good effort! Review the ones you missed."
                : "Keep practising - you'll get there!"}
          </p>
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

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        {/* Question text */}
        <div className="text-slate-800 whitespace-pre-line leading-relaxed mb-4 font-medium">
          {question.content.text}
        </div>

        {/* Question image */}
        {question.content.image_url && (
          <div className="mb-4">
            <img
              src={getImageUrl(question.content.image_url)}
              alt="Question"
              className="max-h-48 rounded-lg"
            />
          </div>
        )}

        {/* Options */}
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
              if (isCorrectAnswer) optClass = "bg-green-50 border-green-300 ring-2 ring-green-200";
              else if (isWrongSelection) optClass = "bg-red-50 border-red-300 ring-2 ring-red-200";
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
                <span
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                    isSelected && !result ? "bg-primary-500 text-white" : "bg-slate-200 text-slate-600"
                  )}
                >
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

        {/* Actions */}
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
          <div className="space-y-3">
            {result.explanation && (
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                <Lightbulb className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-blue-800">{result.explanation}</p>
              </div>
            )}
            <button
              onClick={nextQuestion}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
