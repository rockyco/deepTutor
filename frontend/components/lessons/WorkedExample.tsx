"use client";

import { useState } from "react";
import { ChevronRight, CheckCircle2, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

interface WalkthroughStep {
  step: number;
  text: string;
  highlight: string;
}

interface WorkedExampleProps {
  heading: string;
  question: {
    text: string;
    options: string[];
  };
  walkthrough: WalkthroughStep[];
  answer: string;
}

export function WorkedExample({ heading, question, walkthrough, answer }: WorkedExampleProps) {
  const [currentStep, setCurrentStep] = useState(-1);
  const [showAnswer, setShowAnswer] = useState(false);

  const startWalkthrough = () => setCurrentStep(0);

  const nextStep = () => {
    if (currentStep < walkthrough.length - 1) {
      setCurrentStep((s) => s + 1);
    } else {
      setShowAnswer(true);
    }
  };

  const reset = () => {
    setCurrentStep(-1);
    setShowAnswer(false);
  };

  return (
    <div>
      <h2 className="text-2xl font-heading font-bold text-slate-900 mb-6">{heading}</h2>

      {/* Question display */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="text-slate-800 whitespace-pre-line leading-relaxed mb-4 font-medium">
          {question.text}
        </div>

        {/* Options */}
        <div className="space-y-2">
          {question.options.map((opt, i) => {
            const letter = String.fromCharCode(65 + i);
            const isAnswer = opt === answer;
            const isHighlighted = showAnswer && isAnswer;

            return (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-300",
                  isHighlighted
                    ? "bg-green-50 border-green-300 ring-2 ring-green-200"
                    : "bg-slate-50 border-slate-100"
                )}
              >
                <span
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                    isHighlighted
                      ? "bg-green-500 text-white"
                      : "bg-slate-200 text-slate-600"
                  )}
                >
                  {letter}
                </span>
                <span className={cn("text-sm", isHighlighted ? "font-bold text-green-800" : "text-slate-700")}>
                  {opt}
                </span>
                {isHighlighted && <CheckCircle2 className="w-5 h-5 text-green-500 ml-auto" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* Walkthrough */}
      {currentStep === -1 ? (
        <button
          onClick={startWalkthrough}
          className="flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          <Eye className="w-4 h-4" />
          Walk me through it
        </button>
      ) : (
        <div className="space-y-3">
          {walkthrough.slice(0, currentStep + 1).map((step, i) => (
            <div
              key={i}
              className={cn(
                "flex items-start gap-3 p-4 rounded-xl border animate-fade-in-up",
                i === currentStep ? "bg-primary-50 border-primary-200" : "bg-slate-50 border-slate-100"
              )}
            >
              <div className="w-7 h-7 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                {step.step}
              </div>
              <p className="text-sm text-slate-700 leading-relaxed">{step.text}</p>
            </div>
          ))}

          <div className="flex gap-3 mt-4">
            {!showAnswer ? (
              <button
                onClick={nextStep}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
              >
                {currentStep < walkthrough.length - 1 ? "Next Step" : "Show Answer"}
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg text-sm font-bold">
                <CheckCircle2 className="w-4 h-4" />
                Answer: {answer}
              </div>
            )}
            <button
              onClick={reset}
              className="px-4 py-2 text-slate-500 hover:text-slate-700 text-sm font-medium transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
