"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Loader2 } from "lucide-react";

interface RecoveryProgressProps {
  steps: { label: string; status: "complete" | "active" | "pending" }[];
}

export default function RecoveryProgress({ steps }: RecoveryProgressProps) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Autonomous Recovery
      </h3>
      <div className="space-y-3">
        {steps.map((step, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-3"
          >
            <div className="flex-shrink-0">
              {step.status === "complete" ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              ) : step.status === "active" ? (
                <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-zinc-300 dark:border-zinc-600" />
              )}
            </div>
            <span
              className={`text-sm ${
                step.status === "complete"
                  ? "text-zinc-400 line-through"
                  : step.status === "active"
                  ? "text-blue-600 dark:text-blue-400 font-medium"
                  : "text-zinc-500"
              }`}
            >
              {step.label}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
