import { useState, useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
import { cn } from "@/lib/utils";

export type Course = { code: string; title: string; description?: string };

export default function RecommendationPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [randomCourse, setRandomCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [filteredCourses, setFilteredCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [randomLoading, setRandomLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeUndergrad, setIncludeUndergrad] = useState(true);
  const [includeGrad, setIncludeGrad] = useState(true);
  const [departments, setDepartments] = useState<{ [key: string]: boolean }>({
    MSE: true,
    ECE: true,
  });
  const [showFilters, setShowFilters] = useState(false);

  const { recommendedCourses, completedCourses: contextCompletedCourses } =
    useContext(RecommendationsContext);

  // Local state for the text input
  const [completedCoursesInput, setCompletedCoursesInput] = useState("");

  // Track if we've synced from context (only sync once when transcript is uploaded)
  const [hasSyncedFromContext, setHasSyncedFromContext] = useState(false);

  // Update input when context changes from empty to non-empty (transcript upload)
  useEffect(() => {
    if (contextCompletedCourses.length > 0 && !hasSyncedFromContext) {
      setCompletedCoursesInput(contextCompletedCourses.join(", "));
      setHasSyncedFromContext(true);
    }
  }, [contextCompletedCourses, hasSyncedFromContext]);

  const departmentOptions = ["MSE", "ECE"];

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) {
      setFilteredCourses([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Use the input field as the source of truth for completed courses
      const completedCoursesList = completedCoursesInput
        ? completedCoursesInput
            .split(",")
            .map((c) => c.trim())
            .filter((c) => c)
        : [];

      const filters = {
        include_undergrad: includeUndergrad,
        include_grad: includeGrad,
        department: Object.keys(departments).filter((k) => departments[k]),
        completed_courses: completedCoursesList,
      };
      const requestBody = {
        queries: [search],
        filters,
      };

      const res = await fetch("http://localhost:8000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!res.ok) throw new Error("Failed to fetch recommendations");
      const data = await res.json();
      const results = data.results[search] || [];
      setFilteredCourses(
        results.map(
          (r: { course_code: string; title: string; description: string }) => ({
            code: r.course_code,
            title: r.title,
            description: r.description,
          })
        )
      );
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
      const res = await fetch("http://localhost:8000/random-course");
      if (!res.ok) throw new Error("Failed to fetch random course");
      const data = await res.json();
      setRandomCourse({
        code: data.course_code,
        title: data.title,
        description: data.description,
      });
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
    !departments.MSE,
    !departments.ECE,
    completedCoursesInput.length > 0,
  ].filter(Boolean).length;

  return (
    <div className="min-h-[calc(100vh-4rem)]">
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
                    </div>
                  </div>

                  {/* Filters Panel */}
                  {showFilters && (
                    <Card className="glass-card">
                      <CardContent className="pt-6 space-y-6">
                        {/* Level Filters */}
                        <div className="space-y-3">
                          <Label className="text-sm font-medium">
                            Course Level
                          </Label>
                          <div className="flex gap-6">
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id="undergrad"
                                checked={includeUndergrad}
                                onCheckedChange={(checked) =>
                                  setIncludeUndergrad(checked as boolean)
                                }
                              />
                              <Label
                                htmlFor="undergrad"
                                className="text-sm cursor-pointer"
                              >
                                Undergraduate
                              </Label>
                            </div>
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id="grad"
                                checked={includeGrad}
                                onCheckedChange={(checked) =>
                                  setIncludeGrad(checked as boolean)
                                }
                              />
                              <Label
                                htmlFor="grad"
                                className="text-sm cursor-pointer"
                              >
                                Graduate
                              </Label>
                            </div>
                          </div>
                        </div>

                        {/* Department Filters */}
                        <div className="space-y-3">
                          <Label className="text-sm font-medium">
                            Departments
                          </Label>
                          <div className="flex gap-6">
                            {departmentOptions.map((dept) => (
                              <div
                                key={dept}
                                className="flex items-center gap-2"
                              >
                                <Checkbox
                                  id={dept}
                                  checked={departments[dept]}
                                  onCheckedChange={(checked) =>
                                    setDepartments({
                                      ...departments,
                                      [dept]: checked as boolean,
                                    })
                                  }
                                />
                                <Label
                                  htmlFor={dept}
                                  className="text-sm cursor-pointer"
                                >
                                  {dept}
                                </Label>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Completed Courses */}
                        <div className="space-y-3">
                          <Label
                            htmlFor="completed"
                            className="text-sm font-medium"
                          >
                            Completed Courses (optional)
                          </Label>
                          <Input
                            id="completed"
                            type="text"
                            value={completedCoursesInput}
                            onChange={(e) =>
                              setCompletedCoursesInput(e.target.value)
                            }
                            placeholder="e.g., CS343, ECE124, MATH117"
                            className="bg-background"
                          />
                          <p className="text-xs text-muted-foreground">
                            Enter course codes separated by commas to exclude
                            them from recommendations
                          </p>
                        </div>
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
                      <Button onClick={() => navigate("/profile")} className="gap-2">
                        <FileText className="w-4 h-4" />
                        Upload Resume
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar - Random Course Generator */}
          <div className="lg:sticky lg:top-24 space-y-4">
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
                      <p className="font-medium text-sm">{randomCourse.title}</p>
                      {randomCourse.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {randomCourse.description}
                        </p>
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
        <DialogContent className="glass-card sm:max-w-lg">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <Badge variant="default" className="text-sm">
                {selectedCourse?.code}
              </Badge>
            </div>
            <DialogTitle className="text-xl">
              {selectedCourse?.title}
            </DialogTitle>
          </DialogHeader>
          <DialogDescription asChild>
            <div className="space-y-4">
              {selectedCourse?.description ? (
                <p className="text-foreground leading-relaxed">
                  {selectedCourse.description}
                </p>
              ) : (
                <p className="text-muted-foreground italic">
                  No description available for this course.
                </p>
              )}
            </div>
          </DialogDescription>
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
        "hover:-translate-y-0.5"
      )}
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <Badge
            variant="outline"
            className="bg-primary/10 text-primary border-primary/30"
          >
            {course.code}
          </Badge>
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
        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
        >
          View Details
        </Button>
      </CardContent>
    </Card>
  );
}
