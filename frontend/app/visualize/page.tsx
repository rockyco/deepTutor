"use client";

import { useState, useEffect, useRef } from "react";
import mermaid from "mermaid";
import Link from "next/link";
import { ArrowLeft, Sparkles, Loader2, Download } from "lucide-react";
import { API_BASE } from "@/lib/api";

export default function VisualizePage() {
    const [topic, setTopic] = useState("");
    const [loading, setLoading] = useState(false);
    const [diagramCode, setDiagramCode] = useState("");
    const [error, setError] = useState("");
    const mermaidRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
        });
    }, []);

    useEffect(() => {
        const renderDiagram = async () => {
            if (diagramCode && mermaidRef.current) {
                try {
                    mermaidRef.current.innerHTML = "";
                    const { svg } = await mermaid.render("graphDiv", diagramCode);
                    mermaidRef.current.innerHTML = svg;
                } catch (e) {
                    console.error("Mermaid error:", e);
                    // Fallback or retry?
                }
            }
        };
        renderDiagram();
    }, [diagramCode]);

    const handleGenerate = async () => {
        if (!topic.trim()) return;
        setLoading(true);
        setError("");
        setDiagramCode("");

        try {
            const res = await fetch(`${API_BASE}/visualize/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic }),
            });

            if (!res.ok) throw new Error("Failed to generate diagram");

            const data = await res.json();
            setDiagramCode(data.mermaid);
        } catch (err: any) {
            setError(err.message || "Something went wrong");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
            <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 sticky top-0 z-10">
                <Link href="/" className="flex items-center text-slate-500 hover:text-slate-800 transition-colors">
                    <ArrowLeft className="w-5 h-5 mr-2" />
                    Back to Dashboard
                </Link>
                <span className="ml-4 h-6 w-px bg-slate-200"></span>
                <h1 className="ml-4 font-bold text-lg text-slate-800 flex items-center">
                    visual<span className="text-primary-600">Learning</span>
                </h1>
            </header>

            <main className="flex-grow p-4 md:p-8 max-w-5xl mx-auto w-full">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold text-slate-900 mb-3">Visualize Any Concept</h2>
                    <p className="text-slate-500">Enter a topic (e.g., "Photosynthesis", "Pythagoras Theorem") and AI will draw it for you.</p>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-2 flex gap-2 max-w-2xl mx-auto mb-10">
                    <input
                        type="text"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                        placeholder="What do you want to visualize?"
                        className="flex-grow bg-transparent px-4 py-3 outline-none text-slate-800 placeholder:text-slate-400"
                    />
                    <button
                        onClick={handleGenerate}
                        disabled={loading || !topic}
                        className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-xl font-medium transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5 mr-2" />}
                        {loading ? "Drawing..." : "Visualize"}
                    </button>
                </div>

                {error && (
                    <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-8 text-center border border-red-100">
                        {error}
                    </div>
                )}

                {diagramCode && (
                    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 overflow-hidden animate-fade-in-up">
                        <div className="flex justify-between items-center mb-6 border-b border-slate-100 pb-4">
                            <h3 className="font-bold text-slate-800 text-lg">Visual Explanation: {topic}</h3>
                            <button className="text-slate-400 hover:text-slate-600">
                                <Download className="w-5 h-5" />
                            </button>
                        </div>
                        <div
                            ref={mermaidRef}
                            className="flex justify-center items-center overflow-x-auto min-h-[400px]"
                        >
                            {/* Mermaid renders here */}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
