"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";

export function Sidebar({ className }: { className?: string }) {
    const pathname = usePathname();
    const { user } = useAuth();

    const isActive = (path: string) => pathname === path;

    return (
        <aside className={cn("hidden lg:flex w-72 bg-white border-r border-slate-200 flex-col transition-all duration-300 z-20 shadow-sm relative group h-full", className)}>
            <div className="h-20 flex items-center justify-start px-6 border-b border-slate-100 flex-shrink-0">
                <div className="relative w-10 h-10 flex-shrink-0 bg-gradient-to-br from-primary-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-primary-500/30">
                    DT
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
                </div>
                <div className="ml-3 opacity-100 transition-opacity duration-300">
                    <h1 className="font-heading font-bold text-xl tracking-tight text-slate-900">DeepTutor</h1>
                    <p className="text-xs text-slate-500 font-medium tracking-wider uppercase">AI 11+ Platform</p>
                </div>
            </div>

            <div className="flex-grow py-6 px-3 space-y-2 overflow-y-auto">
                <div className="px-3 mb-2">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Modules</h3>
                </div>

                <Link
                    href="/"
                    className={cn(
                        "w-full flex items-center gap-4 px-3 py-3 rounded-xl transition-colors font-medium",
                        isActive("/") ? "bg-slate-100 text-primary-600" : "hover:bg-slate-50 text-slate-600 hover:text-primary-600"
                    )}
                >
                    <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                    </svg>
                    <span className="font-medium">Dashboard</span>
                </Link>

                <Link
                    href="/learn"
                    className={cn(
                        "w-full flex items-center gap-4 px-3 py-3 rounded-xl transition-colors font-medium",
                        pathname?.startsWith("/learn") ? "bg-teal-50 text-teal-600" : "hover:bg-teal-50 text-slate-600 hover:text-teal-600"
                    )}
                >
                    <div className="w-8 h-8 flex items-center justify-center bg-teal-100 rounded-lg">
                        <BookOpen className="w-4 h-4 text-teal-600" />
                    </div>
                    <span className="font-medium">Learn</span>
                </Link>

                {/* Subjects */}
                <Link href="/practice/maths" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-blue-50 text-slate-600 hover:text-blue-600 transition-colors">
                    <div className="w-8 h-8 flex items-center justify-center text-xl bg-blue-100 rounded-lg">📐</div>
                    <span className="font-medium">Mathematics</span>
                </Link>
                <Link href="/practice/verbal_reasoning" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-purple-50 text-slate-600 hover:text-purple-600 transition-colors">
                    <div className="w-8 h-8 flex items-center justify-center text-xl bg-purple-100 rounded-lg">🗣️</div>
                    <span className="font-medium">Verbal Reasoning</span>
                </Link>
                <Link href="/practice/non_verbal_reasoning" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-orange-50 text-slate-600 hover:text-orange-600 transition-colors">
                    <div className="w-8 h-8 flex items-center justify-center text-xl bg-orange-100 rounded-lg">🧩</div>
                    <span className="font-medium">Non-Verbal</span>
                </Link>
                <Link href="/practice/english" className="w-full flex items-center gap-4 px-3 py-3 rounded-xl hover:bg-green-50 text-slate-600 hover:text-green-600 transition-colors">
                    <div className="w-8 h-8 flex items-center justify-center text-xl bg-green-100 rounded-lg">📖</div>
                    <span className="font-medium">English</span>
                </Link>
            </div>

            <div className="p-4 mt-auto border-t border-slate-100 flex-shrink-0 space-y-2">
                <Link
                    href="/settings"
                    className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-colors",
                        isActive("/settings") ? "bg-slate-100 text-slate-900" : "bg-slate-50 hover:bg-slate-100 text-slate-600"
                    )}
                >
                    <div className="relative">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                        </svg>
                        <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border border-white"></div>
                    </div>
                    <span className="font-medium text-sm">Settings & API</span>
                </Link>

                {user ? (
                    <div className="px-3 py-2 text-xs text-slate-400 text-center">
                        Logged in as {user.name}
                    </div>
                ) : (
                    <Link href="/login" className="block w-full text-center px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                        Sign In
                    </Link>
                )}
            </div>
        </aside>
    );
}
