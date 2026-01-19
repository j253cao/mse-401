import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useLocation,
} from "react-router-dom";
import HomePage from "./HomePage";
import CalendarPage from "./CalendarPage";
import RecommendationPage from "./RecommendationPage";
import ProfilePage from "./ProfilePage";
import { cn } from "@/lib/utils";
import { GraduationCap, Home, Search, User } from "lucide-react";

function AppContent() {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Home", icon: Home },
    { path: "/recommendation", label: "Courses", icon: Search },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
                  <GraduationCap className="w-5 h-5 text-primary-foreground" />
                </div>
                <div className="absolute -inset-1 bg-gradient-to-br from-primary/30 to-accent/30 rounded-xl blur opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className="text-xl font-bold tracking-tight">
                <span className="gradient-text">UW</span>
                <span className="text-foreground"> Guide</span>
              </span>
            </Link>

            {/* Navigation */}
            <nav className="hidden sm:flex items-center gap-1">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                    location.pathname === path
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}
            </nav>

            {/* Profile Button */}
            <Link
              to="/profile"
              className={cn(
                "flex items-center justify-center w-10 h-10 rounded-full transition-all",
                location.pathname === "/profile"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <User className="w-5 h-5" />
            </Link>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="sm:hidden border-t border-border/50">
          <div className="flex justify-center gap-2 p-2">
            {navItems.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                  location.pathname === path
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative">
        {/* Background decoration */}
        <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
        </div>

        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/recommendation" element={<RecommendationPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}
