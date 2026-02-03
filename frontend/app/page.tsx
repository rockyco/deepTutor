"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen } from "lucide-react";

import { Sidebar } from "@/components/Sidebar";

export default function Home() {
  const [activeView, setActiveView] = useState("dashboard");

  return (
    <div className="flex h-[100dvh] w-full bg-slate-50/50 overflow-hidden">
      {/* Sidebar (Desktop Only) */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-grow flex flex-col relative overflow-y-auto h-full px-4 py-8 pb-32 lg:pb-8">
        {/* Header */}
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 px-4 lg:px-8 flex items-center justify-between z-10 sticky top-0 flex-shrink-0 rounded-xl mb-4">
          <div>
            <h2 className="text-xl font-heading font-bold text-slate-800">Dashboard</h2>
            <p className="text-xs text-slate-500 font-medium">Welcome back, Student</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 p-[2px]">
              <div className="h-full w-full rounded-full bg-white flex items-center justify-center">
                <span className="font-bold text-xs text-transparent bg-clip-text bg-gradient-to-tr from-blue-500 to-purple-500">JS</span>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-grow overflow-y-auto relative scroll-smooth">
          <div className="max-w-6xl mx-auto animate-fade-in-up">

            <section className="mb-12">
              <div className="flex justify-between items-end mb-6">
                <div>
                  <h3 className="text-2xl font-heading font-bold text-slate-900">Start Practicing</h3>
                  <p className="text-slate-500">Choose a mode to begin your session</p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {/* Learn Card */}
                <Link href="/learn" className="glass-card rounded-2xl p-6 cursor-pointer relative overflow-hidden group block border-l-4 border-teal-500">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-teal-100 rounded-full blur-2xl -mr-16 -mt-16 opacity-50 group-hover:opacity-70 transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                        <BookOpen className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-slate-900">Learn</h3>
                        <p className="text-xs text-slate-500">Interactive Lessons</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-4 line-clamp-2">Step-by-step lessons for every question type with worked examples.</p>
                    <div className="px-3 py-1.5 bg-teal-50 text-teal-700 text-xs font-bold rounded-lg inline-block">46 Lessons</div>
                  </div>
                </Link>

                {/* Full Mock Card */}
                <Link href="/mock-exam" className="glass-card rounded-2xl p-6 cursor-pointer relative overflow-hidden group block border-l-4 border-indigo-500">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-100 rounded-full blur-2xl -mr-16 -mt-16 opacity-50 group-hover:opacity-70 transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">📝</div>
                      <div>
                        <h3 className="text-xl font-bold text-slate-900">GL Mock Exam</h3>
                        <p className="text-xs text-slate-500">2 Papers • 180 Qs • GL Format</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-4 line-clamp-2">Full Trafford Grammar format: 2 papers, 4 timed sections each, 50 min per paper.</p>
                    <div className="px-3 py-1.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-lg inline-block">Start Exam</div>
                  </div>
                </Link>

                {/* Visualize Card */}
                <Link href="/visualize" className="glass-card rounded-2xl p-6 cursor-pointer relative overflow-hidden group block border-l-4 border-primary-500">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-primary-100 rounded-full blur-2xl -mr-16 -mt-16 opacity-50 group-hover:opacity-70 transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">🎨</div>
                      <div>
                        <h3 className="text-xl font-bold text-slate-900">Visual Learning</h3>
                        <p className="text-xs text-slate-500">Interactive Diagrams</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-4 line-clamp-2">Turn complex concepts into easy flowcharts and mindmaps instantly.</p>
                    <div className="px-3 py-1.5 bg-primary-50 text-primary-700 text-xs font-bold rounded-lg inline-block">New Feature</div>
                  </div>
                </Link>

                {/* Research Card */}
                <Link href="/research" className="glass-card rounded-2xl p-6 cursor-pointer relative overflow-hidden group block border-l-4 border-blue-500">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-blue-100 rounded-full blur-2xl -mr-16 -mt-16 opacity-50 group-hover:opacity-70 transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">🔍</div>
                      <div>
                        <h3 className="text-xl font-bold text-slate-900">Deep Research</h3>
                        <p className="text-xs text-slate-500">Web-Augmented Q&A</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-4 line-clamp-2">Ask anything. I'll search the web and summarize the answer with citations.</p>
                    <div className="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs font-bold rounded-lg inline-block">Real-time Web</div>
                  </div>
                </Link>

                {/* Generator Card */}
                <Link href="/smart-practice" className="glass-card rounded-2xl p-6 cursor-pointer relative overflow-hidden group block border-l-4 border-purple-500">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-purple-100 rounded-full blur-2xl -mr-16 -mt-16 opacity-50 group-hover:opacity-70 transition"></div>
                  <div className="relative z-10">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">🧠</div>
                      <div>
                        <h3 className="text-xl font-bold text-slate-900">Smart Practice</h3>
                        <p className="text-xs text-slate-500">Infinite Quizzes</p>
                      </div>
                    </div>
                    <p className="text-sm text-slate-600 mb-4 line-clamp-2">Generate custom quizzes on any topic or difficulty level.</p>
                    <div className="px-3 py-1.5 bg-purple-50 text-purple-700 text-xs font-bold rounded-lg inline-block">Adaptive</div>
                  </div>
                </Link>
              </div>
            </section>

            <section>
              <h3 className="text-lg font-heading font-bold text-slate-900 mb-4">Topic Shortcuts</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Link href="/practice/maths" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-blue-300 hover:shadow-md transition text-left group">
                  <div className="w-12 h-12 flex items-center justify-center text-3xl bg-blue-50 rounded-2xl mb-3 group-hover:scale-110 transition-transform">
                    📐
                  </div>
                  <div className="font-bold text-slate-800">Mathematics</div>
                  <div className="text-xs text-slate-400">Numbers & Data</div>
                </Link>
                <Link href="/practice/verbal_reasoning" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-purple-300 hover:shadow-md transition text-left group">
                  <div className="w-12 h-12 flex items-center justify-center text-3xl bg-purple-50 rounded-2xl mb-3 group-hover:scale-110 transition-transform">
                    🗣️
                  </div>
                  <div className="font-bold text-slate-800">Verbal Reasoning</div>
                  <div className="text-xs text-slate-400">Logic & Vocabulary</div>
                </Link>
                <Link href="/practice/non_verbal_reasoning" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-orange-300 hover:shadow-md transition text-left group">
                  <div className="w-12 h-12 flex items-center justify-center text-3xl bg-orange-50 rounded-2xl mb-3 group-hover:scale-110 transition-transform">
                    🧩
                  </div>
                  <div className="font-bold text-slate-800">Non-Verbal</div>
                  <div className="text-xs text-slate-400">Patterns & Shapes</div>
                </Link>
                <Link href="/practice/english" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-green-300 hover:shadow-md transition text-left group">
                  <div className="w-12 h-12 flex items-center justify-center text-3xl bg-green-50 rounded-2xl mb-3 group-hover:scale-110 transition-transform">
                    📖
                  </div>
                  <div className="font-bold text-slate-800">English</div>
                  <div className="text-xs text-slate-400">Comprehension</div>
                </Link>
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      <div className="lg:hidden fixed bottom-0 w-full bg-white border-t border-slate-200 flex justify-around items-center h-16 pb-safe z-50 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <button onClick={() => setActiveView('dashboard')} className="flex flex-col items-center justify-center w-full h-full text-primary-600">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
          <span className="text-[10px] font-bold mt-1">Dash</span>
        </button>
        <Link href="/learn" className="flex flex-col items-center justify-center w-full h-full text-slate-400 hover:text-teal-600">
          <BookOpen className="w-5 h-5" />
          <span className="text-[10px] font-medium mt-1">Learn</span>
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
