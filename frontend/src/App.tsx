import "./App.css";
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

function AppContent() {
  const location = useLocation();
  return (
    <div className="main-bg">
      <header className="header">
        <div className="header-left">
          <span className="logo-text">UW Guide</span>
        </div>
        <nav className="nav-bar">
          <Link
            className={"nav-btn" + (location.pathname === "/" ? " active" : "")}
            to="/"
          >
            Home
          </Link>
          <Link
            className={
              "nav-btn" +
              (location.pathname === "/recommendation" ? " active" : "")
            }
            to="/recommendation"
          >
            Course Recommendation
          </Link>
          <Link
            className={
              "nav-btn" + (location.pathname === "/calendar" ? " active" : "")
            }
            to="/calendar"
          >
            Calendar
          </Link>
        </nav>
        <div className="header-right">
          <Link to="/profile" className="profile-btn" aria-label="Profile">
            <svg
              width="28"
              height="28"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 8-4 8-4s8 0 8 4" />
            </svg>
          </Link>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/recommendation" element={<RecommendationPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
      <footer className="footer">
        <div>
          UW Guide &copy; {new Date().getFullYear()} | <a href="#">Contact</a> |{" "}
          <a href="#">GitHub</a> | <a href="#">Privacy Policy</a>
        </div>
      </footer>
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
