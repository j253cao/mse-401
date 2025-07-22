import { Link } from "react-router-dom";

export default function HomePage() {
  return (
    <div className="home-placeholder">
      <h1>Welcome to UW Guide!</h1>
      <p>Your one-stop shop for course recommendations.</p>
      <Link to="/recommendation" className="cta-btn">
        See My Courses Now →
      </Link>
    </div>
  );
}
