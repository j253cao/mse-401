import { useState, useContext, useCallback } from "react";
import { RecommendationsContext } from "./RecommendationsContext";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  FileText,
  User,
  GraduationCap,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Settings2,
  Trash2,
} from "lucide-react";
import { ProgramSelector } from "@/components/ProgramSelector";
import { AcademicTermSelector } from "@/components/AcademicTermSelector";
import { CompletedCoursesManager } from "@/components/CompletedCoursesManager";
import { ENGINEERING_PROGRAMS } from "@/constants/engineeringPrograms";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/services/api";

export default function ProfilePage() {
  const {
    setRecommendedCourses,
    setCompletedCourses,
    setStudentProfile,
    setTermSummaries,
    studentProfile,
    completedCourses,
    programCode,
    setProgramCode,
    incomingLevel,
    setIncomingLevel,
    clearProfile,
  } = useContext(RecommendationsContext);

  const [loading, setLoading] = useState(false);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showTranscriptConfirmation, setShowTranscriptConfirmation] =
    useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [transcriptDragActive, setTranscriptDragActive] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedTranscriptName, setUploadedTranscriptName] = useState<
    string | null
  >(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const navigate = useNavigate();

  function handleClearProfile() {
    clearProfile();
    setUploadedFileName(null);
    setUploadedTranscriptName(null);
    setShowClearConfirm(false);
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleTranscriptDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setTranscriptDragActive(true);
    } else if (e.type === "dragleave") {
      setTranscriptDragActive(false);
    }
  }, []);

  async function handleResumeUpload(file: File) {
    setLoading(true);
    setError(null);
    setUploadedFileName(file.name);
    try {
      const courses = await api.uploadResume(file);
      setRecommendedCourses(courses);
      setShowConfirmation(true);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not get recommendations. Please try again.";
      setError(message);
      setUploadedFileName(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleTranscriptUpload(file: File) {
    setTranscriptLoading(true);
    setTranscriptError(null);
    setUploadedTranscriptName(file.name);
    try {
      const data = await api.parseTranscript(file);

      // Merge completed courses (dedupe) instead of replacing
      setCompletedCourses((prev) => {
        const merged = new Set([...prev, ...(data.courses || [])]);
        return [...merged];
      });

      // Update term summaries
      setTermSummaries(data.term_summaries || []);

      // Update student profile
      setStudentProfile({
        program: data.program,
        studentNumber: data.student_number,
        latestTerm: data.latest_term,
      });

      setShowTranscriptConfirmation(true);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not parse transcript.";
      setTranscriptError(message);
      setUploadedTranscriptName(null);
    } finally {
      setTranscriptLoading(false);
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleResumeUpload(e.dataTransfer.files[0]);
    }
  };

  const handleTranscriptDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setTranscriptDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleTranscriptUpload(e.dataTransfer.files[0]);
    }
  };

  const programDisplayName = programCode
    ? (ENGINEERING_PROGRAMS.find((p) => p.code === programCode)?.displayName ??
      programCode)
    : "—";
  const displayProgram = studentProfile?.program || programDisplayName;
  const displayLevel =
    studentProfile?.latestTerm?.level || incomingLevel || "—";

  const profileInfo = studentProfile
    ? [
        {
          icon: User,
          label: "Student ID",
          value: studentProfile.studentNumber?.toString() || "—",
        },
        {
          icon: GraduationCap,
          label: "Program",
          value: studentProfile.program || "—",
        },
        {
          icon: FileText,
          label: "Level",
          value: studentProfile.latestTerm?.level || "—",
        },
      ]
    : [
        { icon: User, label: "Student ID", value: "Upload transcript" },
        { icon: GraduationCap, label: "Program", value: displayProgram },
        { icon: FileText, label: "Level", value: displayLevel },
      ];

  return (
    <div className="min-h-main">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Your Profile</h1>
            <p className="text-muted-foreground mt-1">
              Upload your documents to get personalized recommendations
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-muted-foreground hover:text-destructive hover:border-destructive/50 self-start sm:self-auto"
            onClick={() => setShowClearConfirm(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear profile data
          </Button>
        </div>

        {/* Clear confirmation dialog */}
        <Dialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Clear profile data?</DialogTitle>
              <DialogDescription>
                This will remove your program, course level, completed courses,
                resume recommendations, and transcript data. This cannot be
                undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                variant="outline"
                onClick={() => setShowClearConfirm(false)}
              >
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleClearProfile}>
                Clear all
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="grid md:grid-cols-[1fr,320px] gap-8">
          {/* Left Column - Upload Section */}
          <div className="space-y-6">
            {/* Manual Setup */}
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="w-5 h-5 text-primary" />
                  Set up your profile
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Select your program and incoming term to auto-populate
                  required courses
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProgramSelector
                  value={programCode}
                  onChange={setProgramCode}
                />
                <AcademicTermSelector
                  value={incomingLevel}
                  onChange={setIncomingLevel}
                />
                {programCode && incomingLevel && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/5">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <p className="text-sm text-muted-foreground">
                      Required core courses for terms before {incomingLevel}{" "}
                      have been loaded
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Resume Upload
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" />
                  Resume Upload
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div
                  className={cn(
                    "relative border-2 border-dashed rounded-xl p-8 transition-all duration-200 text-center",
                    dragActive
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50 hover:bg-card/50",
                    loading && "pointer-events-none opacity-50"
                  )}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleResumeUpload(e.target.files[0]);
                      }
                    }}
                  />
                  <div className="space-y-4">
                    <div
                      className={cn(
                        "w-16 h-16 rounded-full mx-auto flex items-center justify-center transition-colors",
                        dragActive ? "bg-primary/20" : "bg-muted"
                      )}
                    >
                      {loading ? (
                        <Loader2 className="w-8 h-8 text-primary animate-spin" />
                      ) : uploadedFileName ? (
                        <CheckCircle2 className="w-8 h-8 text-green-500" />
                      ) : (
                        <Upload className="w-8 h-8 text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      {loading ? (
                        <p className="font-medium">Analyzing your resume...</p>
                      ) : uploadedFileName ? (
                        <>
                          <p className="font-medium text-green-500">
                            Upload successful!
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            {uploadedFileName}
                          </p>
                        </>
                      ) : (
                        <>
                          <p className="font-medium">
                            Drop your resume here or click to browse
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Supports PDF, DOC, DOCX
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {error && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p className="text-sm">{error}</p>
                  </div>
                )}

                <div className="flex items-start gap-2 p-3 rounded-lg bg-primary/5">
                  <Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-muted-foreground">
                    Our AI analyzes your resume to find courses that match your
                    skills and experience.
                  </p>
                </div>
              </CardContent>
            </Card> */}

            {/* Transcript Upload */}
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-accent" />
                  Transcript Upload
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div
                  className={cn(
                    "relative border-2 border-dashed rounded-xl p-8 transition-all duration-200 text-center",
                    transcriptDragActive
                      ? "border-accent bg-accent/5"
                      : "border-border hover:border-accent/50 hover:bg-card/50",
                    transcriptLoading && "pointer-events-none opacity-50",
                  )}
                  onDragEnter={handleTranscriptDrag}
                  onDragLeave={handleTranscriptDrag}
                  onDragOver={handleTranscriptDrag}
                  onDrop={handleTranscriptDrop}
                >
                  <input
                    type="file"
                    accept=".pdf"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleTranscriptUpload(e.target.files[0]);
                      }
                    }}
                  />
                  <div className="space-y-4">
                    <div
                      className={cn(
                        "w-16 h-16 rounded-full mx-auto flex items-center justify-center transition-colors",
                        transcriptDragActive ? "bg-accent/20" : "bg-muted",
                      )}
                    >
                      {transcriptLoading ? (
                        <Loader2 className="w-8 h-8 text-accent animate-spin" />
                      ) : uploadedTranscriptName ? (
                        <CheckCircle2 className="w-8 h-8 text-green-500" />
                      ) : (
                        <Upload className="w-8 h-8 text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      {transcriptLoading ? (
                        <p className="font-medium">
                          Parsing your transcript...
                        </p>
                      ) : uploadedTranscriptName ? (
                        <>
                          <p className="font-medium text-green-500">
                            Transcript parsed!
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            {uploadedTranscriptName}
                          </p>
                        </>
                      ) : (
                        <>
                          <p className="font-medium">
                            Drop your transcript here or click to browse
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Supports PDF
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {transcriptError && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p className="text-sm">{transcriptError}</p>
                  </div>
                )}

                {completedCourses.length > 0 && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 text-green-500">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    <p className="text-sm">
                      {completedCourses.length} courses loaded from transcript
                    </p>
                  </div>
                )}

                <div className="flex items-start gap-2 p-3 rounded-lg bg-accent/5">
                  <GraduationCap className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-muted-foreground">
                    Upload your transcript to track completed courses and get
                    better recommendations.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Completed Courses Manager */}
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-accent" />
                  Completed Courses
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Add or remove courses. Only known courses can be added. Used
                  to filter recommendations.
                </p>
              </CardHeader>
              <CardContent>
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
                />
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Profile Card */}
          <div>
            <Card className="glass-card sticky-below-header">
              <CardContent className="pt-6">
                {/* Avatar */}
                <div className="flex flex-col items-center space-y-4 mb-6">
                  <div className="relative">
                    <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-accent p-0.5">
                      <div className="w-full h-full rounded-full bg-card flex items-center justify-center">
                        <User className="w-12 h-12 text-primary" />
                      </div>
                    </div>
                    {studentProfile && (
                      <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-green-500 border-4 border-card flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-white" />
                      </div>
                    )}
                  </div>
                  <div className="text-center">
                    <h3 className="font-semibold text-lg">
                      {studentProfile
                        ? `Student #${studentProfile.studentNumber}`
                        : "Student Profile"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {studentProfile?.program ||
                        displayProgram ||
                        "Upload transcript or set up above"}
                    </p>
                  </div>
                </div>

                {/* Profile Info */}
                <div className="space-y-3">
                  {profileInfo.map(({ icon: Icon, label, value }) => (
                    <div
                      key={label}
                      className="flex items-center gap-3 p-3 rounded-lg bg-background/50"
                    >
                      <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center">
                        <Icon className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className="text-sm font-medium truncate">{value}</p>
                      </div>
                    </div>
                  ))}
                  {/* Courses Completed */}
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-background/50">
                    <div className="w-8 h-8 rounded-md bg-accent/10 flex items-center justify-center">
                      <Badge variant="secondary" className="text-xs px-1.5">
                        {completedCourses.length}
                      </Badge>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-muted-foreground">
                        Courses Completed
                      </p>
                      <p className="text-sm font-medium truncate">
                        {completedCourses.length > 0
                          ? `${completedCourses.length} courses`
                          : "None loaded"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Edit Button */}
                <Button variant="outline" className="w-full mt-6" disabled>
                  Edit Profile (Coming Soon)
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Resume Success Modal */}
      <Dialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <DialogContent className="glass-card sm:max-w-md">
          <DialogHeader className="text-center sm:text-center">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>
            <DialogTitle>Resume Uploaded Successfully!</DialogTitle>
            <DialogDescription>
              We've analyzed your resume and generated personalized course
              recommendations for you.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowConfirmation(false)}
              className="w-full sm:w-auto"
            >
              Stay Here
            </Button>
            <Button
              onClick={() => {
                setShowConfirmation(false);
                navigate("/recommendation");
              }}
              className="w-full sm:w-auto gap-2"
            >
              <Sparkles className="w-4 h-4" />
              View Recommendations
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Transcript Success Modal */}
      <Dialog
        open={showTranscriptConfirmation}
        onOpenChange={setShowTranscriptConfirmation}
      >
        <DialogContent className="glass-card sm:max-w-md">
          <DialogHeader className="text-center sm:text-center">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>
            <DialogTitle>Transcript Parsed Successfully!</DialogTitle>
            <DialogDescription>
              <strong>{completedCourses.length}</strong> courses loaded from
              your transcript.
            </DialogDescription>
            {studentProfile && (
              <p className="text-sm text-muted-foreground text-center sm:text-left">
                {studentProfile.program} • Level{" "}
                {studentProfile.latestTerm?.level}
              </p>
            )}
          </DialogHeader>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowTranscriptConfirmation(false)}
              className="w-full sm:w-auto"
            >
              Stay Here
            </Button>
            <Button
              onClick={() => {
                setShowTranscriptConfirmation(false);
                navigate("/recommendation");
              }}
              className="w-full sm:w-auto gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Get Recommendations
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
