"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Trophy,
  BookOpen,
  Calculator,
  Brain,
  Shapes,
  TrendingUp,
  TrendingDown,
  Target,
  Clock,
  CheckCircle,
  XCircle,
  ChevronLeft,
  BarChart3,
  Flame,
} from "lucide-react";
import { progressAPI, usersAPI, User, ProgressSummary } from "@/lib/api";

const subjectConfig: Record<string, { icon: typeof BookOpen; color: string; bgColor: string }> = {
  english: { icon: BookOpen, color: "text-sky-600", bgColor: "bg-sky-100" },
  maths: { icon: Calculator, color: "text-emerald-600", bgColor: "bg-emerald-100" },
  verbal_reasoning: { icon: Brain, color: "text-purple-600", bgColor: "bg-purple-100" },
  non_verbal_reasoning: { icon: Shapes, color: "text-orange-600", bgColor: "bg-orange-100" },
};

function formatSubjectName(subject: string): string {
  return subject
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function ProgressPage() {
  const [user, setUser] = useState<User | null>(null);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProgress() {
      try {
        // Get or create demo user
        let users = await usersAPI.listUsers();
        let currentUser = users[0];

        if (!currentUser) {
          currentUser = await usersAPI.createUser("Student", 5, []);
        }

        setUser(currentUser);

        // Load progress
        const progressData = await progressAPI.getSummary(currentUser.id);
        setProgress(progressData);
      } catch (err) {
        setError("Unable to load progress data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadProgress();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your progress...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </Link>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Your Progress</h1>
                <p className="text-sm text-gray-500">Track your 11+ preparation</p>
              </div>
            </div>
            <Link
              href="/mock-exam"
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              Take Mock Exam
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <p className="text-red-700">{error}</p>
            <Link
              href="/"
              className="mt-4 inline-block text-red-600 hover:text-red-800"
            >
              Return to Home
            </Link>
          </div>
        ) : (
          <>
            {/* Overview Stats */}
            <section className="mb-8">
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                      <Target className="w-5 h-5 text-indigo-600" />
                    </div>
                    <span className="text-sm text-gray-500">Overall Mastery</span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900">
                    {progress?.overall_mastery ? `${Math.round(progress.overall_mastery * 100)}%` : "0%"}
                  </p>
                </div>

                <div className="bg-white rounded-xl border p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-emerald-100 rounded-lg">
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                    </div>
                    <span className="text-sm text-gray-500">Questions Correct</span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900">
                    {user?.total_correct || 0}
                    <span className="text-lg text-gray-400 font-normal">
                      /{user?.total_questions_attempted || 0}
                    </span>
                  </p>
                </div>

                <div className="bg-white rounded-xl border p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-orange-100 rounded-lg">
                      <Flame className="w-5 h-5 text-orange-600" />
                    </div>
                    <span className="text-sm text-gray-500">Current Streak</span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900">
                    {user?.current_streak || 0}
                    <span className="text-lg text-gray-400 font-normal"> days</span>
                  </p>
                </div>

                <div className="bg-white rounded-xl border p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Clock className="w-5 h-5 text-purple-600" />
                    </div>
                    <span className="text-sm text-gray-500">Practice Time</span>
                  </div>
                  <p className="text-3xl font-bold text-gray-900">
                    {user?.total_practice_time_minutes || 0}
                    <span className="text-lg text-gray-400 font-normal"> mins</span>
                  </p>
                </div>
              </div>
            </section>

            {/* Subject Progress */}
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Progress by Subject</h2>
              <div className="grid md:grid-cols-2 gap-4">
                {Object.entries(progress?.subjects || {}).map(([subject, data]) => {
                  const config = subjectConfig[subject] || subjectConfig.english;
                  const Icon = config.icon;
                  const accuracy = data.accuracy ?? (data.total_attempted > 0 ? data.total_correct / data.total_attempted : 0);

                  return (
                    <div key={subject} className="bg-white rounded-xl border p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <div className={`p-2 ${config.bgColor} rounded-lg`}>
                          <Icon className={`w-5 h-5 ${config.color}`} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">
                            {formatSubjectName(subject)}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {data.total_attempted} questions attempted
                          </p>
                        </div>
                      </div>

                      {/* Mastery Bar */}
                      <div className="mb-4">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Mastery</span>
                          <span className="font-medium text-gray-900">
                            {Math.round(data.mastery * 100)}%
                          </span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${config.bgColor.replace("100", "500")} rounded-full transition-all`}
                            style={{ width: `${Math.round(data.mastery * 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Accuracy */}
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Accuracy</span>
                        <span className={`font-medium ${accuracy >= 0.7 ? "text-emerald-600" : accuracy >= 0.5 ? "text-yellow-600" : "text-red-600"}`}>
                          {Math.round(accuracy * 100)}%
                        </span>
                      </div>

                      <Link
                        href={`/practice/${subject}`}
                        className={`mt-4 block text-center py-2 rounded-lg ${config.bgColor} ${config.color} hover:opacity-80 transition-opacity text-sm font-medium`}
                      >
                        Practice {formatSubjectName(subject)}
                      </Link>
                    </div>
                  );
                })}

                {/* Show empty state if no progress */}
                {(!progress?.subjects || Object.keys(progress.subjects).length === 0) && (
                  <div className="col-span-2 bg-white rounded-xl border p-8 text-center">
                    <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900 mb-2">No practice data yet</h3>
                    <p className="text-gray-500 mb-4">
                      Start practicing to see your progress here!
                    </p>
                    <Link
                      href="/"
                      className="inline-block bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700"
                    >
                      Start Practicing
                    </Link>
                  </div>
                )}
              </div>
            </section>

            {/* Strengths and Weaknesses */}
            <section className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Strengths */}
              <div className="bg-white rounded-xl border p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-semibold text-gray-900">Strong Areas</h3>
                </div>
                {progress?.strong_areas && progress.strong_areas.length > 0 ? (
                  <ul className="space-y-3">
                    {progress.strong_areas.slice(0, 5).map((area, idx) => (
                      <li key={idx} className="flex items-center justify-between">
                        <span className="text-gray-700">
                          {formatSubjectName(area.type)}
                        </span>
                        <span className="text-emerald-600 font-medium">
                          {Math.round(area.accuracy * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 text-sm">
                    Practice more questions to identify your strengths!
                  </p>
                )}
              </div>

              {/* Weaknesses */}
              <div className="bg-white rounded-xl border p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingDown className="w-5 h-5 text-red-500" />
                  <h3 className="font-semibold text-gray-900">Areas to Improve</h3>
                </div>
                {progress?.weak_areas && progress.weak_areas.length > 0 ? (
                  <ul className="space-y-3">
                    {progress.weak_areas.slice(0, 5).map((area, idx) => (
                      <li key={idx} className="flex items-center justify-between">
                        <Link
                          href={`/practice/${area.subject}?type=${area.type}`}
                          className="text-gray-700 hover:text-indigo-600"
                        >
                          {formatSubjectName(area.type)}
                        </Link>
                        <span className="text-red-500 font-medium">
                          {Math.round(area.accuracy * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 text-sm">
                    Practice more questions to identify areas for improvement!
                  </p>
                )}
              </div>
            </section>

            {/* Recommendations */}
            {progress?.recommended_next && progress.recommended_next.length > 0 && (
              <section className="mb-8">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Recommended Practice</h2>
                <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {progress.recommended_next.slice(0, 3).map((rec, idx) => (
                      <Link
                        key={idx}
                        href={`/practice/${rec.subject}?type=${rec.type}`}
                        className="bg-white/20 rounded-lg p-4 hover:bg-white/30 transition-colors"
                      >
                        <h4 className="font-medium mb-1">
                          {formatSubjectName(rec.type)}
                        </h4>
                        <p className="text-sm text-indigo-100">{rec.reason}</p>
                      </Link>
                    ))}
                  </div>
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
