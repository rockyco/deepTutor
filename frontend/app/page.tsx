"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Calculator,
  Brain,
  Shapes,
  Trophy,
  Target,
  Clock,
  ChevronRight,
} from "lucide-react";

const subjects = [
  {
    id: "english",
    name: "English",
    description: "Comprehension, grammar, spelling, and vocabulary",
    icon: BookOpen,
    color: "bg-sky-500",
    lightColor: "bg-sky-50",
    borderColor: "border-sky-500",
    questions: "49-56 questions",
    time: "50 minutes",
  },
  {
    id: "maths",
    name: "Maths",
    description: "Number operations, fractions, geometry, and word problems",
    icon: Calculator,
    color: "bg-emerald-500",
    lightColor: "bg-emerald-50",
    borderColor: "border-emerald-500",
    questions: "50 questions",
    time: "50 minutes",
  },
  {
    id: "verbal_reasoning",
    name: "Verbal Reasoning",
    description: "21 question types including codes, patterns, and word puzzles",
    icon: Brain,
    color: "bg-purple-500",
    lightColor: "bg-purple-50",
    borderColor: "border-purple-500",
    questions: "80 questions",
    time: "50-60 minutes",
  },
  {
    id: "non_verbal_reasoning",
    name: "Non-verbal Reasoning",
    description: "Sequences, patterns, rotation, reflection, and spatial awareness",
    icon: Shapes,
    color: "bg-orange-500",
    lightColor: "bg-orange-50",
    borderColor: "border-orange-500",
    questions: "~40 questions",
    time: "40 minutes",
  },
];

export default function Home() {
  const [userName, setUserName] = useState<string>("");
  const [showWelcome, setShowWelcome] = useState(true);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">11+ Deep Tutor</h1>
                <p className="text-sm text-gray-500">GL Assessment Preparation</p>
              </div>
            </div>
            <nav className="flex items-center gap-4">
              <Link
                href="/progress"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-100"
              >
                Progress
              </Link>
              <Link
                href="/mock-exam"
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
              >
                Mock Exam
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        {showWelcome && (
          <div className="mb-8 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 text-white">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-2">
                  Welcome to 11+ Deep Tutor!
                </h2>
                <p className="text-indigo-100 mb-4 max-w-2xl">
                  Master the GL Assessment 11+ exam with interactive practice questions,
                  detailed explanations, and progress tracking. Start with any subject
                  below to begin your journey to grammar school success.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    <span>Adaptive difficulty</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>Timed practice</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4" />
                    <span>Detailed explanations</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowWelcome(false)}
                className="text-indigo-200 hover:text-white"
              >
                <span className="sr-only">Close</span>
                &times;
              </button>
            </div>
          </div>
        )}

        {/* Subject Cards */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            Choose a Subject to Practice
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {subjects.map((subject) => (
              <Link
                key={subject.id}
                href={`/practice/${subject.id}`}
                className={`group relative overflow-hidden rounded-xl border-2 ${subject.borderColor} ${subject.lightColor} p-6 transition-all hover:shadow-lg hover:-translate-y-1`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`${subject.color} rounded-xl p-3 text-white shadow-lg`}
                  >
                    <subject.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                      {subject.name}
                    </h3>
                    <p className="text-gray-600 text-sm mb-3">
                      {subject.description}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        {subject.questions}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {subject.time}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Quick Practice Section */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            Quick Practice by Topic
          </h2>
          <div className="bg-white rounded-xl border p-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Verbal Reasoning Topics */}
              <div>
                <h3 className="text-sm font-medium text-purple-600 mb-3">
                  Verbal Reasoning
                </h3>
                <ul className="space-y-2">
                  {[
                    { name: "Synonyms", type: "vr_synonyms" },
                    { name: "Hidden Words", type: "vr_hidden_word" },
                    { name: "Number Series", type: "vr_number_series" },
                    { name: "Alphabet Codes", type: "vr_alphabet_code" },
                    { name: "Word Pairs", type: "vr_word_pairs" },
                  ].map((topic) => (
                    <li key={topic.name}>
                      <Link
                        href={`/practice/verbal_reasoning?type=${topic.type}`}
                        className="text-sm text-gray-600 hover:text-purple-600 flex items-center gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                        {topic.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Maths Topics */}
              <div>
                <h3 className="text-sm font-medium text-emerald-600 mb-3">
                  Maths
                </h3>
                <ul className="space-y-2">
                  {[
                    { name: "Fractions", type: "fractions" },
                    { name: "Percentages", type: "percentages" },
                    { name: "Geometry", type: "geometry" },
                    { name: "Word Problems", type: "word_problems" },
                    { name: "Algebra", type: "algebra" },
                  ].map((topic) => (
                    <li key={topic.name}>
                      <Link
                        href={`/practice/maths?type=${topic.type}`}
                        className="text-sm text-gray-600 hover:text-emerald-600 flex items-center gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        {topic.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* English Topics */}
              <div>
                <h3 className="text-sm font-medium text-sky-600 mb-3">English</h3>
                <ul className="space-y-2">
                  {[
                    "Comprehension",
                    "Grammar",
                    "Spelling",
                    "Vocabulary",
                  ].map((topic) => (
                    <li key={topic}>
                      <Link
                        href={`/practice/english?type=${topic.toLowerCase()}`}
                        className="text-sm text-gray-600 hover:text-sky-600 flex items-center gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                        {topic}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Non-verbal Reasoning Topics */}
              <div>
                <h3 className="text-sm font-medium text-orange-600 mb-3">
                  Non-verbal Reasoning
                </h3>
                <ul className="space-y-2">
                  {[
                    { label: "Sequences", type: "nvr_sequences" },
                    { label: "Odd One Out", type: "nvr_odd_one_out" },
                    { label: "Analogies", type: "nvr_analogies" },
                    { label: "Matrices", type: "nvr_matrices" },
                    { label: "Rotation", type: "nvr_rotation" },
                    { label: "Reflection", type: "nvr_reflection" },
                    { label: "Spatial 3D", type: "nvr_spatial_3d" },
                    { label: "Codes", type: "nvr_codes" },
                  ].map((topic) => (
                    <li key={topic.type}>
                      <Link
                        href={`/practice/non_verbal_reasoning?type=${topic.type}`}
                        className="text-sm text-gray-600 hover:text-orange-600 flex items-center gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                        {topic.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Exam Info */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            About the GL Assessment 11+
          </h2>
          <div className="bg-white rounded-xl border p-6">
            <p className="text-gray-600 mb-4">
              The GL Assessment 11+ exam is used by over 80% of grammar schools in
              England. It tests pupils in four key areas to assess their academic
              potential.
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Test Format</h4>
                <p className="text-sm text-gray-600">
                  Multiple choice answers marked on a separate answer sheet
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Timing</h4>
                <p className="text-sm text-gray-600">
                  Around 45-60 minutes per paper, varies by region
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Scoring</h4>
                <p className="text-sm text-gray-600">
                  Age-standardised scores ensure fairness across age groups
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">When</h4>
                <p className="text-sm text-gray-600">
                  Usually September/October of Year 6
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>11+ Deep Tutor - AI-powered exam preparation</p>
            <p className="mt-1">
              Designed for Year 5 students preparing for GL Assessment 11+ exams
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
