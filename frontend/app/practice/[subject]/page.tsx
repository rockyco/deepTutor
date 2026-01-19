import { Suspense } from "react";
import PracticeClient from "./PracticeClient";

// Generate static params for all subjects
export function generateStaticParams() {
  return [
    { subject: "english" },
    { subject: "maths" },
    { subject: "verbal_reasoning" },
    { subject: "non_verbal_reasoning" },
  ];
}

export default function PracticePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <PracticeClient />
    </Suspense>
  );
}
