import { useState, useContext, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { RecommendationsContext } from "./RecommendationsContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Search,
  Dice5,
  FileText,
  Loader2,
  BookOpen,
  GraduationCap,
  Filter,
  X,
  Sparkles,
  RefreshCw,
  ArrowRight,
  ExternalLink,
  Compass,
  LayoutGrid,
  ChevronDown,
} from "lucide-react";
import { api } from "@/services/api";
import type { Course } from "@/types/api";
import { CompletedCoursesManager } from "@/components/CompletedCoursesManager";
import { FILTER_DEPARTMENTS } from "@/constants/filterDepartments";
import { ENGINEERING_PROGRAMS } from "@/constants/engineeringPrograms";
import { OptionBadges } from "@/components/OptionBadge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

function uwFlowUrl(code: string) {
  return `https://uwflow.com/course/${code.replace(/\s+/g, "").toLowerCase()}`;
}

/**
 * Check if a course has program-level prerequisites that don't match the user's program.
 * Returns true if the course requires specific programs and the user's program isn't one of them.
 */
function needsOverride(prereqs: string | null | undefined, programCode: string): boolean {
  if (!prereqs || !programCode) return false;
  const programStudentParts = prereqs
    .split(";")
    .map((s) => s.trim())
    .filter((s) => /\bstudents\b/i.test(s));
  if (programStudentParts.length === 0) return false;
  const program = ENGINEERING_PROGRAMS.find((p) => p.code === programCode);
  if (!program) return false;
  const nameLower = program.displayName.toLowerCase();
  const codeLower = program.code.toLowerCase();
  // Match full display name, program code, or any leading word subset
  // (e.g. "Mechatronics" matches "Mechatronics Engineering")
  const nameWords = nameLower.split(" ");
  return !programStudentParts.some((part) => {
    const p = part.toLowerCase();
    if (p.includes(nameLower) || p.includes(codeLower)) return true;
    // Check if part contains any prefix of the display name words
    // e.g. "mechatronics" should match "mechatronics engineering"
    for (let i = nameWords.length; i >= 1; i--) {
      if (p.includes(nameWords.slice(0, i).join(" "))) return true;
    }
    return false;
  });
}

const OVERRIDE_BADGE_CLASS =
  "bg-red-500/15 text-red-400 border border-red-500/30";

export default function RecommendationPage() {
  const {
    recommendedCourses,
    completedCourses,
    setCompletedCourses,
    incomingLevel,
    programCode,
    search,
    setSearch,
    filteredCourses,
    setFilteredCourses,
    departments,
    setDepartments,
    includeOtherDepts,
    setIncludeOtherDepts,
    includeUndergrad,
    setIncludeUndergrad,
    includeGrad,
    setIncludeGrad,
    selectedOptions,
    setSelectedOptions,
    explorationMode,
    setExplorationMode,
    hasSearched,
    setHasSearched,
  } = useContext(RecommendationsContext);

  const isUndergrad = !!incomingLevel;

  const [randomCourse, setRandomCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(false);
  const [randomLoading, setRandomLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [similarCourses, setSimilarCourses] = useState<Course[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [optionSearch, setOptionSearch] = useState("");
  const [optionsAndMinors, setOptionsAndMinors] = useState<{
    options: { name: string }[];
    minors: { name: string }[];
  } | null>(null);

  const [highValueCourses, setHighValueCourses] = useState<Course[]>([]);
  const [highValueLoading, setHighValueLoading] = useState(false);
  const [highValueError, setHighValueError] = useState(false);
  const searchRequestSeq = useRef(0);

  // Only show high-value block for first-year (1A/1B) or new users (no level set)
  const showHighValueBlock =
    !hasSearched &&
    (incomingLevel === "" || incomingLevel === "1A" || incomingLevel === "1B");

  const fetchHighValueCourses = useCallback(() => {
    if (!showHighValueBlock) return;
    setHighValueLoading(true);
    setHighValueError(false);
    api
      .getHighValueCourses(incomingLevel || undefined, 12)
      .then((courses) => {
        setHighValueCourses(courses);
        setHighValueError(false);
      })
      .catch(() => {
        setHighValueCourses([]);
        setHighValueError(true);
      })
      .finally(() => setHighValueLoading(false));
  }, [showHighValueBlock, incomingLevel, programCode]);

  useEffect(() => {
    if (showHighValueBlock && !highValueLoading) {
      fetchHighValueCourses();
    }
  }, [showHighValueBlock, incomingLevel, fetchHighValueCourses]);

  useEffect(() => {
    if (!optionsAndMinors) {
      api
        .getOptionsAndMinors()
        .then(setOptionsAndMinors)
        .catch(() => setOptionsAndMinors({ options: [], minors: [] }));
    }
  }, [optionsAndMinors]);

  useEffect(() => {
    if (!selectedCourse) {
      setSimilarCourses([]);
      return;
    }
    let cancelled = false;
    setSimilarLoading(true);
    api
      .getSimilarCourses(selectedCourse.code)
      .then((courses) => {
        if (!cancelled) {
          const antireqs = selectedCourse.antireqs
            ? selectedCourse.antireqs.split(",").map((s) => s.trim())
            : [];
          setSimilarCourses(
            courses.filter((c) => {
              if (antireqs.includes(c.code)) return false;
              if (isUndergrad) {
                const num = parseInt(c.code.replace(/\D/g, ""), 10);
                if (!isNaN(num) && num >= 600) return false;
              }
              return true;
            }),
          );
        }
      })
      .catch(() => {
        if (!cancelled) setSimilarCourses([]);
      })
      .finally(() => {
        if (!cancelled) setSimilarLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCourse, isUndergrad]);

  const allPrograms = optionsAndMinors
    ? [
        ...optionsAndMinors.options.map((o) => ({
          name: o.name,
          type: "option" as const,
        })),
        ...optionsAndMinors.minors.map((m) => ({
          name: m.name,
          type: "minor" as const,
        })),
      ]
    : [];
  const optionSearchLower = optionSearch.trim().toLowerCase();
  const optionMatches = optionSearchLower
    ? allPrograms.filter(
        (p) =>
          p.name.toLowerCase().includes(optionSearchLower) &&
          !selectedOptions.includes(p.name),
      )
    : [];

  const executeSearch = useCallback(async (optionsOverride?: string[]) => {
    const requestId = ++searchRequestSeq.current;
    const opts = optionsOverride ?? selectedOptions;
    if (!search.trim() && opts.length === 0) {
      // Invalidate in-flight searches when the active filter/query set is empty.
      setHasSearched(false);
      setFilteredCourses([]);
      setError(null);
      setLoading(false);
      return;
    }
    setHasSearched(true);
    setLoading(true);
    setError(null);
    try {
      const selectedDepts = Object.entries(departments)
        .filter(([, v]) => v)
        .map(([k]) => k);
      const filters = {
        include_undergrad: includeUndergrad,
        include_grad: includeGrad,
        department: selectedDepts,
        include_other_depts: includeOtherDepts,
        completed_courses: completedCourses,
        ignore_dependencies: explorationMode,
        ...(opts.length > 0 && { options: opts }),
        ...(incomingLevel && { incoming_level: incomingLevel }),
        ...(programCode && incomingLevel && { user_department: programCode }),
      };

      const courses = await api.recommend([search.trim() || ""], filters);
      if (requestId !== searchRequestSeq.current) return;
      setFilteredCourses(courses);
    } catch {
      if (requestId !== searchRequestSeq.current) return;
      setFilteredCourses([]);
      setError("Could not fetch recommendations.");
    } finally {
      if (requestId !== searchRequestSeq.current) return;
      setLoading(false);
    }
  }, [search, selectedOptions, departments, includeUndergrad, includeGrad, includeOtherDepts, completedCourses, explorationMode, incomingLevel, programCode, setHasSearched, setFilteredCourses]);

  function setOptionsAndSearch(nextOptions: string[]) {
    setSelectedOptions(nextOptions);
    executeSearch(nextOptions);
  }

  function addOption(name: string) {
    const trimmed = name.trim();
    if (!trimmed || selectedOptions.includes(trimmed)) return;
    setOptionsAndSearch([...selectedOptions, trimmed]);
  }

  function removeOption(name: string) {
    setOptionsAndSearch(selectedOptions.filter((n) => n !== name));
  }

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    executeSearch();
  }

  function toggleOption(name: string) {
    const next = selectedOptions.includes(name)
      ? selectedOptions.filter((n) => n !== name)
      : [...selectedOptions, name];
    setOptionsAndSearch(next);
  }

  async function handleRandomCourse() {
    setRandomLoading(true);
    setError(null);
    try {
      const course = await api.getRandomCourse();
      setRandomCourse(course);
    } catch {
      setRandomCourse(null);
      setError("Could not fetch random course.");
    } finally {
      setRandomLoading(false);
    }
  }

  const activeFiltersCount = [
    !includeUndergrad,
    !includeGrad && !isUndergrad,
    ...Object.values(departments).filter((v) => !v),
    !includeOtherDepts,
    completedCourses.length > 0,
    selectedOptions.length > 0,
  ].filter(Boolean).length;

  return (
    <div className="min-h-main">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-[1fr,320px] gap-8">
          {/* Main Content */}
          <div className="space-y-6">
            <Tabs defaultValue="search" className="w-full">
              {/* <TabsList className="w-full sm:w-auto grid grid-cols-2 sm:inline-flex h-11 bg-card border border-border">
                <TabsTrigger
                  value="search"
                  className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Search className="w-4 h-4" />
                  Search
                </TabsTrigger>
                <TabsTrigger
                  value="recommended"
                  className="gap-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Sparkles className="w-4 h-4" />
                  Recommended
                  {recommendedCourses.length > 0 && (
                    <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                      {recommendedCourses.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList> */}

              {/* Search Tab */}
              <TabsContent value="search" className="mt-6 space-y-6">
                {/* Search Bar */}
                <form onSubmit={handleSearchSubmit} className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="Describe the course you're looking for..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="h-12 pl-12 pr-24 text-base bg-card border-border focus:border-primary"
                    />
                    <Button
                      type="submit"
                      size="sm"
                      className="absolute right-2 top-1/2 -translate-y-1/2"
                      disabled={loading}
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        "Search"
                      )}
                    </Button>
                  </div>

                  {/* Filter Toggle */}
                  <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-4">
                    <Button
                      type="button"
                      variant={explorationMode ? "default" : "outline"}
                      size="sm"
                      onClick={() => setExplorationMode(!explorationMode)}
                      className={cn(
                        "gap-2",
                        explorationMode && "bg-amber-500 hover:bg-amber-600 text-white border-amber-500 shadow-amber-500/25 shadow-md"
                      )}
                    >
                      <Compass className="w-4 h-4" />
                      {explorationMode ? "Exploring" : "Explore"}
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="gap-2"
                        >
                          <LayoutGrid className="w-4 h-4" />
                          Options
                          <ChevronDown className="w-3 h-3 opacity-50" />
                          {selectedOptions.length > 0 && (
                            <Badge variant="default" className="h-5 px-1.5">
                              {selectedOptions.length}
                            </Badge>
                          )}
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" className="w-56">
                        <DropdownMenuLabel>Engineering Options</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        {optionsAndMinors ? (
                          optionsAndMinors.options.map((opt) => (
                            <DropdownMenuCheckboxItem
                              key={opt.name}
                              checked={selectedOptions.includes(opt.name)}
                              onCheckedChange={() => toggleOption(opt.name)}
                              onSelect={(e) => e.preventDefault()}
                            >
                              {opt.name}
                            </DropdownMenuCheckboxItem>
                          ))
                        ) : (
                          <div className="px-2 py-3 text-sm text-muted-foreground text-center">
                            <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1" />
                            Loading...
                          </div>
                        )}
                        {selectedOptions.length > 0 && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuCheckboxItem
                              checked={false}
                              onCheckedChange={() => {
                                setOptionsAndSearch([]);
                              }}
                              onSelect={(e) => e.preventDefault()}
                              className="text-muted-foreground"
                            >
                              Clear all
                            </DropdownMenuCheckboxItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowFilters(!showFilters)}
                      className="gap-2"
                    >
                      <Filter className="w-4 h-4" />
                      Filters
                      {activeFiltersCount > 0 && (
                        <Badge variant="default" className="h-5 px-1.5">
                          {activeFiltersCount}
                        </Badge>
                      )}
                    </Button>

                    {/* Active filter badges */}
                    <div className="flex flex-wrap gap-2">
                      {!includeUndergrad && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => setIncludeUndergrad(true)}
                        >
                          No Undergrad
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                      {!includeGrad && !isUndergrad && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => setIncludeGrad(true)}
                        >
                          No Grad
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                      {(Object.values(departments).filter(Boolean).length <
                        FILTER_DEPARTMENTS.length ||
                        !includeOtherDepts) && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => {
                            setDepartments(
                              Object.fromEntries(
                                FILTER_DEPARTMENTS.map((d) => [
                                  d.code,
                                  true,
                                ]),
                              ),
                            );
                            setIncludeOtherDepts(true);
                          }}
                        >
                          {FILTER_DEPARTMENTS.length -
                            Object.values(departments).filter(Boolean).length +
                            (includeOtherDepts ? 0 : 1)}{" "}
                          depts excluded
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                      {selectedOptions.length > 0 && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => {
                            setOptionsAndSearch([]);
                          }}
                        >
                          {selectedOptions.length} option
                          {selectedOptions.length !== 1 ? "s" : ""} selected
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                    </div>
                  </div>
                  {explorationMode && (
                    <p className="text-xs text-amber-500 font-medium mt-1">
                      Explore mode on — prerequisites are being ignored
                    </p>
                  )}
                  </div>

                  {/* Filters Panel */}
                  {showFilters && (
                    <Card className="glass-card">
                      <CardContent className="pt-6 space-y-6">
                        {/* Level Filters - gold = included */}
                        <div className="space-y-2">
                          <Label className="text-sm font-medium">
                            Course Level
                          </Label>
                          <div className="flex rounded-lg border border-input p-1 bg-muted/30">
                            <button
                              type="button"
                              onClick={() =>
                                setIncludeUndergrad(!includeUndergrad)
                              }
                              className={cn(
                                "flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors mr-2",
                                includeUndergrad
                                  ? "bg-primary text-primary-foreground shadow"
                                  : "text-muted-foreground hover:text-foreground",
                              )}
                            >
                              Undergraduate
                            </button>
                            <button
                              type="button"
                              onClick={() => setIncludeGrad(!includeGrad)}
                              className={cn(
                                "flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors",
                                includeGrad
                                  ? "bg-primary text-primary-foreground shadow"
                                  : "text-muted-foreground hover:text-foreground",
                              )}
                            >
                              Graduate
                            </button>
                          </div>
                        </div>

                        {/* Department Filters - grid with select all */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label className="text-sm font-medium">
                              Departments
                            </Label>
                            <div className="flex gap-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() =>
                                  setDepartments(
                                    Object.fromEntries(
                                      FILTER_DEPARTMENTS.map((d) => [
                                        d.code,
                                        true,
                                      ]),
                                    ),
                                  )
                                }
                              >
                                All
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() =>
                                  setDepartments(
                                    Object.fromEntries(
                                      FILTER_DEPARTMENTS.map((d) => [
                                        d.code,
                                        false,
                                      ]),
                                    ),
                                  )
                                }
                              >
                                None
                              </Button>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto rounded-lg border border-input p-2 bg-muted/20">
                            {FILTER_DEPARTMENTS.map((dept) => (
                              <div
                                key={dept.code}
                                className="flex items-center gap-2 min-w-0"
                              >
                                <Checkbox
                                  id={dept.code}
                                  checked={departments[dept.code] ?? true}
                                  onCheckedChange={(checked) =>
                                    setDepartments({
                                      ...departments,
                                      [dept.code]: checked as boolean,
                                    })
                                  }
                                />
                                <Label
                                  htmlFor={dept.code}
                                  className="text-sm cursor-pointer flex-1 min-w-0 truncate"
                                  title={`${dept.abbr} — ${dept.fullName}`}
                                >
                                  <span className="font-medium">
                                    {dept.abbr}
                                  </span>
                                  <span className="text-muted-foreground">
                                    {" "}
                                    {dept.fullName}
                                  </span>
                                </Label>
                              </div>
                            ))}
                            <div className="flex items-center gap-2 min-w-0 col-span-2 sm:col-span-3 border-t border-input pt-2 mt-1">
                              <Checkbox
                                id="other-depts"
                                checked={includeOtherDepts}
                                onCheckedChange={(checked) =>
                                  setIncludeOtherDepts(checked as boolean)
                                }
                              />
                              <Label
                                htmlFor="other-depts"
                                className="text-sm cursor-pointer flex-1 min-w-0 truncate"
                                title="Include non-engineering departments (CS, MATH, ECON, etc.)"
                              >
                                <span className="font-medium">Other</span>
                                <span className="text-muted-foreground">
                                  {" "}
                                  All non-engineering
                                </span>
                              </Label>
                            </div>
                          </div>
                        </div>

                        {/* Options & Minors - search + tags */}
                        {optionsAndMinors && (
                          <div className="space-y-2">
                            <Label className="text-sm font-medium">
                              Options & Minors
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              Search and add options or minors to filter
                              courses.
                            </p>
                            <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                              <span className="flex items-center gap-1.5">
                                <span className="inline-flex items-center rounded border border-primary/20 bg-primary/5 px-1.5 py-0.5 text-[9px] font-medium text-primary">
                                  Opt
                                </span>
                                Option
                              </span>
                              <span className="flex items-center gap-1.5">
                                <span className="inline-flex items-center rounded border border-muted bg-muted/50 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                                  Min
                                </span>
                                Minor
                              </span>
                            </div>
                            <div className="relative">
                              <Input
                                type="text"
                                placeholder="Search options or minors..."
                                value={optionSearch}
                                onChange={(e) =>
                                  setOptionSearch(e.target.value)
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" && optionMatches[0]) {
                                    e.preventDefault();
                                    addOption(optionMatches[0].name);
                                    setOptionSearch("");
                                  }
                                }}
                                className="pr-3"
                              />
                              {optionSearch.trim() &&
                                optionMatches.length > 0 && (
                                  <div className="absolute z-10 mt-1 w-full rounded-md border border-input bg-popover py-1 shadow-md max-h-48 overflow-y-auto">
                                    {optionMatches.slice(0, 10).map((p) => (
                                      <button
                                        key={p.name}
                                        type="button"
                                        className="w-full px-3 py-2 text-left text-sm hover:bg-muted/50 flex items-center justify-between"
                                        onClick={() => {
                                          addOption(p.name);
                                          setOptionSearch("");
                                        }}
                                      >
                                        {p.name}
                                        <span className="text-[10px] text-muted-foreground uppercase">
                                          {p.type}
                                        </span>
                                      </button>
                                    ))}
                                    {optionMatches.length > 10 && (
                                      <div className="px-3 py-1 text-xs text-muted-foreground">
                                        +{optionMatches.length - 10} more — keep
                                        typing to narrow
                                      </div>
                                    )}
                                  </div>
                                )}
                            </div>
                            {selectedOptions.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {selectedOptions.map((name) => (
                                  <Badge
                                    key={name}
                                    variant="secondary"
                                    className="gap-1 pr-1 cursor-pointer hover:bg-destructive/20"
                                    onClick={() => removeOption(name)}
                                  >
                                    {name}
                                    <X className="w-3 h-3" />
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Completed Courses - compact with expand */}
                        <CompletedCoursesManager
                          completedCourses={completedCourses}
                          onAdd={(code) =>
                            setCompletedCourses((prev) =>
                              prev.includes(code) ? prev : [...prev, code],
                            )
                          }
                          onRemove={(code) =>
                            setCompletedCourses((prev) =>
                              prev.filter((c) => c !== code),
                            )
                          }
                          onClearAll={() => setCompletedCourses([])}
                          compact
                        />
                      </CardContent>
                    </Card>
                  )}
                </form>

                {/* Results */}
                <div className="space-y-4">
                  {loading ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                  ) : error ? (
                    <Card className="glass-card">
                      <CardContent className="py-8 text-center">
                        <p className="text-destructive">{error}</p>
                      </CardContent>
                    </Card>
                  ) : filteredCourses.length === 0 && hasSearched ? (
                    <Card className="glass-card">
                      <CardContent className="py-16 text-center space-y-4">
                        <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto">
                          <Search className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="font-medium">No courses found</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Try searching for topics like "machine learning" or
                            "data science"
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : filteredCourses.length === 0 &&
                    !hasSearched &&
                    showHighValueBlock ? (
                    <div className="space-y-4">
                      {highValueLoading ? (
                        <div className="flex justify-center py-12">
                          <Loader2 className="w-8 h-8 animate-spin text-primary" />
                        </div>
                      ) : highValueError ? (
                        <div className="text-center py-8 space-y-4">
                          <p className="text-sm text-muted-foreground">
                            Could not load suggestions. Please try again later
                            or try a search above.
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={fetchHighValueCourses}
                            className="gap-2"
                          >
                            <RefreshCw className="w-4 h-4" />
                            Retry
                          </Button>
                        </div>
                      ) : highValueCourses.length > 0 ? (
                        <div className="grid sm:grid-cols-2 gap-4">
                          {highValueCourses.map((course) => (
                            <CourseCard
                              key={course.code}
                              course={course}
                              onClick={() => setSelectedCourse(course)}
                              overrideRequired={needsOverride(course.prereqs, programCode)}
                            />
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-8">
                          Try searching for topics above.
                        </p>
                      )}
                    </div>
                  ) : filteredCourses.length === 0 && !hasSearched ? (
                    <Card className="glass-card">
                      <CardContent className="py-16 text-center space-y-4">
                        <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto">
                          <Search className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="font-medium">No courses yet</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Try searching for topics like "machine learning" or
                            "data science"
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid sm:grid-cols-2 gap-4">
                      {filteredCourses.map((course) => (
                        <CourseCard
                          key={course.code}
                          course={course}
                          onClick={() => setSelectedCourse(course)}
                          overrideRequired={needsOverride(course.prereqs, programCode)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Recommended Tab */}
              <TabsContent value="recommended" className="mt-6">
                {recommendedCourses && recommendedCourses.length > 0 ? (
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      Based on your resume, here are courses that match your
                      background:
                    </p>
                    <div className="grid sm:grid-cols-2 gap-4">
                      {recommendedCourses.map((course) => (
                        <CourseCard
                          key={course.code}
                          course={course}
                          onClick={() => setSelectedCourse(course)}
                          overrideRequired={needsOverride(course.prereqs, programCode)}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <Card className="glass-card">
                    <CardContent className="py-16 text-center space-y-6">
                      <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                        <FileText className="w-10 h-10 text-primary" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-xl font-semibold">
                          No Recommendations Yet
                        </h3>
                        <p className="text-muted-foreground max-w-sm mx-auto">
                          Upload your resume to get personalized course
                          recommendations based on your skills and experience.
                        </p>
                      </div>
                      <Button asChild className="gap-2">
                        <Link to="/profile">
                          <FileText className="w-4 h-4" />
                          Upload Resume
                        </Link>
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar - Random Course Generator */}
          <div className="lg:sticky-below-header space-y-4">
            <Card className="glass-card overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-accent/5" />
              <CardHeader className="relative">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Dice5 className="w-5 h-5 text-primary" />
                  </div>
                  <CardTitle className="text-lg">Random Course</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="relative space-y-4">
                <p className="text-sm text-muted-foreground">
                  Feeling adventurous? Discover a random course that might spark
                  your interest.
                </p>
                <Button
                  onClick={handleRandomCourse}
                  disabled={randomLoading}
                  className="w-full gap-2"
                  variant="secondary"
                >
                  {randomLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Dice5 className="w-4 h-4" />
                  )}
                  Generate Random Course
                </Button>

                {randomCourse && (
                  <Card
                    className="bg-background/50 cursor-pointer hover:bg-background/80 transition-colors"
                    onClick={() => setSelectedCourse(randomCourse)}
                  >
                    <CardContent className="p-4 space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{randomCourse.code}</Badge>
                        {needsOverride(randomCourse.prereqs, programCode) && (
                          <Badge className={OVERRIDE_BADGE_CLASS}>
                            Override required
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium text-sm">
                        {randomCourse.title}
                      </p>
                      {randomCourse.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {randomCourse.description}
                        </p>
                      )}
                      {randomCourse.contributing_programs &&
                        randomCourse.contributing_programs.length > 0 && (
                          <OptionBadges
                            programs={randomCourse.contributing_programs}
                          />
                        )}
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card className="glass-card">
              <CardContent className="p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 rounded-lg bg-background/50">
                    <GraduationCap className="w-5 h-5 text-primary mx-auto mb-1" />
                    <div className="text-lg font-bold">
                      {filteredCourses.length || recommendedCourses.length}
                    </div>
                    <div className="text-xs text-muted-foreground">Results</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-background/50">
                    <BookOpen className="w-5 h-5 text-accent mx-auto mb-1" />
                    <div className="text-lg font-bold">
                      {Object.values(departments).filter(Boolean).length +
                        (includeOtherDepts ? 1 : 0)}
                    </div>
                    <div className="text-xs text-muted-foreground">Depts</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Course Details Modal */}
      <Dialog
        open={!!selectedCourse}
        onOpenChange={() => setSelectedCourse(null)}
      >
        <DialogContent className="glass-card sm:max-w-3xl">
          <DialogHeader>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <Badge variant="default" className="text-sm">
                {selectedCourse?.code}
              </Badge>
              {needsOverride(selectedCourse?.prereqs, programCode) && (
                <Badge className={OVERRIDE_BADGE_CLASS}>
                  Override required
                </Badge>
              )}
              {selectedCourse?.contributing_programs &&
                selectedCourse.contributing_programs.length > 0 && (
                  <OptionBadges
                    programs={selectedCourse.contributing_programs}
                    className="flex-1"
                  />
                )}
            </div>
            <div className="flex items-center gap-3">
              <DialogTitle className="text-xl flex-1">
                {selectedCourse?.title}
              </DialogTitle>
              {selectedCourse && (
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="gap-1.5 shrink-0"
                >
                  <a
                    href={uwFlowUrl(selectedCourse.code)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    UW Flow
                  </a>
                </Button>
              )}
            </div>
          </DialogHeader>
          <div className="mt-4 grid gap-6 sm:grid-cols-[minmax(0,2fr),minmax(0,1.4fr)] items-start">
            <div className="rounded-lg border border-border bg-muted/20 p-4">
              {selectedCourse?.description ? (
                <DialogDescription className="text-foreground leading-relaxed">
                  {selectedCourse.description}
                </DialogDescription>
              ) : (
                <DialogDescription className="text-muted-foreground italic">
                  No description available for this course.
                </DialogDescription>
              )}
            </div>
            <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-4">
              <div>
                <h3 className="text-sm font-semibold">
                  {selectedCourse?.code} prerequisites
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {selectedCourse?.prereqs
                    ? selectedCourse.prereqs
                    : "No prerequisites"}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold">
                  {selectedCourse?.code} corequisites
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {selectedCourse?.coreqs
                    ? selectedCourse.coreqs
                    : "No corequisites"}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold">
                  {selectedCourse?.code} antirequisites
                </h3>
                <p className="mt-1 text-xs text-primary">
                  {selectedCourse?.antireqs
                    ? selectedCourse.antireqs
                    : "No antirequisites"}
                </p>
              </div>
            </div>
          </div>

          {/* Similar Courses */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              Similar Courses
            </h3>
            {similarLoading ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
                <Loader2 className="w-3 h-3 animate-spin" />
                Finding similar courses…
              </div>
            ) : similarCourses.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {similarCourses.map((c) => (
                  <button
                    key={c.code}
                    onClick={() => setSelectedCourse(c)}
                    className={cn(
                      "text-left rounded-lg border border-border bg-muted/20 p-3",
                      "hover:border-primary/40 hover:bg-primary/5 transition-all",
                      "group cursor-pointer",
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1">
                        <Badge
                          variant="outline"
                          className="text-[10px] bg-primary/10 text-primary border-primary/30"
                        >
                          {c.code}
                        </Badge>
                        {needsOverride(c.prereqs, programCode) && (
                          <Badge className={cn("text-[9px] px-1 py-0", OVERRIDE_BADGE_CLASS)}>
                            Override
                          </Badge>
                        )}
                      </div>
                      <ArrowRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-xs font-medium leading-tight line-clamp-2">
                      {c.title}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No similar courses found.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CourseCard({
  course,
  onClick,
  overrideRequired,
}: {
  course: Course;
  onClick: () => void;
  overrideRequired?: boolean;
}) {
  return (
    <Card
      className={cn(
        "glass-card cursor-pointer group transition-all duration-300",
        "hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5",
        "hover:-translate-y-0.5",
      )}
    >
      <CardContent className="p-4 space-y-3 h-full flex flex-col">
        <div className="flex items-start justify-between" onClick={onClick}>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className="bg-primary/10 text-primary border-primary/30"
            >
              {course.code}
            </Badge>
            {overrideRequired && (
              <Badge className={OVERRIDE_BADGE_CLASS}>
                Override required
              </Badge>
            )}
          </div>
          <BookOpen className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
        <div className="flex-1" onClick={onClick}>
          <h3 className="font-semibold text-sm leading-tight group-hover:text-primary transition-colors">
            {course.title}
          </h3>
          {course.description && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-2">
              {course.description}
            </p>
          )}
          {course.contributing_programs &&
            course.contributing_programs.length > 0 && (
              <div className="mt-2">
                <OptionBadges programs={course.contributing_programs} />
              </div>
            )}
        </div>
        <a
          href={uwFlowUrl(course.code)}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className={cn(
            "inline-flex items-center gap-1.5 text-xs font-medium",
            "text-muted-foreground hover:text-primary transition-colors",
            "mt-auto pt-1",
          )}
        >
          <ExternalLink className="w-3 h-3" />
          View on UW Flow
        </a>
      </CardContent>
    </Card>
  );
}
