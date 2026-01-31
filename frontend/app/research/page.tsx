"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Search, Loader2, Globe, BookOpen } from "lucide-react";
import { API_BASE } from "@/lib/api";

type Source = {
    title: string;
    href: string;
    body: string;
};

export default function ResearchPage() {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [answer, setAnswer] = useState("");
    const [sources, setSources] = useState<Source[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);

    const handleResearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setAnswer("");
        setSources([]);

        try {
            const res = await fetch(`${API_BASE}/research/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            });

            if (!res.ok) throw new Error("Search failed");

            const data = await res.json();
            setAnswer(data.answer);
            setSources(data.sources || []);
        } catch (err) {
            setAnswer("Sorry, I encountered an error while researching. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col h-screen overflow-hidden">
            <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 flex-shrink-0">
                <Link href="/" className="flex items-center text-slate-500 hover:text-slate-800 transition-colors">
                    <ArrowLeft className="w-5 h-5 mr-2" />
                </Link>
                <h1 className="ml-4 font-bold text-lg text-slate-800 flex items-center">
                    Deep<span className="text-blue-600">Research</span>
                </h1>
            </header>

            <div className="flex-grow flex flex-col md:flex-row overflow-hidden">
                {/* Main Chat Area */}
                <main className="flex-grow flex flex-col relative">
                    <div className="flex-grow overflow-y-auto p-4 md:p-8 scroll-smooth">
                        {!answer && !loading && (
                            <div className="flex flex-col items-center justify-center h-full text-center text-slate-400">
                                <Globe className="w-16 h-16 mb-4 opacity-20" />
                                <h2 className="text-xl font-medium text-slate-500">Ask me anything</h2>
                                <p className="max-w-md mt-2">I will search the web, read multiple sources, and synthesize a comprehensive answer for you.</p>
                            </div>
                        )}

                        {(answer || loading) && (
                            <div className="max-w-3xl mx-auto space-y-6 pb-20">
                                <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100 inline-block">
                                    <p className="font-heading font-bold text-slate-800">{query}</p>
                                </div>

                                {loading && (
                                    <div className="flex items-center text-slate-500 animate-pulse">
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Analyzing sources...
                                    </div>
                                )}

                                {answer && (
                                    <div className="prose prose-slate max-w-none bg-white p-6 rounded-2xl shadow-sm border border-slate-200 animate-fade-in-up">
                                        <div className="whitespace-pre-wrap">{answer}</div>
                                    </div>
                                )}
                                <div ref={bottomRef} />
                            </div>
                        )}
                    </div>

                    {/* Input Area */}
                    <div className="p-4 bg-white border-t border-slate-200">
                        <div className="max-w-3xl mx-auto flex gap-2">
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleResearch()}
                                placeholder="Research a topic..."
                                className="flex-grow bg-slate-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-100 transition-all text-slate-800"
                            />
                            <button
                                onClick={handleResearch}
                                disabled={loading || !query}
                                className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-xl transition-colors disabled:opacity-50"
                            >
                                <Search className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </main>

                {/* Sidebar Sources (Desktop) */}
                {sources.length > 0 && (
                    <aside className="w-80 bg-white border-l border-slate-200 overflow-y-auto hidden md:block flex-shrink-0 p-4">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Cited Sources</h3>
                        <div className="space-y-3">
                            {sources.map((source, i) => (
                                <a
                                    key={i}
                                    href={source.href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block p-3 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all group"
                                >
                                    <div className="flex items-start gap-2">
                                        <span className="bg-slate-100 text-slate-500 text-xs font-bold px-1.5 py-0.5 rounded flex-shrink-0">
                                            {i + 1}
                                        </span>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-800 line-clamp-2 group-hover:text-blue-600 transition-colors">
                                                {source.title}
                                            </h4>
                                            <p className="text-xs text-slate-400 mt-1 truncate">
                                                {new URL(source.href).hostname}
                                            </p>
                                        </div>
                                    </div>
                                </a>
                            ))}
                        </div>
                    </aside>
                )}
            </div>
        </div>
    );
}
