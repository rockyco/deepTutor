"use client";

import { useState } from "react";
import Link from "next/link";

export default function Home() {
  const [activeView, setActiveView] = useState("dashboard");

  return (
    <div className="flex h-screen w-full bg-slate-50/50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-20 lg:w-72 bg-white border-r border-slate-200 flex flex-col transition-all duration-300 z-20 shadow-sm relative group h-full">
        <div className="h-20 flex items-center justify-center lg:justify-start lg:px-6 border-b border-slate-100 flex-shrink-0">
          <div className="relative w-10 h-10 flex-shrink-0 bg-gradient-to-br from-primary-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-primary-500/30">
            DT
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
          </div>
          <div className="ml-3 hidden lg:block opacity-0 group-hover:opacity-100 lg:opacity-100 transition-opacity duration-300">
            <h1 className="font-heading font-bold text-xl tracking-tight text-slate-900">DeepTutor</h1>
            <p className="text-xs text-slate-500 font-medium tracking-wider uppercase">AI 11+ Platform</p>
          </div>
        </div>

        <div className="flex-grow py-6 px-3 space-y-2 overflow-y-auto">
          <div className="px-3 mb-2 hidden lg:block">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Modules</h3>
          </div>

          <button onClick={() => setActiveView('dashboard')} className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-slate-50 text-slate-600 hover:text-primary-600 transition-colors group/btn">
            <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            <span className="hidden lg:block font-medium">Dashboard</span>
          </button>

          <Link href="/practice/maths" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-blue-50 text-slate-600 hover:text-blue-600 transition-colors">
            <div className="w-6 h-6 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <span className="hidden lg:block font-medium">Mathematics</span>
          </Link>
          <Link href="/practice/verbal_reasoning" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-purple-50 text-slate-600 hover:text-purple-600 transition-colors">
            <div className="w-6 h-6 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">Ab</div>
            <span className="hidden lg:block font-medium">Verbal Reasoning</span>
          </Link>
          <Link href="/practice/non_verbal_reasoning" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-orange-50 text-slate-600 hover:text-orange-600 transition-colors">
            <div className="w-6 h-6 rounded-lg bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="hidden lg:block font-medium">Non-Verbal</span>
          </Link>
          <Link href="/practice/english" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-green-50 text-slate-600 hover:text-green-600 transition-colors">
            <div className="w-6 h-6 rounded-lg bg-green-100 text-green-600 flex items-center justify-center text-xs font-bold flex-shrink-0">¶</div>
            <span className="hidden lg:block font-medium">English</span>
          </Link>
        </div>

        <div className="p-4 mt-auto border-t border-slate-100 flex-shrink-0">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 transition-colors">
            <div className="relative">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border border-white"></div>
            </div>
            <span className="hidden lg:block font-medium text-sm">Settings & API</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-grow flex flex-col relative overflow-y-auto h-full px-4 py-8">
        {/* Header */}
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 flex items-center justify-between z-10 sticky top-0 flex-shrink-0">
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
        <div className="flex-grow overflow-y-auto p-6 md:p-10 scroll-smooth relative">
          <div className="max-w-6xl mx-auto animate-fade-in-up">

            <section className="mb-12">
              <div className="flex justify-between items-end mb-6">
                <div>
                  <h3 className="text-2xl font-heading font-bold text-slate-900">Start Practicing</h3>
                  <p className="text-slate-500">Choose a mode to begin your session</p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                {/* Full Mock Card */}
                <Link href="/mock-exam" className="glass-card rounded-2xl p-8 cursor-pointer relative overflow-hidden group block">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-primary-100 rounded-full blur-3xl -mr-32 -mt-32 opacity-50 transition duration-500 group-hover:opacity-70"></div>

                  <div className="relative z-10">
                    <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform duration-300">
                      📝
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-2">Full Mock Exam</h3>
                    <p className="text-slate-500 mb-6">Simulate the real exam experience. 52 mixed questions, strict timing.</p>

                    <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
                      <span className="bg-white/60 px-3 py-1 rounded-full border border-slate-200/50">⏱️ 50 Mins</span>
                      <span className="bg-white/60 px-3 py-1 rounded-full border border-slate-200/50">📚 52 Qs</span>
                      <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full border border-green-200/50">Official Format</span>
                    </div>
                  </div>
                </Link>

                {/* Import Card */}
                <div className="glass-card rounded-2xl p-8 cursor-pointer relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-purple-100 rounded-full blur-3xl -mr-32 -mt-32 opacity-50 transition duration-500 group-hover:opacity-70"></div>

                  <div className="relative z-10">
                    <div className="w-14 h-14 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform duration-300">
                      ✨
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-2">AI Resource Importer</h3>
                    <p className="text-slate-500 mb-6">Digitize paper tests instantly using Gemini AI. Paste text and convert to interactive quizzes.</p>

                    <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
                      <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full border border-purple-200/50">🔮 Powered by Gemini</span>
                      <span className="bg-white/60 px-3 py-1 rounded-full border border-slate-200/50">⚡ Instant Digitization</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section>
              <h3 className="text-lg font-heading font-bold text-slate-900 mb-4">Topic Shortcuts</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Link href="/practice/maths" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-blue-300 hover:shadow-md transition text-left group">
                  <div className="w-8 h-8 rounded-lg bg-blue-100/50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition"></div>
                  <div className="font-bold text-slate-800">Mathematics</div>
                  <div className="text-xs text-slate-400">Numbers & Data</div>
                </Link>
                <Link href="/practice/verbal_reasoning" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-purple-300 hover:shadow-md transition text-left group">
                  <div className="w-8 h-8 rounded-lg bg-purple-100/50 text-purple-600 flex items-center justify-center mb-3 group-hover:bg-purple-600 group-hover:text-white transition">Ab</div>
                  <div className="font-bold text-slate-800">Verbal Reasoning</div>
                  <div className="text-xs text-slate-400">Logic & Vocabulary</div>
                </Link>
                <Link href="/practice/non_verbal_reasoning" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-orange-300 hover:shadow-md transition text-left group">
                  <div className="w-8 h-8 rounded-lg bg-orange-100/50 text-orange-600 flex items-center justify-center mb-3 group-hover:bg-orange-600 group-hover:text-white transition"></div>
                  <div className="font-bold text-slate-800">Non-Verbal</div>
                  <div className="text-xs text-slate-400">Patterns & Shapes</div>
                </Link>
                <Link href="/practice/english" className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 hover:border-green-300 hover:shadow-md transition text-left group">
                  <div className="w-8 h-8 rounded-lg bg-green-100/50 text-green-600 flex items-center justify-center mb-3 group-hover:bg-green-600 group-hover:text-white transition">¶</div>
                  <div className="font-bold text-slate-800">English</div>
                  <div className="text-xs text-slate-400">Comprehension</div>
                </Link>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
