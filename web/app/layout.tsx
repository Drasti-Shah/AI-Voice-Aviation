import "./globals.css";
import type { Metadata } from "next";
import Shell from "@/components/Shell";

export const metadata: Metadata = {
  title: "Aviation Voice Assistant",
  description: "AI-powered voice assistant for flight status, baggage and check-in.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
