interface StatCardProps {
  label: string;
  value: number | string;
  sub?: string;
  color?: "blue" | "yellow" | "red" | "gray";
}

const colorMap = {
  blue: {
    text: "text-blue-400",
    glow: "shadow-blue-500/5",
    border: "border-blue-500/10",
    dot: "bg-blue-500",
  },
  yellow: {
    text: "text-yellow-400",
    glow: "shadow-yellow-500/5",
    border: "border-yellow-500/10",
    dot: "bg-yellow-500",
  },
  red: {
    text: "text-red-400",
    glow: "shadow-red-500/5",
    border: "border-red-500/10",
    dot: "bg-red-500",
  },
  gray: {
    text: "text-gray-400",
    glow: "shadow-none",
    border: "border-white/[0.06]",
    dot: "bg-gray-500",
  },
};

export function StatCard({ label, value, sub, color = "blue" }: StatCardProps) {
  const c = colorMap[color];

  return (
    <div
      className={`relative bg-[#111] border ${c.border} rounded-lg p-4 shadow-lg ${c.glow} hover:border-white/[0.1] transition-all duration-150`}
    >
      {color !== "gray" && (
        <div className={`absolute inset-x-0 top-0 h-px ${c.dot} opacity-10 rounded-t-lg`} />
      )}

      <div className="flex items-center gap-2 mb-2">
        <span className={`w-1 h-1 rounded-full ${c.dot} opacity-60`} />
        <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500">
          {label}
        </p>
      </div>

      <p className={`text-2xl font-semibold font-mono tracking-tight ${c.text}`}>
        {value}
      </p>

      {sub && (
        <p className="text-[11px] text-gray-600 mt-1.5 leading-tight">{sub}</p>
      )}
    </div>
  );
}
