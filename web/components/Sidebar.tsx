"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/dial", label: "Dial", icon: "📞" },
  { href: "/calls", label: "Calls", icon: "🗂" },
  { href: "/campaigns", label: "Campaigns", icon: "📢" },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }
  return (
    <aside className="w-56 bg-slate-900 text-slate-100 min-h-screen flex flex-col">
      <div className="px-5 py-6 border-b border-slate-800">
        <div className="text-lg font-bold leading-tight">Aviation</div>
        <div className="text-xs text-slate-400">Voice Assistant</div>
      </div>
      <nav className="flex-1 py-4">
        {NAV.map((item) => {
          const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-5 py-2.5 text-sm transition ${
                active
                  ? "bg-slate-800 text-white border-l-2 border-blue-400"
                  : "text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <button
        onClick={handleLogout}
        className="mx-3 mb-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 rounded text-left flex items-center gap-2"
      >
        <span>🚪</span>
        <span>Log out</span>
      </button>
      <div className="px-5 py-3 text-xs text-slate-500 border-t border-slate-800">
        v0.1 · localhost
      </div>
    </aside>
  );
}
