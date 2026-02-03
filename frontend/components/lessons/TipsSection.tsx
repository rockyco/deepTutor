"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";

interface Tip {
  trap: string;
  fix: string;
}

interface TipsSectionProps {
  heading: string;
  items: Tip[];
}

export function TipsSection({ heading, items }: TipsSectionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (i: number) => {
    setOpenIndex(openIndex === i ? null : i);
  };

  return (
    <div>
      <h2 className="text-2xl font-heading font-bold text-slate-900 mb-6">{heading}</h2>
      <div className="space-y-3">
        {items.map((item, i) => (
          <div
            key={i}
            className="bg-white rounded-xl border border-slate-200 overflow-hidden transition-shadow hover:shadow-sm"
          >
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center gap-3 px-5 py-4 text-left"
            >
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
              <span className="font-medium text-slate-800 flex-1">{item.trap}</span>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-slate-400 transition-transform duration-200",
                  openIndex === i && "rotate-180"
                )}
              />
            </button>
            <div
              className={cn(
                "overflow-hidden transition-all duration-300",
                openIndex === i ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
              )}
            >
              <div className="px-5 pb-4 flex items-start gap-3">
                <Lightbulb className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-slate-600">{item.fix}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
