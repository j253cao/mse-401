import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  computeOptionsProgress,
  type OptionProgress,
  type ListProgress,
} from "@/utils/optionsProgress";
import {
  ChevronDown,
  ChevronRight,
  Target,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import optionsIndex from "@/data/options_index.json";

const optionUrls: Record<string, string> = Object.fromEntries(
  optionsIndex.links.map((l) => [l.name, l.url]),
);
import { cn } from "@/lib/utils";

interface OptionsTrackerProps {
  completedCourses: string[];
}

function ListRow({ list }: { list: ListProgress }) {
  const completedCount = list.completed_courses.length;
  const fillPercent =
    list.required_count > 0
      ? Math.min((completedCount / list.required_count) * 100, 100)
      : 0;

  // Use list_description as subtitle only when it differs meaningfully from the name
  const showDescription =
    list.list_description &&
    list.list_description !== list.list_name &&
    !list.list_name.includes(list.list_description);

  return (
    <div className="py-2 space-y-1.5 min-w-0">
      <div className="flex items-start justify-between gap-2 min-w-0">
        <span className="text-sm font-medium line-clamp-2 min-w-0">
          {list.list_name}
        </span>
        <span
          className={cn(
            "text-xs font-medium whitespace-nowrap pt-0.5",
            list.is_satisfied ? "text-green-500" : "text-muted-foreground",
          )}
        >
          {completedCount}/{list.required_count}
        </span>
      </div>
      {showDescription && (
        <p className="text-xs text-muted-foreground line-clamp-2">
          {list.list_description}
        </p>
      )}
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            list.is_satisfied ? "bg-green-500" : "bg-amber-500",
          )}
          style={{ width: `${fillPercent}%` }}
        />
      </div>
      {list.completed_courses.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {list.completed_courses.map((code) => (
            <Badge
              key={code}
              variant="secondary"
              className="text-[10px] px-1.5 py-0"
            >
              {code}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function OptionRow({ option }: { option: OptionProgress }) {
  const [expanded, setExpanded] = useState(false);
  const fillPercent = Math.round(option.completion_ratio * 100);
  const url = optionUrls[option.option_name];

  return (
    <div className="border-b border-border/50 last:border-b-0">
      <div className="flex items-center gap-1">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-1 min-w-0 flex items-center gap-3 py-3 px-1 text-left hover:bg-muted/30 rounded-md transition-colors"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium">{option.option_name}</span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-20 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  option.completion_ratio === 1
                    ? "bg-green-500"
                    : option.completion_ratio > 0
                      ? "bg-amber-500"
                      : "bg-muted",
                )}
                style={{ width: `${fillPercent}%` }}
              />
            </div>
            <span
              className={cn(
                "text-xs font-medium whitespace-nowrap",
                option.completion_ratio === 1
                  ? "text-green-500"
                  : "text-muted-foreground",
              )}
            >
              {option.satisfied_count}/{option.total_lists}
            </span>
          </div>
        </button>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-muted/50 transition-colors flex-shrink-0"
            title="View in academic calendar"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
      {expanded && (
        <div className="pl-8 pr-2 pb-3 space-y-1 divide-y divide-border/30">
          {option.lists.map((list, i) => (
            <ListRow key={i} list={list} />
          ))}
        </div>
      )}
    </div>
  );
}

export function OptionsTracker({ completedCourses }: OptionsTrackerProps) {
  const progress = useMemo(
    () => computeOptionsProgress(completedCourses),
    [completedCourses],
  );

  return (
    <Card className="glass-card overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="w-5 h-5 text-primary" />
          Engineering Options Progress
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Track how your completed courses contribute toward engineering options
        </p>
      </CardHeader>
      <CardContent>
        {completedCourses.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <BookOpen className="w-8 h-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              Add completed courses above to see your progress toward
              engineering options.
            </p>
          </div>
        ) : (
          <div>
            {progress.map((option) => (
              <OptionRow key={option.option_name} option={option} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
