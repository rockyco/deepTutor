'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

// Types
interface Question {
  id: string;
  subject: string;
  question_type: string;
  formatting: string;
  difficulty: number;
  content: {
    text: string;
    options: string[];
    images?: string[];
    option_images?: string[];
    passage?: string;
  };
  answer: {
    value: string;
    correct_index: number;
  };
  explanation?: string;
  source?: string;
}

export default function MockExamPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [showExplanation, setShowExplanation] = useState(false);

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/questions?limit=52', { cache: 'no-store' });
      const data = await res.json();
      setQuestions(data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch", err);
      setLoading(false);
    }
  };

  const currentQ = questions[currentIndex];

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-xl font-medium text-gray-600 animate-pulse">Loading DeepTutor Exam...</div>
      </div>
    );
  }

  if (!currentQ) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 flex-col gap-4">
        <h1 className="text-2xl font-bold text-gray-800">No Questions Found</h1>
        <p className="text-gray-600">Please run the content generator first.</p>
        <Link href="/" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">
          Go Home
        </Link>
      </div>
    );
  }

  // Theming Logic
  const getTheme = (subject: string) => {
    switch (subject) {
      case 'maths': return { bg: 'bg-pink-50', border: 'border-pink-200', accent: 'text-pink-700', button: 'bg-pink-600 hover:bg-pink-700' };
      case 'english': return { bg: 'bg-blue-50', border: 'border-blue-200', accent: 'text-blue-700', button: 'bg-blue-600 hover:bg-blue-700' };
      case 'non_verbal_reasoning': return { bg: 'bg-yellow-50', border: 'border-yellow-200', accent: 'text-yellow-700', button: 'bg-yellow-600 hover:bg-yellow-700' };
      case 'verbal_reasoning': return { bg: 'bg-green-50', border: 'border-green-200', accent: 'text-green-700', button: 'bg-green-600 hover:bg-green-700' };
      default: return { bg: 'bg-gray-50', border: 'border-gray-200', accent: 'text-gray-700', button: 'bg-gray-800 hover:bg-gray-900' };
    }
  };

  const theme = getTheme(currentQ.subject);
  const progress = ((currentIndex + 1) / questions.length) * 100;

  return (
    <div className={`min-h-screen ${theme.bg} p-4 md:p-8 transition-colors duration-500`}>

      {/* Header / Nav */}
      <div className="max-w-4xl mx-auto flex justify-between items-center mb-8">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-gray-500 hover:text-gray-900 font-medium">← Exit</Link>
        </div>
        <div className="text-sm font-semibold tracking-wide uppercase text-gray-500">
          {currentQ.subject.replace(/_/g, ' ')} • Q{currentIndex + 1} of {questions.length}
        </div>
      </div>

      {/* Main Card (Zen Mode) */}
      <main className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden border border-white/50 relative">

        {/* Progress Bar */}
        <div className="absolute top-0 left-0 w-full h-1.5 bg-gray-100">
          <div
            className={`h-full ${theme.button} transition-all duration-300`}
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="p-8 md:p-12">

          {/* Question Text */}
          <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-8 leading-snug">
            {currentQ.content.text}
          </h2>

          {/* Passage (English) */}
          {currentQ.content.passage && (
            <div className="mb-8 p-6 bg-gray-50 rounded-xl border border-gray-200 text-gray-700 italic leading-relaxed font-serif">
              "{currentQ.content.passage}"
            </div>
          )}

          {/* Images (NVR / Maths) */}
          {currentQ.content.images && currentQ.content.images.length > 0 && (
            <div className="mb-8 flex justify-center">
              {currentQ.content.images.map((img, i) => (
                <img
                  key={i}
                  src={img}
                  alt="Question Diagram"
                  className="max-h-80 md:max-h-96 w-auto object-contain rounded-lg border border-gray-100 shadow-sm"
                />
              ))}
            </div>
          )}

          {/* Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentQ.content.options.map((opt, i) => {
              const optImg = currentQ.content.option_images?.[i];
              return (
                <button
                  key={i}
                  onClick={() => setAnswers({ ...answers, [currentQ.id]: i })}
                  className={`
                    group relative flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all duration-200
                    ${answers[currentQ.id] === i
                      ? `${theme.border} ${theme.bg} shadow-md scale-[1.02]`
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}
                  `}
                >
                  {/* Radio Circle */}
                  <div className={`
                    w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors
                    ${answers[currentQ.id] === i ? `border-${theme.accent.split('-')[1]}-600` : 'border-gray-300'}
                  `}>
                    {answers[currentQ.id] === i && (
                      <div className={`w-3 h-3 rounded-full ${theme.button}`} />
                    )}
                  </div>

                  {/* Option Content (Image or Text) */}
                  {optImg ? (
                    <img src={optImg} alt={`Option ${i}`} className="h-16 w-16 object-contain" />
                  ) : (
                    <span className="text-lg font-medium text-gray-700 group-hover:text-gray-900">
                      {opt}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

        </div>

        {/* Footer Actions */}
        <div className="bg-gray-50 p-6 flex justify-between items-center border-t border-gray-100">
          <button
            onClick={() => setShowExplanation(true)}
            className="text-gray-500 hover:text-gray-700 font-medium text-sm flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            See Example / Help
          </button>

          <div className="flex gap-3">
            <button
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex(prev => prev - 1)}
              className="px-6 py-2 rounded-lg font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentIndex(prev => Math.min(questions.length - 1, prev + 1))}
              className={`px-8 py-2 rounded-lg font-bold text-white shadow-lg transition transform active:scale-95 ${theme.button}`}
            >
              {currentIndex === questions.length - 1 ? 'Finish' : 'Next Question'}
            </button>
          </div>
        </div>
      </main>

      {/* Explanation Modal */}
      {showExplanation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl p-8 relative">
            <button
              onClick={() => setShowExplanation(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 p-2"
            >
              ✕
            </button>

            <h3 className={`text-xl font-bold mb-4 ${theme.accent}`}>How to solve this?</h3>

            <div className="text-gray-600 space-y-4">
              {currentQ.explanation ? (
                <p className="leading-relaxed">{currentQ.explanation}</p>
              ) : (
                <>
                  <p>Study the pattern carefully.</p>
                  <ul className="list-disc pl-5 space-y-2">
                    <li>Look for changes in <strong>rotation</strong> (clockwise or anti-clockwise).</li>
                    <li>Count the number of sides or shapes.</li>
                    <li>Check for alternating colours or shading.</li>
                  </ul>
                  <p className="mt-4 text-sm text-gray-500 italic">This is a generated example. Look closely at the rows and columns!</p>
                </>
              )}
            </div>

            <button
              onClick={() => setShowExplanation(false)}
              className={`mt-8 w-full py-3 rounded-xl font-bold text-white ${theme.button}`}
            >
              Got it!
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
