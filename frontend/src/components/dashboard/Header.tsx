"use client";

export default function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
          <span className="text-white font-bold text-sm">RR</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight">ReRoute AI</h1>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-zinc-500">Jeevan</span>
        <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-sm font-medium">
          J
        </div>
      </div>
    </header>
  );
}
