import { cn } from "@/lib/utils";

function formatMatchPercent(score: number): number {
  return Math.min(99, Math.round(score * 100));
}

function getMatchInfo(score: number): {
  percent: number;
  label: string;
  toneClass: string;
} {
  const percent = formatMatchPercent(score);

  if (percent >= 80) {
    return {
      percent,
      label: "Highly recommended",
      toneClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
  }

  if (percent >= 60) {
    return {
      percent,
      label: "Strong match",
      toneClass: "bg-amber-50 text-amber-700 border-amber-200",
    };
  }

  if (percent >= 40) {
    return {
      percent,
      label: "Moderate match",
      toneClass: "bg-sky-50 text-sky-700 border-sky-200",
    };
  }

  return {
    percent,
    label: "Lower match",
    toneClass: "bg-slate-50 text-slate-700 border-slate-200",
  };
}

export function MatchBadge({ score }: { score: number }) {
  const { percent, label, toneClass } = getMatchInfo(score);

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-tight shadow-sm",
        "bg-card/80 backdrop-blur-sm",
        toneClass,
      )}
    >
      <span>{percent}% match</span>
      <span className="ml-1 hidden sm:inline text-[10px] font-medium opacity-90">
        • {label}
      </span>
    </span>
  );
}
