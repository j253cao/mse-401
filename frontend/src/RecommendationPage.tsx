import { useState, useContext, useEffect } from "react";
import { Link } from "react-router-dom";
import { RecommendationsContext } from "./RecommendationsContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
} from "lucide-react";
import { api } from "@/services/api";
import type { Course } from "@/types/api";
import { CompletedCoursesManager } from "@/components/CompletedCoursesManager";
import { FILTER_DEPARTMENTS } from "@/constants/filterDepartments";
import { OptionBadges } from "@/components/OptionBadge";
import { cn } from "@/lib/utils";

type DepartmentFilters = Record<string, boolean>;

const INITIAL_DEPARTMENTS: DepartmentFilters = Object.fromEntries(
  FILTER_DEPARTMENTS.map((d) => [d.code, true]),
);

export default function RecommendationPage() {
  const [search, setSearch] = useState("");
  const [randomCourse, setRandomCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [filteredCourses, setFilteredCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [randomLoading, setRandomLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeUndergrad, setIncludeUndergrad] = useState(true);
  const [includeGrad, setIncludeGrad] = useState(true);
  const [explorationMode, setExplorationMode] = useState(false);
  const [departments, setDepartments] =
    useState<DepartmentFilters>(INITIAL_DEPARTMENTS);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [optionSearch, setOptionSearch] = useState("");
  const [optionsAndMinors, setOptionsAndMinors] = useState<{
    options: { name: string }[];
    minors: { name: string }[];
  } | null>(null);

  const { recommendedCourses, completedCourses, setCompletedCourses } =
    useContext(RecommendationsContext);

  useEffect(() => {
    if (showFilters && !optionsAndMinors) {
      api.getOptionsAndMinors().then(setOptionsAndMinors).catch(() => setOptionsAndMinors({ options: [], minors: [] }));
    }
  }, [showFilters, optionsAndMinors]);

  function addOption(name: string) {
    if (!name.trim() || selectedOptions.includes(name)) return;
    setSelectedOptions((prev) => [...prev, name]);
  }

  function removeOption(name: string) {
    setSelectedOptions((prev) => prev.filter((n) => n !== name));
  }

  const allPrograms = optionsAndMinors
    ? [
        ...optionsAndMinors.options.map((o) => ({ name: o.name, type: "option" as const })),
        ...optionsAndMinors.minors.map((m) => ({ name: m.name, type: "minor" as const })),
      ]
    : [];
  const optionSearchLower = optionSearch.trim().toLowerCase();
  const optionMatches = optionSearchLower
    ? allPrograms.filter(
        (p) =>
          p.name.toLowerCase().includes(optionSearchLower) &&
          !selectedOptions.includes(p.name)
      )
    : [];

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) {
      setFilteredCourses([]);
      return;
    }
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
        completed_courses: completedCourses,
        ignore_dependencies: explorationMode,
        ...(selectedOptions.length > 0 && { options: selectedOptions }),
      };

      const courses = await api.recommend([search], filters);
      setFilteredCourses(courses);
    } catch {
      setFilteredCourses([]);
      setError("Could not fetch recommendations.");
    } finally {
      setLoading(false);
    }
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
    !includeGrad,
    ...Object.values(departments).filter((v) => !v),
    completedCourses.length > 0,
    explorationMode,
    selectedOptions.length > 0,
  ].filter(Boolean).length;

  return (
    <div className="min-h-main">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-[1fr,320px] gap-8">
          {/* Main Content */}
          <div className="space-y-6">
            <Tabs defaultValue="search" className="w-full">
              <TabsList className="w-full sm:w-auto grid grid-cols-2 sm:inline-flex h-11 bg-card border border-border">
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
              </TabsList>

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
                  <div className="flex items-center gap-4">
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
                      {!includeGrad && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => setIncludeGrad(true)}
                        >
                          No Grad
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                      {Object.values(departments).filter(Boolean).length <
                        FILTER_DEPARTMENTS.length && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() =>
                            setDepartments(
                              Object.fromEntries(
                                FILTER_DEPARTMENTS.map((d) => [d.code, true]),
                              ),
                            )
                          }
                        >
                          {FILTER_DEPARTMENTS.length -
                            Object.values(departments).filter(Boolean)
                              .length}{" "}
                          depts excluded
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                      {selectedOptions.length > 0 && (
                        <Badge
                          variant="secondary"
                          className="gap-1 cursor-pointer hover:bg-destructive/20"
                          onClick={() => setSelectedOptions([])}
                        >
                          {selectedOptions.length} option
                          {selectedOptions.length !== 1 ? "s" : ""} selected
                          <X className="w-3 h-3" />
                        </Badge>
                      )}
                    </div>
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
                          </div>
                        </div>

                        {/* Options & Minors - search + tags */}
                        {optionsAndMinors && (
                          <div className="space-y-2">
                            <Label className="text-sm font-medium">
                              Options & Minors
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              Search and add options or minors to filter courses.
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
                              {optionSearch.trim() && optionMatches.length > 0 && (
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

                        {/* Exploration Mode */}
                        <div className="space-y-2">
                          <Label className="text-sm font-medium">
                            Exploration Mode
                          </Label>
                          <div className="flex items-center justify-between rounded-lg border border-input px-3 py-2 bg-muted/20">
                            <div className="space-y-0.5">
                              <p className="text-sm font-medium">
                                Ignore prerequisites
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Show courses even if pre-, co-, or
                                anti-requisites are not satisfied.
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id="exploration-mode"
                                checked={explorationMode}
                                onCheckedChange={(checked) =>
                                  setExplorationMode(!!checked)
                                }
                              />
                            </div>
                          </div>
                        </div>

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
                  ) : filteredCourses.length === 0 ? (
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
                  ) : (
                    <div className="grid sm:grid-cols-2 gap-4">
                      {filteredCourses.map((course) => (
                        <CourseCard
                          key={course.code}
                          course={course}
                          onClick={() => setSelectedCourse(course)}
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
                      {Object.values(departments).filter(Boolean).length}
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
              {selectedCourse?.contributing_programs &&
                selectedCourse.contributing_programs.length > 0 && (
                  <OptionBadges
                    programs={selectedCourse.contributing_programs}
                    className="flex-1"
                  />
                )}
            </div>
            <DialogTitle className="text-xl">
              {selectedCourse?.title}
            </DialogTitle>
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
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CourseCard({
  course,
  onClick,
}: {
  course: Course;
  onClick: () => void;
}) {
  return (
    <Card
      className={cn(
        "glass-card cursor-pointer group transition-all duration-300",
        "hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5",
        "hover:-translate-y-0.5",
      )}
    >
      <CardContent
        className="p-4 space-y-3 h-full flex flex-col"
        onClick={onClick}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className="bg-primary/10 text-primary border-primary/30"
            >
              {course.code}
            </Badge>
          </div>
          <BookOpen className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
        <h3 className="font-semibold text-sm leading-tight group-hover:text-primary transition-colors">
          {course.title}
        </h3>
        {course.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {course.description}
          </p>
        )}
        {course.contributing_programs &&
          course.contributing_programs.length > 0 && (
            <OptionBadges programs={course.contributing_programs} />
          )}
      </CardContent>
    </Card>
  );
}
