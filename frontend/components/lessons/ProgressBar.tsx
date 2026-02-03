"use client";

import { cn } from "@/lib/utils";

interface ProgressBarProps {
  sections: string[];
  currentIndex: number;
  onSectionClick: (index: number) => void;
}

export function ProgressBar({ sections, currentIndex, onSectionClick }: ProgressBarProps) {
  return (
    <div className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-center gap-1.5">
        {sections.map((section, i) => (
          <button
            key={i}
            onClick={() => onSectionClick(i)}
            className="flex-1 group relative"
            title={section}
          >
            <div
              className={cn(
                "h-2 rounded-full transition-all duration-300",
                i <= currentIndex
                  ? "bg-primary-500"
                  : "bg-slate-200 group-hover:bg-slate-300"
              )}
            />
            <span
              className={cn(
                "absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] font-medium whitespace-nowrap transition-opacity",
                i === currentIndex ? "opacity-100 text-primary-600" : "opacity-0 group-hover:opacity-100 text-slate-400"
              )}
            >
              {section}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
