import { useState, useEffect, useCallback } from "react";
import { Command } from "cmdk";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Plus, X, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";

const SEARCH_DEBOUNCE_MS = 300;

export interface CompletedCoursesManagerProps {
  completedCourses: string[];
  onAdd: (code: string) => void;
  onRemove: (code: string) => void;
  onClearAll?: () => void;
  compact?: boolean;
  className?: string;
}

export function CompletedCoursesManager({
  completedCourses,
  onAdd,
  onRemove,
  onClearAll,
  compact = false,
  className,
}: CompletedCoursesManagerProps) {
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<{ code: string; title: string }[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const fetchCourses = useCallback(async (q: string) => {
    if (!q || q.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    try {
      const results = await api.searchCourses(q.trim(), 20);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchCourses(search), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search, fetchCourses]);

  const handleSelect = useCallback(
    (code: string) => {
      if (!completedCourses.includes(code)) {
        onAdd(code);
      }
      setSearch("");
    },
    [completedCourses, onAdd]
  );

  const showFull = !compact || expanded;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <Label className="text-sm font-medium">
          Completed Courses ({completedCourses.length})
        </Label>
        {compact && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-8 px-2"
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        )}
      </div>

      {showFull && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            {completedCourses.map((code) => (
              <Badge
                key={code}
                variant="secondary"
                className="gap-1 pr-1 py-1"
              >
                {code}
                <button
                  type="button"
                  onClick={() => onRemove(code)}
                  className="rounded-full p-0.5 hover:bg-muted transition-colors"
                  aria-label={`Remove ${code}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
            {completedCourses.length > 0 && onClearAll && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClearAll}
                className="h-7 gap-1.5 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear all
              </Button>
            )}
          </div>

          <div className="flex gap-2">
            <Command
              shouldFilter={false}
              className="flex-1 rounded-lg border border-input bg-background overflow-hidden"
            >
              <div className="flex items-center border-b border-input px-3">
                <Plus className="w-4 h-4 text-muted-foreground mr-2" />
                <Command.Input
                  placeholder="Search courses to add (min 2 chars)..."
                  value={search}
                  onValueChange={setSearch}
                  className="flex h-9 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
              <Command.List className="max-h-[200px] overflow-auto p-1">
                {searchLoading && (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    Searching...
                  </div>
                )}
                {!searchLoading && search.trim().length >= 2 && searchResults.length === 0 && (
                  <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                    No courses found.
                  </Command.Empty>
                )}
                {!searchLoading &&
                  searchResults
                    .filter((r) => !completedCourses.includes(r.code))
                    .map((r) => (
                      <Command.Item
                        key={r.code}
                        value={r.code}
                        onSelect={() => handleSelect(r.code)}
                        className="flex cursor-pointer gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
                      >
                        <span className="font-medium">{r.code}</span>
                        <span className="text-muted-foreground truncate">{r.title}</span>
                      </Command.Item>
                    ))}
              </Command.List>
            </Command>
          </div>
        </>
      )}

      {compact && !expanded && completedCourses.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {completedCourses.slice(0, 5).join(", ")}
          {completedCourses.length > 5 && ` +${completedCourses.length - 5} more`}
        </p>
      )}
    </div>
  );
}
