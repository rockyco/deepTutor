'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  API_BASE,
  mockExamAPI,
  getImageUrl,
  isImageUrl,
  type MockExamSession,
  type MockExamQuestion,
  type MockExamResult,
  type PaperResult,
  type SectionResult,
} from '@/lib/api';

// Section display config
const SECTION_CONFIG: Record<string, { label: string; color: string; bgColor: string; borderColor: string; buttonColor: string }> = {
  english: {
    label: 'English',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    buttonColor: 'bg-blue-600 hover:bg-blue-700',
  },
  maths: {
    label: 'Mathematics',
    color: 'text-pink-700',
    bgColor: 'bg-pink-50',
    borderColor: 'border-pink-200',
    buttonColor: 'bg-pink-600 hover:bg-pink-700',
  },
  non_verbal_reasoning: {
    label: 'Non-Verbal Reasoning',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    buttonColor: 'bg-amber-600 hover:bg-amber-700',
  },
  verbal_reasoning: {
    label: 'Verbal Reasoning',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    buttonColor: 'bg-green-600 hover:bg-green-700',
  },
};

type ExamPhase =
  | 'intro'
  | 'section'       // answering questions in a section
  | 'section_break'  // between sections within a paper
  | 'paper_break'    // between paper 1 and paper 2
  | 'results';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// --- Timer Component ---
function ExamTimer({ seconds, onExpired, paused }: { seconds: number; onExpired: () => void; paused?: boolean }) {
  const [remaining, setRemaining] = useState(seconds);
  const onExpiredRef = useRef(onExpired);
  onExpiredRef.current = onExpired;

  useEffect(() => {
    setRemaining(seconds);
  }, [seconds]);

  useEffect(() => {
    if (paused) return;
    if (remaining <= 0) {
      onExpiredRef.current();
      return;
    }
    const timer = setInterval(() => {
      setRemaining(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onExpiredRef.current();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [remaining, paused]);

  const isLow = remaining < 60;
  return (
    <div className={`font-mono text-lg font-bold tabular-nums ${isLow ? 'text-red-600 animate-pulse' : 'text-gray-700'}`}>
      {formatTime(remaining)}
    </div>
  );
}

// --- Question Renderer ---
function QuestionCard({
  question,
  index,
  total,
  selectedAnswer,
  onSelect,
  sectionName,
}: {
  question: MockExamQuestion;
  index: number;
  total: number;
  selectedAnswer: string | undefined;
  onSelect: (answer: string) => void;
  sectionName: string;
}) {
  const config = SECTION_CONFIG[question.subject] || SECTION_CONFIG.english;

  return (
    <div className="space-y-6">
      {/* Question header */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span className={`font-semibold ${config.color}`}>{sectionName}</span>
        <span>Question {index + 1} of {total}</span>
      </div>

      {/* Passage for comprehension */}
      {question.content.passage && (
        <div className="p-5 bg-gray-50 rounded-xl border border-gray-200 text-gray-700 leading-relaxed font-serif text-[15px]">
          {question.content.passage}
        </div>
      )}

      {/* Question images */}
      {question.content.images && question.content.images.length > 0 && (
        <div className="flex justify-center gap-3 flex-wrap">
          {question.content.images.map((img, i) => (
            <img
              key={i}
              src={getImageUrl(img)}
              alt={`Figure ${i + 1}`}
              className="max-h-64 w-auto object-contain rounded-lg border border-gray-200 shadow-sm"
            />
          ))}
        </div>
      )}

      {question.content.image_url && (
        <div className="flex justify-center">
          <img
            src={getImageUrl(question.content.image_url)}
            alt="Question figure"
            className="max-h-72 w-auto object-contain rounded-lg border border-gray-200 shadow-sm"
          />
        </div>
      )}

      {/* Question text */}
      <h2 className="text-xl font-bold text-gray-800 leading-relaxed whitespace-pre-line">
        {question.content.text}
      </h2>

      {/* Options */}
      {question.content.options && (
        <div className="grid grid-cols-1 gap-3">
          {question.content.options.map((opt, i) => {
            const isSelected = selectedAnswer === opt;
            const optImg = question.content.option_images?.[i];
            const letter = String.fromCharCode(65 + i); // A, B, C, D, E

            return (
              <button
                key={i}
                onClick={() => onSelect(opt)}
                className={`
                  flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all duration-150
                  ${isSelected
                    ? `${config.borderColor} ${config.bgColor} shadow-md`
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}
                `}
              >
                <div className={`
                  w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-sm font-bold transition-colors
                  ${isSelected ? `${config.borderColor} ${config.color}` : 'border-gray-300 text-gray-400'}
                `}>
                  {letter}
                </div>

                {optImg && isImageUrl(optImg) ? (
                  <img src={getImageUrl(optImg)} alt={`Option ${letter}`} className="h-14 w-14 object-contain" />
                ) : (
                  <span className={`text-base ${isSelected ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                    {opt}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --- Main Page ---
export default function MockExamPage() {
  const [phase, setPhase] = useState<ExamPhase>('intro');
  const [session, setSession] = useState<MockExamSession | null>(null);
  const [currentPaper, setCurrentPaper] = useState(1);
  const [currentSectionIdx, setCurrentSectionIdx] = useState(0);
  const [questions, setQuestions] = useState<MockExamQuestion[]>([]);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<MockExamResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sectionTimeLeft, setSectionTimeLeft] = useState(0);
  const questionStartTime = useRef(Date.now());

  // Get user ID from localStorage
  const getUserId = () => {
    if (typeof window === 'undefined') return 'anonymous';
    return localStorage.getItem('userId') || 'anonymous';
  };

  const startExam = async () => {
    setLoading(true);
    setError('');
    try {
      const examSession = await mockExamAPI.startExam(getUserId());
      setSession(examSession);
      setCurrentPaper(1);
      setCurrentSectionIdx(0);
      setPhase('section');
      await loadSection(examSession.id, 1, 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start exam');
    } finally {
      setLoading(false);
    }
  };

  const loadSection = async (examId: string, paperNum: number, sectionIdx: number) => {
    setLoading(true);
    try {
      const sectionQuestions = await mockExamAPI.getSectionQuestions(examId, paperNum, sectionIdx);
      setQuestions(sectionQuestions);
      setCurrentQuestionIdx(0);
      questionStartTime.current = Date.now();

      // Get section time
      if (session || examId) {
        const s = session || await mockExamAPI.getExam(examId);
        if (s) {
          const paper = s.papers.find(p => p.paper_number === paperNum);
          if (paper && paper.sections[sectionIdx]) {
            setSectionTimeLeft(paper.sections[sectionIdx].time_seconds);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load section');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAnswer = (answer: string) => {
    const q = questions[currentQuestionIdx];
    if (!q) return;
    setAnswers(prev => ({ ...prev, [q.id]: answer }));

    // Submit to backend
    if (session) {
      const elapsed = Math.round((Date.now() - questionStartTime.current) / 1000);
      mockExamAPI.submitAnswer(session.id, q.id, answer, elapsed).catch(() => {});
    }
  };

  const nextQuestion = () => {
    questionStartTime.current = Date.now();
    if (currentQuestionIdx < questions.length - 1) {
      setCurrentQuestionIdx(prev => prev + 1);
    }
  };

  const prevQuestion = () => {
    questionStartTime.current = Date.now();
    if (currentQuestionIdx > 0) {
      setCurrentQuestionIdx(prev => prev - 1);
    }
  };

  const finishSection = useCallback(() => {
    if (!session) return;

    const paper = session.papers.find(p => p.paper_number === currentPaper);
    if (!paper) return;

    const nextSectionIdx = currentSectionIdx + 1;

    if (nextSectionIdx < paper.sections.length) {
      // More sections in this paper
      setCurrentSectionIdx(nextSectionIdx);
      setPhase('section_break');
    } else if (currentPaper === 1) {
      // End of Paper 1 -> break before Paper 2
      setPhase('paper_break');
    } else {
      // End of Paper 2 -> complete exam
      completeExam();
    }
  }, [session, currentPaper, currentSectionIdx]);

  const startNextSection = async () => {
    if (!session) return;
    setPhase('section');
    await loadSection(session.id, currentPaper, currentSectionIdx);
  };

  const startPaper2 = async () => {
    if (!session) return;
    setCurrentPaper(2);
    setCurrentSectionIdx(0);
    setPhase('section');
    await loadSection(session.id, 2, 0);
  };

  const completeExam = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const examResults = await mockExamAPI.completeExam(session.id);
      setResults(examResults);
      setPhase('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete exam');
    } finally {
      setLoading(false);
    }
  };

  const handleTimerExpired = useCallback(() => {
    finishSection();
  }, [finishSection]);

  // Current section info
  const currentSection = session?.papers.find(p => p.paper_number === currentPaper)?.sections[currentSectionIdx];
  const sectionConfig = currentSection ? SECTION_CONFIG[currentSection.section] : null;

  // --- INTRO ---
  if (phase === 'intro') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 p-4 md:p-8">
        <div className="max-w-2xl mx-auto">
          <Link href="/" className="text-gray-500 hover:text-gray-900 font-medium text-sm mb-8 inline-block">
            &larr; Back to Dashboard
          </Link>

          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-8 text-white">
              <h1 className="text-3xl font-bold mb-2">GL Assessment Mock Exam</h1>
              <p className="text-indigo-100">Trafford Grammar School Format</p>
            </div>

            <div className="p-8 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-gray-900">2</div>
                  <div className="text-sm text-gray-500 mt-1">Papers</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-gray-900">180</div>
                  <div className="text-sm text-gray-500 mt-1">Questions</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-gray-900">50</div>
                  <div className="text-sm text-gray-500 mt-1">Min / Paper</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-gray-900">4</div>
                  <div className="text-sm text-gray-500 mt-1">Sections / Paper</div>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold text-gray-800">Each paper contains:</h3>
                <div className="space-y-2 text-sm">
                  {[
                    { label: 'English (Comprehension + Vocabulary)', count: '20 Qs', time: '15 min', color: 'bg-blue-100 text-blue-700' },
                    { label: 'Mathematics', count: '30 Qs', time: '19 min', color: 'bg-pink-100 text-pink-700' },
                    { label: 'Non-Verbal Reasoning', count: '20 Qs', time: '8 min', color: 'bg-amber-100 text-amber-700' },
                    { label: 'Verbal Reasoning', count: '20 Qs', time: '8 min', color: 'bg-green-100 text-green-700' },
                  ].map(s => (
                    <div key={s.label} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className={`px-2 py-0.5 rounded font-medium ${s.color}`}>{s.label}</span>
                      <div className="flex gap-4 text-gray-600">
                        <span>{s.count}</span>
                        <span className="font-medium">{s.time}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                <strong>Important:</strong> Each section is timed. When time runs out, you will automatically move to the next section.
                You can navigate between questions within a section.
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
                  {error}
                </div>
              )}

              <button
                onClick={startExam}
                disabled={loading}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-lg rounded-xl shadow-lg transition disabled:opacity-50"
              >
                {loading ? 'Preparing Exam...' : 'Start Mock Exam'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- SECTION (answering questions) ---
  if (phase === 'section') {
    const q = questions[currentQuestionIdx];
    const sectionLabel = sectionConfig?.label || 'Section';
    const totalInSection = questions.length;
    const answeredCount = questions.filter(q => answers[q.id]).length;

    if (loading || !q) {
      return (
        <div className="flex h-screen items-center justify-center bg-gray-50">
          <div className="text-xl font-medium text-gray-600 animate-pulse">Loading section...</div>
        </div>
      );
    }

    return (
      <div className={`min-h-screen ${sectionConfig?.bgColor || 'bg-gray-50'} transition-colors duration-300`}>
        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-white/90 backdrop-blur-sm border-b border-gray-200 shadow-sm">
          <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold uppercase text-gray-400">
                Paper {currentPaper}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${sectionConfig?.color} ${sectionConfig?.bgColor}`}>
                {sectionLabel}
              </span>
              <span className="text-xs text-gray-400">
                {answeredCount}/{totalInSection} answered
              </span>
            </div>
            <ExamTimer
              seconds={sectionTimeLeft}
              onExpired={handleTimerExpired}
            />
          </div>
          {/* Section progress bar */}
          <div className="h-1 bg-gray-100">
            <div
              className={`h-full ${sectionConfig?.buttonColor?.split(' ')[0] || 'bg-gray-600'} transition-all duration-300`}
              style={{ width: `${((currentQuestionIdx + 1) / totalInSection) * 100}%` }}
            />
          </div>
        </div>

        {/* Question content */}
        <div className="max-w-3xl mx-auto px-4 py-8">
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 md:p-8">
            <QuestionCard
              question={q}
              index={currentQuestionIdx}
              total={totalInSection}
              selectedAnswer={answers[q.id]}
              onSelect={handleSelectAnswer}
              sectionName={sectionLabel}
            />
          </div>

          {/* Navigation */}
          <div className="flex justify-between items-center mt-6">
            <button
              onClick={prevQuestion}
              disabled={currentQuestionIdx === 0}
              className="px-6 py-2.5 rounded-xl font-medium text-gray-600 hover:bg-white hover:shadow transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              &larr; Previous
            </button>

            <div className="flex gap-3">
              {/* Question navigator dots */}
              <div className="hidden md:flex items-center gap-1">
                {questions.map((q, i) => (
                  <button
                    key={q.id}
                    onClick={() => { setCurrentQuestionIdx(i); questionStartTime.current = Date.now(); }}
                    className={`w-2.5 h-2.5 rounded-full transition-all ${
                      i === currentQuestionIdx
                        ? `${sectionConfig?.buttonColor?.split(' ')[0] || 'bg-gray-600'} scale-125`
                        : answers[q.id]
                          ? 'bg-gray-400'
                          : 'bg-gray-200'
                    }`}
                    title={`Question ${i + 1}${answers[q.id] ? ' (answered)' : ''}`}
                  />
                ))}
              </div>
            </div>

            {currentQuestionIdx === totalInSection - 1 ? (
              <button
                onClick={finishSection}
                className={`px-6 py-2.5 rounded-xl font-bold text-white shadow-lg transition ${sectionConfig?.buttonColor || 'bg-gray-800 hover:bg-gray-900'}`}
              >
                Finish Section &rarr;
              </button>
            ) : (
              <button
                onClick={nextQuestion}
                className={`px-6 py-2.5 rounded-xl font-bold text-white shadow-lg transition ${sectionConfig?.buttonColor || 'bg-gray-800 hover:bg-gray-900'}`}
              >
                Next &rarr;
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- SECTION BREAK ---
  if (phase === 'section_break') {
    const nextSection = session?.papers.find(p => p.paper_number === currentPaper)?.sections[currentSectionIdx];
    const nextConfig = nextSection ? SECTION_CONFIG[nextSection.section] : null;

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 max-w-lg w-full p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-2">Section Complete</h2>
          <p className="text-gray-500 mb-6">Paper {currentPaper}, Section {currentSectionIdx} of 4</p>

          {nextSection && nextConfig && (
            <div className={`${nextConfig.bgColor} rounded-xl p-4 mb-6`}>
              <p className="text-sm text-gray-500 mb-1">Next section:</p>
              <p className={`text-lg font-bold ${nextConfig.color}`}>{nextConfig.label}</p>
              <p className="text-sm text-gray-600 mt-1">
                {nextSection.question_count} questions - {formatTime(nextSection.time_seconds)}
              </p>
            </div>
          )}

          <button
            onClick={startNextSection}
            disabled={loading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg transition disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Start Next Section'}
          </button>
        </div>
      </div>
    );
  }

  // --- PAPER BREAK ---
  if (phase === 'paper_break') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 max-w-lg w-full p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-2">Paper 1 Complete!</h2>
          <p className="text-gray-500 mb-6">Take a short break before starting Paper 2.</p>

          <div className="bg-gray-50 rounded-xl p-4 mb-6 text-left space-y-2">
            <p className="font-semibold text-gray-700">Paper 2 contains:</p>
            <p className="text-sm text-gray-600">Same structure as Paper 1, with different questions:</p>
            <ul className="text-sm text-gray-600 space-y-1 ml-4 list-disc">
              <li>English (20 questions, 15 min)</li>
              <li>Mathematics (30 questions, 19 min)</li>
              <li>Non-Verbal Reasoning (20 questions, 8 min)</li>
              <li>Verbal Reasoning (20 questions, 8 min)</li>
            </ul>
          </div>

          <button
            onClick={startPaper2}
            disabled={loading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg transition disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Start Paper 2'}
          </button>
        </div>
      </div>
    );
  }

  // --- RESULTS ---
  if (phase === 'results' && results) {
    const percentage = Math.round(results.overall_accuracy * 100);

    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-8">
        <div className="max-w-3xl mx-auto">
          <Link href="/" className="text-gray-500 hover:text-gray-900 font-medium text-sm mb-6 inline-block">
            &larr; Back to Dashboard
          </Link>

          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            {/* Header */}
            <div className={`p-8 text-center ${percentage >= 75 ? 'bg-green-600' : percentage >= 50 ? 'bg-amber-500' : 'bg-red-500'} text-white`}>
              <h1 className="text-3xl font-bold mb-2">Mock Exam Complete</h1>
              <div className="text-6xl font-bold my-4">{percentage}%</div>
              <p className="text-lg opacity-90">
                {results.total_correct} / {results.total_questions} correct
              </p>
            </div>

            {/* Per-paper results */}
            <div className="p-8 space-y-6">
              {results.papers.map((paper: PaperResult) => (
                <div key={paper.paper_number} className="space-y-3">
                  <h3 className="font-bold text-gray-800 text-lg">
                    Paper {paper.paper_number}
                    <span className="text-sm font-normal text-gray-500 ml-2">
                      {paper.total_correct}/{paper.total_questions} ({Math.round(paper.accuracy * 100)}%)
                    </span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {paper.sections.map((section: SectionResult) => {
                      const config = SECTION_CONFIG[section.section];
                      const pct = Math.round(section.accuracy * 100);
                      return (
                        <div
                          key={section.section}
                          className={`${config?.bgColor || 'bg-gray-50'} rounded-xl p-4 border ${config?.borderColor || 'border-gray-200'}`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className={`font-semibold text-sm ${config?.color || 'text-gray-700'}`}>
                              {config?.label || section.section}
                            </span>
                            <span className="font-bold text-gray-800">{pct}%</span>
                          </div>
                          <div className="w-full bg-white/50 rounded-full h-2 mb-1">
                            <div
                              className={`h-full rounded-full ${config?.buttonColor?.split(' ')[0] || 'bg-gray-600'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <div className="text-xs text-gray-500">
                            {section.correct}/{section.total} correct
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}

              {/* Subject breakdown */}
              <div className="border-t pt-6">
                <h3 className="font-bold text-gray-800 text-lg mb-4">Overall by Subject</h3>
                <div className="space-y-3">
                  {Object.entries(results.subject_breakdown).map(([subject, stats]) => {
                    const config = SECTION_CONFIG[subject];
                    const pct = Math.round((stats.accuracy as number) * 100);
                    return (
                      <div key={subject} className="flex items-center gap-4">
                        <span className={`w-40 text-sm font-medium ${config?.color || 'text-gray-700'}`}>
                          {config?.label || subject}
                        </span>
                        <div className="flex-1 bg-gray-100 rounded-full h-3">
                          <div
                            className={`h-full rounded-full ${config?.buttonColor?.split(' ')[0] || 'bg-gray-600'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-sm font-bold text-gray-800 w-12 text-right">{pct}%</span>
                        <span className="text-xs text-gray-500 w-16">
                          {stats.correct}/{stats.total}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Link
                  href="/"
                  className="flex-1 py-3 text-center bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-xl transition"
                >
                  Back to Dashboard
                </Link>
                <button
                  onClick={() => {
                    setPhase('intro');
                    setSession(null);
                    setResults(null);
                    setAnswers({});
                  }}
                  className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow transition"
                >
                  Take Another Exam
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Fallback loading
  return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
      <div className="text-xl font-medium text-gray-600 animate-pulse">Loading...</div>
    </div>
  );
}
