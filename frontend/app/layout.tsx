import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "11+ Deep Tutor - Master Your GL Assessment",
  description:
    "AI-powered 11+ exam preparation for GL Assessment. Practice English, Maths, Verbal Reasoning, and Non-verbal Reasoning.",
  keywords: [
    "11+",
    "GL Assessment",
    "grammar school",
    "verbal reasoning",
    "non-verbal reasoning",
    "11 plus",
    "exam preparation",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
