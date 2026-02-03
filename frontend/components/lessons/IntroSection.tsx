"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface IntroSectionProps {
  heading: string;
  body: string;
  visual?: {
    type: "mermaid";
    code: string;
  };
}

export function IntroSection({ heading, body, visual }: IntroSectionProps) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.1 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (visible && visual?.type === "mermaid" && mermaidRef.current) {
      import("mermaid").then((m) => {
        m.default.initialize({ startOnLoad: false, theme: "neutral" });
        mermaidRef.current!.innerHTML = visual.code;
        m.default.run({ nodes: [mermaidRef.current!] });
      });
    }
  }, [visible, visual]);

  return (
    <div
      ref={ref}
      className={cn(
        "transition-all duration-700",
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
      )}
    >
      <h2 className="text-2xl font-heading font-bold text-slate-900 mb-4">{heading}</h2>
      <div
        className="prose prose-slate max-w-none text-slate-600 leading-relaxed mb-6"
        dangerouslySetInnerHTML={{ __html: body }}
      />
      {visual?.type === "mermaid" && (
        <div className="bg-slate-50 rounded-xl p-6 border border-slate-100">
          <div ref={mermaidRef} className="mermaid flex justify-center" />
        </div>
      )}
    </div>
  );
}
