import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ArrowRight,
  BookOpen,
  Brain,
  FileText,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";

export default function HomePage() {
  const features = [
    {
      icon: Brain,
      title: "AI-Powered Recommendations",
      description:
        "Get personalized course suggestions based on your skills and interests",
    },
    {
      icon: FileText,
      title: "Transcript Analysis",
      description:
        "Upload your transcript to discover courses that align with your experience",
    },
    {
      icon: Target,
      title: "Smart Filtering",
      description:
        "Filter by department, level, and completed courses to find the perfect fit",
    },
  ];

  return (
    <div className="min-h-main">
      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card text-sm text-muted-foreground">
                <Sparkles className="w-4 h-4 text-primary" />
                <span>Powered by AI recommendations</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
                Find Your Perfect
                <span className="block gradient-text mt-2">Course Match</span>
              </h1>

              <p className="text-lg text-muted-foreground max-w-lg">
                Discover courses tailored to your academic journey. Our AI
                analyzes your background and interests to recommend the courses
                that will help you succeed.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <Button
                  asChild
                  size="lg"
                  className="w-full sm:w-auto gap-2 group"
                >
                  <Link to="/recommendation">
                    Explore Courses
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  size="lg"
                  className="w-full sm:w-auto gap-2"
                >
                  <Link to="/profile">
                    <FileText className="w-4 h-4" />
                    Upload Transcript
                  </Link>
                </Button>
              </div>

              {/* Stats */}
              <div className="flex gap-8 pt-4">
                <div>
                  <div className="text-3xl font-bold gradient-text">500+</div>
                  <div className="text-sm text-muted-foreground">
                    Courses Available
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-bold gradient-text">AI</div>
                  <div className="text-sm text-muted-foreground">
                    Powered Search
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-bold gradient-text">24/7</div>
                  <div className="text-sm text-muted-foreground">
                    Always Available
                  </div>
                </div>
              </div>
            </div>

            {/* Right Content - Hero Illustration */}
            <div className="relative hidden lg:block">
              <div className="relative w-full aspect-square max-w-lg mx-auto">
                {/* Background glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 rounded-full blur-3xl animate-glow" />

                {/* Floating cards */}
                <div className="absolute top-8 left-8 animate-float">
                  <Card className="glass-card p-4 shadow-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                        <BookOpen className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <div className="font-semibold text-sm">MSE 343</div>
                        <div className="text-xs text-muted-foreground">
                          Human-Computer Interaction
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>

                <div
                  className="absolute top-1/4 right-4 animate-float"
                  style={{ animationDelay: "1s" }}
                >
                  <Card className="glass-card p-4 shadow-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                        <Zap className="w-5 h-5 text-accent" />
                      </div>
                      <div>
                        <div className="font-semibold text-sm">SYDE 577</div>
                        <div className="text-xs text-muted-foreground">
                          Deep Learning
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>

                <div
                  className="absolute bottom-1/4 left-4 animate-float"
                  style={{ animationDelay: "2s" }}
                >
                  <Card className="glass-card p-4 shadow-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                        <Target className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <div className="font-semibold text-sm">MSE 211</div>
                        <div className="text-xs text-muted-foreground">
                          Org. Behaviour
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Center orb */}
                <div className="absolute inset-1/4 rounded-full glass-card flex items-center justify-center">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center animate-glow">
                    <Brain className="w-12 h-12 text-primary-foreground" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-t border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl font-bold">
              Everything You Need to{" "}
              <span className="gradient-text">Plan Your Courses</span>
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our platform combines powerful AI with a seamless user experience
              to help you make informed decisions about your academic path.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="glass-card group hover:border-primary/30 transition-all duration-300"
              >
                <CardContent className="pt-6 space-y-4">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <feature.icon className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card className="glass-card overflow-hidden">
            <div className="relative p-8 sm:p-12 lg:p-16">
              {/* Background decoration */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent/10 rounded-full blur-3xl" />

              <div className="relative z-10 text-center space-y-6">
                <h2 className="text-3xl sm:text-4xl font-bold">
                  Ready to Find Your{" "}
                  <span className="gradient-text">Next Course?</span>
                </h2>
                <p className="text-muted-foreground max-w-xl mx-auto">
                  Start exploring personalized course recommendations today and
                  take your academic journey to the next level.
                </p>
                <Button asChild size="lg" className="gap-2 group">
                  <Link to="/recommendation">
                    Get Started
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
