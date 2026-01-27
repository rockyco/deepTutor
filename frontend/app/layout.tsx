import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeepTutor | Premium AI 11+ Prep",
  description: "AI-powered 11+ exam preparation for GL Assessment",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen bg-surface font-sans antialiased text-slate-800 selection:bg-primary-200 selection:text-primary-900">
        {children}
      </body>
    </html>
  );
}
