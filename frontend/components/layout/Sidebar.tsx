"use client";

import { useState } from "react";
import { LayoutDashboard, Plane, AlertTriangle, RefreshCcw, Hotel, Truck, Bell, Settings, FileText, ShieldAlert } from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  disruptionCount?: number;
}

export default function Sidebar({ activeTab, setActiveTab, disruptionCount = 0 }: SidebarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "trips", label: "My Trips", icon: Plane },
    { id: "disruptions", label: "Disruptions", icon: AlertTriangle, badge: disruptionCount > 0 ? disruptionCount : undefined },
    { id: "rebookings", label: "Rebookings", icon: RefreshCcw },
    { id: "hotel", label: "Hotel Recovery", icon: Hotel },
    { id: "transfers", label: "Transfers", icon: Truck },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "reports", label: "Audit Reports", icon: FileText },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="w-64 bg-zinc-900 border-r border-zinc-800 text-zinc-300 flex flex-col justify-between hidden md:flex shrink-0 min-h-screen">
      <div>
        {/* Brand Logo & Header */}
        <div className="p-6 border-b border-zinc-800 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <Plane className="w-5 h-5 rotate-45" />
          </div>
          <div>
            <h1 className="font-bold text-white text-base tracking-wide flex items-center gap-1.5">
              ReRoute <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">AI</span>
            </h1>
            <p className="text-[10px] text-zinc-500 tracking-tight uppercase font-medium">Autonomous Travel Recovery</p>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                    : "hover:bg-zinc-800/60 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-zinc-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-2 py-0.5 text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-full">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Engine Status & User Profile Footer */}
      <div className="p-4 border-t border-zinc-800 space-y-4">
        <div className="bg-zinc-800/50 border border-zinc-800 rounded-xl p-3.5 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-medium text-zinc-300 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
              AI Recovery Engine
            </span>
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              ACTIVE
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 leading-relaxed">
            Continuous trip monitoring and connection risk analysis enabled.
          </p>
        </div>

        <div className="flex items-center gap-3 px-2 pt-1">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xs">
            J
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">Jeevan</p>
            <p className="text-[10px] text-zinc-500 truncate">Enterprise Traveler</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
