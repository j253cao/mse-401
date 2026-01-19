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
  Mail,
  GraduationCap,
  Calendar,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function ProfilePage() {
  const { setRecommendedCourses } = useContext(RecommendationsContext) as {
    setRecommendedCourses: React.Dispatch<
      React.SetStateAction<
        { code: string; title: string; description?: string }[]
      >
    >;
  };
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  async function handleResumeUpload(file: File) {
    setLoading(true);
    setError(null);
    setUploadedFileName(file.name);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("http://localhost:8000/resume-recommend", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to get recommendations");
      const data = await res.json();
      setRecommendedCourses(
        data.map(
          (r: { course_code: string; title: string; description: string }) => ({
            code: r.course_code,
            title: r.title,
            description: r.description,
          })
        )
      );
      setShowConfirmation(true);
    } catch {
      setError("Could not get recommendations. Please try again.");
      setUploadedFileName(null);
    } finally {
      setLoading(false);
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleResumeUpload(e.dataTransfer.files[0]);
    }
  }, []);

  const profileInfo = [
    { icon: User, label: "Name", value: "John Doe" },
    { icon: Mail, label: "Email", value: "johndoe@email.com" },
    { icon: GraduationCap, label: "Program", value: "Management Engineering" },
    { icon: Calendar, label: "Year", value: "3" },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Your Profile</h1>
          <p className="text-muted-foreground mt-1">
            Upload your documents to get personalized recommendations
          </p>
        </div>

        <div className="grid md:grid-cols-[1fr,320px] gap-8">
          {/* Left Column - Upload Section */}
          <div className="space-y-6">
            {/* Resume Upload */}
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
            </Card>

            {/* Transcript Upload */}
            <Card className="glass-card overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-accent" />
                  Transcript Upload
                  <Badge variant="secondary" className="ml-2">
                    Coming Soon
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative border-2 border-dashed border-border/50 rounded-xl p-8 text-center opacity-60">
                  <div className="space-y-4">
                    <div className="w-16 h-16 rounded-full bg-muted/50 mx-auto flex items-center justify-center">
                      <Upload className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium text-muted-foreground">
                        Transcript upload coming soon
                      </p>
                      <p className="text-sm text-muted-foreground/70 mt-1">
                        Track your completed courses automatically
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Profile Card */}
          <div>
            <Card className="glass-card sticky top-24">
              <CardContent className="pt-6">
                {/* Avatar */}
                <div className="flex flex-col items-center space-y-4 mb-6">
                  <div className="relative">
                    <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-accent p-0.5">
                      <div className="w-full h-full rounded-full bg-card flex items-center justify-center">
                        <User className="w-12 h-12 text-primary" />
                      </div>
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-green-500 border-4 border-card flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <div className="text-center">
                    <h3 className="font-semibold text-lg">John Doe</h3>
                    <p className="text-sm text-muted-foreground">
                      Management Engineering
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

      {/* Success Modal */}
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
    </div>
  );
}
