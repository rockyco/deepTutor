"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { Question } from "@/lib/api";
import { ProgressBar } from "./ProgressBar";
import { IntroSection } from "./IntroSection";
import { StrategySteps } from "./StrategySteps";
import { WorkedExample } from "./WorkedExample";
import { PracticeSection } from "./PracticeSection";
import { TipsSection } from "./TipsSection";
import { AssessmentSection } from "./AssessmentSection";

// Section type definitions matching lesson JSON schema
interface LessonSection {
  type: string;
  heading: string;
  body?: string;
  visual?: { type: "mermaid"; code: string } | {
    type: "flowchart";
    direction: "TD" | "LR";
    nodes: { id: string; label: string; style?: string }[];
    edges: { from: string; to: string; label?: string }[];
    subgraphs?: { id: string; label: string; nodeIds: string[] }[];
  };
  steps?: { label: string; detail: string; icon: string }[];
  question?: { text: string; options: string[]; image_url?: string; option_images?: string[] };
  walkthrough?: { step: number; text: string; highlight: string }[];
  answer?: string;
  items?: { trap: string; fix: string }[];
  questions?: string[];
}

interface LessonData {
  questionType: string;
  title: string;
  subtitle: string;
  subject: string;
  difficulty: string;
  color: string;
  sections: LessonSection[];
}

interface LessonRendererProps {
  lesson: LessonData;
  practiceQuestions: Question[];
  assessmentQuestions: Question[];
}

const SECTION_LABELS: Record<string, string> = {
  intro: "Intro",
  strategy: "Strategy",
  worked_example: "Example",
  practice: "Practice",
  tips: "Tips",
  assessment: "Quiz",
};

export function LessonRenderer({ lesson, practiceQuestions, assessmentQuestions }: LessonRendererProps) {
  const [currentSection, setCurrentSection] = useState(0);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);

  const sections = lesson.sections;
  const sectionLabels = sections.map((s) => SECTION_LABELS[s.type] || s.type);

  // Track scroll position to update progress bar
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = sectionRefs.current.indexOf(entry.target as HTMLDivElement);
            if (idx >= 0) setCurrentSection(idx);
          }
        }
      },
      { threshold: 0.3 }
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    return () => observer.disconnect();
  }, [sections.length]);

  const scrollToSection = useCallback((index: number) => {
    sectionRefs.current[index]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const renderSection = (section: LessonSection, index: number) => {
    switch (section.type) {
      case "intro":
        return (
          <IntroSection
            heading={section.heading}
            body={section.body || ""}
            visual={section.visual}
          />
        );

      case "strategy":
        return (
          <StrategySteps
            heading={section.heading}
            steps={section.steps || []}
          />
        );

      case "worked_example":
        return (
          <WorkedExample
            heading={section.heading}
            question={section.question || { text: "", options: [] }}
            walkthrough={section.walkthrough || []}
            answer={section.answer || ""}
          />
        );

      case "practice":
        return (
          <PracticeSection
            heading={section.heading}
            questions={practiceQuestions}
          />
        );

      case "tips":
        return (
          <TipsSection
            heading={section.heading}
            items={section.items || []}
          />
        );

      case "assessment":
        return (
          <AssessmentSection
            heading={section.heading}
            questions={assessmentQuestions}
            subject={lesson.subject}
            questionType={lesson.questionType}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50">
      <ProgressBar
        sections={sectionLabels}
        currentIndex={currentSection}
        onSectionClick={scrollToSection}
      />

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-16">
        {sections.map((section, i) => (
          <div
            key={i}
            ref={(el) => { sectionRefs.current[i] = el; }}
            className={cn(
              "scroll-mt-20",
              i > 0 && "pt-8 border-t border-slate-100"
            )}
          >
            {renderSection(section, i)}
          </div>
        ))}
      </div>
    </div>
  );
}
