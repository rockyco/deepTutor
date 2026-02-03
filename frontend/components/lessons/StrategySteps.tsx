"use client";

import { useState } from "react";
import {
  Eye,
  Link2,
  CheckCircle2,
  Brain,
  Search,
  Pencil,
  Puzzle,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  eye: Eye,
  link: Link2,
  check: CheckCircle2,
  brain: Brain,
  search: Search,
  pencil: Pencil,
  puzzle: Puzzle,
  lightbulb: Lightbulb,
};

interface Step {
  label: string;
  detail: string;
  icon: string;
}

interface StrategyStepsProps {
  heading: string;
  steps: Step[];
}

export function StrategySteps({ heading, steps }: StrategyStepsProps) {
  const [revealedCount, setRevealedCount] = useState(0);

  const revealNext = () => {
    if (revealedCount < steps.length) {
      setRevealedCount((c) => c + 1);
    }
  };

  const revealAll = () => setRevealedCount(steps.length);

  return (
    <div>
      <h2 className="text-2xl font-heading font-bold text-slate-900 mb-6">{heading}</h2>
      <div className="space-y-4">
        {steps.map((step, i) => {
          const Icon = ICONS[step.icon] || CheckCircle2;
          const isRevealed = i < revealedCount;

          return (
            <div
              key={i}
              className={cn(
                "flex items-start gap-4 p-4 rounded-xl border transition-all duration-500",
                isRevealed
                  ? "bg-white border-primary-200 shadow-sm"
                  : "bg-slate-50 border-slate-100 opacity-40 blur-[2px]"
              )}
            >
              <div
                className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                  isRevealed ? "bg-primary-100 text-primary-600" : "bg-slate-200 text-slate-400"
                )}
              >
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-slate-800">
                  Step {i + 1}: {step.label}
                </div>
                <p className="text-sm text-slate-600 mt-1">{step.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
      {revealedCount < steps.length ? (
        <div className="flex gap-3 mt-4">
          <button
            onClick={revealNext}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Reveal Step {revealedCount + 1}
          </button>
          <button
            onClick={revealAll}
            className="px-4 py-2 text-slate-500 hover:text-slate-700 text-sm font-medium transition-colors"
          >
            Show All
          </button>
        </div>
      ) : (
        <p className="text-sm text-green-600 font-medium mt-4">All steps revealed!</p>
      )}
    </div>
  );
}
