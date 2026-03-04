import { Badge } from "@/components/ui/badge";
import type { ContributingProgram } from "@/types/api";
import { cn } from "@/lib/utils";

const MAX_VISIBLE = 3;

interface OptionBadgeProps {
  programs: ContributingProgram[];
  className?: string;
}

export function OptionBadges({ programs, className }: OptionBadgeProps) {
  if (!programs?.length) return null;

  const visible = programs.slice(0, MAX_VISIBLE);
  const remaining = programs.length - MAX_VISIBLE;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex flex-wrap gap-1.5">
        {visible.map((p) => (
          <Badge
            key={`${p.name}-${p.type}`}
            variant="outline"
            className={cn(
              "text-[10px] font-medium px-2.5 py-1 gap-1.5 items-center justify-center leading-tight",
              p.type === "option"
                ? "bg-primary/5 text-primary border-primary/20"
                : "bg-muted/50 text-muted-foreground border-muted",
            )}
            title={
              p.type === "option" ? `Option: ${p.name}` : `Minor: ${p.name}`
            }
          >
            <span className="opacity-75 text-[10px] uppercase shrink-0">
              {p.type === "option" ? "Opt" : "Min"}
            </span>
            <span>{p.name}</span>
          </Badge>
        ))}
        {remaining > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] font-medium px-2.5 py-1 bg-muted/30 text-muted-foreground items-center justify-center"
            title={programs
              .slice(MAX_VISIBLE)
              .map((p) => p.name)
              .join(", ")}
          >
            +{remaining} more
          </Badge>
        )}
      </div>
    </div>
  );
}
