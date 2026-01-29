"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, BrainCircuit, Loader2, CheckCircle } from "lucide-react";

type Question = {
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
};

export default function GeneratorPage() {
    const [step, setStep] = useState<"config" | "quiz">("config");
    const [topic, setTopic] = useState("");
    const [loading, setLoading] = useState(false);
    const [questions, setQuestions] = useState<Question[]>([]);

    // Quiz State
    const [answers, setAnswers] = useState<Record<number, string>>({});
    const [showResults, setShowResults] = useState(false);

    const handleGenerate = async () => {
        if (!topic.trim()) return;
        setLoading(true);

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${API_URL}/generator/quiz`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic, difficulty: "Medium" }),
            });

            if (!res.ok) throw new Error("Failed to generate quiz");

            const data = await res.json();
            setQuestions(data.questions || []);
            setStep("quiz");
        } catch (err) {
            alert("Failed to generate quiz.");
        } finally {
            setLoading(false);
        }
    };

    const handleOptionSelect = (qIndex: number, option: string) => {
        if (showResults) return;
        setAnswers(prev => ({ ...prev, [qIndex]: option }));
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
            <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 sticky top-0 z-10">
                <Link href="/" className="flex items-center text-slate-500 hover:text-slate-800 transition-colors">
                    <ArrowLeft className="w-5 h-5 mr-2" />
                    Back to Dashboard
                </Link>
                <h1 className="ml-4 font-bold text-lg text-slate-800 flex items-center">
                    Smart<span className="text-purple-600">Practice</span>
                </h1>
            </header>

            <main className="flex-grow p-4 md:p-8 max-w-3xl mx-auto w-full">
                {step === "config" && (
                    <div className="max-w-lg mx-auto mt-10">
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 bg-purple-100 text-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                <BrainCircuit className="w-8 h-8" />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-900">What do you want to practice?</h2>
                            <p className="text-slate-500 mt-2">AI will generate a custom quiz just for you.</p>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                            <label className="block text-sm font-bold text-slate-700 mb-2">Topic</label>
                            <input
                                type="text"
                                value={topic}
                                onChange={(e) => setTopic(e.target.value)}
                                placeholder="e.g. Algebra, Synonyms, 3D Shapes"
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-100 focus:border-purple-300 transition-all mb-6"
                            />

                            <button
                                onClick={handleGenerate}
                                disabled={loading || !topic}
                                className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-bold transition-all flex items-center justify-center disabled:opacity-50"
                            >
                                {loading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : "Generate Quiz"}
                            </button>
                        </div>
                    </div>
                )}

                {step === "quiz" && (
                    <div className="space-y-8 pb-32">
                        <div className="flex justify-between items-center">
                            <h2 className="text-2xl font-bold text-slate-900">{topic} Quiz</h2>
                            {!showResults && (
                                <button
                                    onClick={() => setShowResults(true)}
                                    className="text-purple-600 font-bold hover:bg-purple-50 px-4 py-2 rounded-lg transition-colors"
                                >
                                    Finish & Check
                                </button>
                            )}
                        </div>

                        {questions.map((q, idx) => {
                            const isCorrect = answers[idx] === q.correct_answer;
                            const isSelected = !!answers[idx];

                            return (
                                <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                                    <h3 className="font-bold text-lg text-slate-800 mb-4 flex gap-3">
                                        <span className="bg-slate-100 text-slate-500 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm">{idx + 1}</span>
                                        {q.question}
                                    </h3>

                                    <div className="grid gap-3">
                                        {q.options.map((opt, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleOptionSelect(idx, opt)}
                                                className={`w-full text-left p-4 rounded-xl border transition-all relative ${answers[idx] === opt
                                                        ? showResults
                                                            ? isCorrect ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
                                                            : "bg-purple-50 border-purple-300 ring-1 ring-purple-300"
                                                        : "bg-white border-slate-100 hover:bg-slate-50"
                                                    }`}
                                            >
                                                {opt}
                                                {showResults && opt === q.correct_answer && (
                                                    <CheckCircle className="w-5 h-5 text-green-500 absolute right-4 top-1/2 -translate-y-1/2" />
                                                )}
                                            </button>
                                        ))}
                                    </div>

                                    {showResults && (
                                        <div className="mt-4 p-4 bg-slate-50 rounded-xl text-sm text-slate-600 border border-slate-100">
                                            <span className="font-bold text-slate-800">Explanation:</span> {q.explanation}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>
        </div>
    );
}
