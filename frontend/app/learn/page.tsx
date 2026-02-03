"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Loader2, ChevronRight } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { lessonsAPI } from "@/lib/api";
import { getSubjectDisplayName } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface LessonSummary {
  subject: string;
  questionType: string;
  title: string;
  subtitle: string;
  difficulty: string;
  color: string;
  sectionCount: number;
}

const SUBJECT_ORDER = ["english", "maths", "verbal_reasoning", "non_verbal_reasoning"];

const SUBJECT_STYLES: Record<string, { accent: string; bg: string; border: string; icon: string }> = {
  english: { accent: "text-green-600", bg: "bg-green-50", border: "border-green-200", icon: "📖" },
  maths: { accent: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200", icon: "📐" },
  verbal_reasoning: { accent: "text-purple-600", bg: "bg-purple-50", border: "border-purple-200", icon: "🗣️" },
  non_verbal_reasoning: { accent: "text-orange-600", bg: "bg-orange-50", border: "border-orange-200", icon: "🧩" },
};

export default function LearnPage() {
  const [lessons, setLessons] = useState<LessonSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await lessonsAPI.list();
        setLessons(data);
      } catch (e) {
        console.error("Failed to load lessons:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Group lessons by subject
  const grouped = SUBJECT_ORDER.reduce<Record<string, LessonSummary[]>>((acc, subj) => {
    acc[subj] = lessons.filter((l) => l.subject === subj);
    return acc;
  }, {});

  return (
    <div className="flex h-[100dvh] w-full bg-slate-50/50 overflow-hidden">
      <Sidebar />

      <main className="flex-grow flex flex-col relative overflow-y-auto h-full px-4 py-8 pb-32 lg:pb-8">
        {/* Header */}
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 px-4 lg:px-8 flex items-center justify-between z-10 sticky top-0 flex-shrink-0 rounded-xl mb-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-slate-400 hover:text-slate-600 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h2 className="text-xl font-heading font-bold text-slate-800">Learn</h2>
              <p className="text-xs text-slate-500 font-medium">
                Interactive lessons for every question type
              </p>
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-600 flex items-center justify-center text-xl">
            <BookOpen className="w-5 h-5" />
          </div>
        </header>

        <div className="flex-grow overflow-y-auto relative scroll-smooth">
          <div className="max-w-6xl mx-auto animate-fade-in-up">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
              </div>
            ) : lessons.length === 0 ? (
              <div className="text-center py-20">
                <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-slate-700 mb-2">No lessons available yet</h3>
                <p className="text-sm text-slate-500">Lessons are being prepared. Check back soon.</p>
              </div>
            ) : (
              <div className="space-y-10">
                {SUBJECT_ORDER.map((subject) => {
                  const subjectLessons = grouped[subject];
                  if (!subjectLessons || subjectLessons.length === 0) return null;

                  const style = SUBJECT_STYLES[subject];

                  return (
                    <section key={subject}>
                      <div className="flex items-center gap-3 mb-4">
                        <span className="text-2xl">{style.icon}</span>
                        <h3 className="text-xl font-heading font-bold text-slate-900">
                          {getSubjectDisplayName(subject)}
                        </h3>
                        <span className="text-sm text-slate-400 font-medium">
                          {subjectLessons.length} lesson{subjectLessons.length !== 1 ? "s" : ""}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {subjectLessons.map((lesson) => (
                          <Link
                            key={`${lesson.subject}-${lesson.questionType}`}
                            href={`/learn/${lesson.subject}/${lesson.questionType}`}
                            className={cn(
                              "group bg-white rounded-xl border p-4 hover:shadow-md transition-all duration-200",
                              style.border,
                              "hover:border-primary-300"
                            )}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-bold text-slate-800 group-hover:text-primary-600 transition-colors truncate">
                                  {lesson.title}
                                </h4>
                                <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                                  {lesson.subtitle}
                                </p>
                              </div>
                              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 transition-colors flex-shrink-0 mt-1" />
                            </div>
                            <div className="flex items-center gap-2 mt-3">
                              <span className={cn("text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full", style.bg, style.accent)}>
                                {lesson.difficulty}
                              </span>
                              <span className="text-[10px] text-slate-400">
                                {lesson.sectionCount} sections
                              </span>
                            </div>
                          </Link>
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      <div className="lg:hidden fixed bottom-0 w-full bg-white border-t border-slate-200 flex justify-around items-center h-16 pb-safe z-50 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <Link href="/" className="flex flex-col items-center justify-center w-full h-full text-slate-400 hover:text-primary-600">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
          <span className="text-[10px] font-medium mt-1">Dash</span>
        </Link>
        <Link href="/learn" className="flex flex-col items-center justify-center w-full h-full text-teal-600">
          <BookOpen className="w-5 h-5" />
          <span className="text-[10px] font-bold mt-1">Learn</span>
        </Link>
        <Link href="/practice/maths" className="flex flex-col items-center justify-center w-full h-full text-slate-400 hover:text-blue-600">
          <div className="text-lg mb-1">📐</div>
          <span className="text-[10px] font-medium">Maths</span>
        </Link>
        <Link href="/practice/verbal_reasoning" className="flex flex-col items-center justify-center w-full h-full text-slate-400 hover:text-purple-600">
          <div className="text-lg mb-1">🗣️</div>
          <span className="text-[10px] font-medium">Verbal</span>
        </Link>
        <Link href="/mock-exam" className="flex flex-col items-center justify-center w-full h-full text-slate-400 hover:text-indigo-600">
          <div className="text-lg mb-1">📝</div>
          <span className="text-[10px] font-medium">Exam</span>
        </Link>
      </div>
    </div>
  );
}
