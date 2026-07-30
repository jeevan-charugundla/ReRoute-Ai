export function formatTime(isoString: string): string {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDate(isoString: string): string {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatCurrency(amount: number): string {
  return `?${amount.toLocaleString("en-IN")}`;
}

export function formatConnectionBuffer(minutes: number): string {
  if (minutes >= 0) {
    return `+${minutes} min`;
  }
  return `${minutes} min`;
}
