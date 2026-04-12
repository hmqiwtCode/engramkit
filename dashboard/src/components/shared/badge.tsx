interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "semantic" | "lexical" | "stale" | "secret";
}

const variants = {
  default: "bg-white/[0.04] text-gray-400 border-white/[0.06]",
  semantic: "bg-blue-500/8 text-blue-400 border-blue-500/15",
  lexical: "bg-violet-500/8 text-violet-400 border-violet-500/15",
  stale: "bg-amber-500/8 text-amber-400 border-amber-500/15",
  secret: "bg-red-500/8 text-red-400 border-red-500/15",
};

export function Badge({ children, variant = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-medium font-mono leading-none ${variants[variant]}`}
    >
      {children}
    </span>
  );
}
