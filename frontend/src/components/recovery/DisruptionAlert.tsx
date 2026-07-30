"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Clock } from "lucide-react";

interface DisruptionAlertProps {
  flight: string;
  delayMinutes: number;
  affectedFlight: string;
  connectionBuffer: number;
}

export default function DisruptionAlert({
  flight,
  delayMinutes,
  affectedFlight,
  connectionBuffer,
}: DisruptionAlertProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-red-100 dark:bg-red-900/40 rounded-lg">
          <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="font-semibold text-red-900 dark:text-red-100">
            Disruption Detected
          </h3>
          <p className="text-sm text-red-700 dark:text-red-300">
            Flight {flight} delayed by {delayMinutes} minutes
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-4">
        <div className="bg-white/50 dark:bg-red-900/20 rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 mb-1">
            <Clock className="w-4 h-4" />
            <span>Affected Connection</span>
          </div>
          <p className="font-semibold text-lg">{affectedFlight}</p>
        </div>
        <div className="bg-white/50 dark:bg-red-900/20 rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 mb-1">
            <Clock className="w-4 h-4" />
            <span>Connection Buffer</span>
          </div>
          <p className="font-semibold text-lg text-red-700 dark:text-red-300">
            {connectionBuffer} min
          </p>
        </div>
      </div>
    </motion.div>
  );
}
