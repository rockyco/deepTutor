"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, BookOpen, Loader2 } from "lucide-react";
import { lessonsAPI } from "@/lib/api";
import { questionsAPI } from "@/lib/api";
import { getSubjectDisplayName, getQuestionTypeDisplayName } from "@/lib/utils";
import { LessonRenderer } from "@/components/lessons/LessonRenderer";
import type { Question } from "@/lib/api";

interface LessonData {
  questionType: string;
  title: string;
  subtitle: string;
  subject: string;
  difficulty: string;
  color: string;
  sections: any[];
}

export default function LessonClient() {
  const params = useParams();
  const subject = params.subject as string;
  const type = params.type as string;

  const [lesson, setLesson] = useState<LessonData | null>(null);
  const [practiceQuestions, setPracticeQuestions] = useState<Question[]>([]);
  const [assessmentQuestions, setAssessmentQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await lessonsAPI.get(subject, type);
        setLesson(data);

        // Load practice questions for this type
        try {
          const qs = await questionsAPI.getQuestions({
            subject: subject as any,
            question_type: type as any,
            limit: 5,
          });
          // Split: first 3 for practice, last 2 for assessment
          setPracticeQuestions(qs.slice(0, 3));
          setAssessmentQuestions(qs.slice(3, 5));
        } catch {
          // Questions may not be available - that's okay
        }
      } catch (e: any) {
        setError(e.message || "Failed to load lesson");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [subject, type]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50/50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading lesson...</p>
        </div>
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50/50">
        <div className="text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-800 mb-2">Lesson not found</h2>
          <p className="text-sm text-slate-500 mb-4">{error || "This lesson is not available yet."}</p>
          <Link
            href="/learn"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Lessons
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <Link
            href="/learn"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-primary-600 transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            All Lessons
          </Link>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-primary-600">
              {getSubjectDisplayName(subject)}
            </span>
            <span className="text-xs text-slate-300">/</span>
            <span className="text-xs font-medium text-slate-500">
              {getQuestionTypeDisplayName(type)}
            </span>
          </div>
          <h1 className="text-2xl font-heading font-bold text-slate-900">{lesson.title}</h1>
          <p className="text-sm text-slate-500 mt-1">{lesson.subtitle}</p>
        </div>
      </div>

      <LessonRenderer
        lesson={lesson}
        practiceQuestions={practiceQuestions}
        assessmentQuestions={assessmentQuestions}
      />
    </div>
  );
}
