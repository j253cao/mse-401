import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const PLACEHOLDER_COURSES: Course[] = [
  { code: "MATH 135", title: "Algebra for Honours Mathematics" },
  { code: "CS 136", title: "Elementary Algorithm Design and Data Abstraction" },
  { code: "MSE 100", title: "Management Engineering Concepts" },
  { code: "PHYS 121", title: "Mechanics" },
  { code: "MSE 446", title: "Introduction to Machine Learning" },
  { code: "CS 240", title: "Introduction to Computer Systems" },
  { code: "CS 241", title: "Programming Languages and Paradigms" },
  { code: "CS 242", title: "Software Tools and Systems Programming" },
  { code: "CS 243", title: "Introduction to Computer Organization" },
  { code: "CS 244", title: "Introduction to Computer Networks" },
  { code: "CS 245", title: "Introduction to Computer Security" },
  { code: "CS 246", title: "Introduction to Computer Graphics" },
];

export type Course = { code: string; title: string };

export default function RecommendationPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [randomCourse, setRandomCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [mode, setMode] = useState<"search" | "recommended">("search");
  const [filteredCourses, setFilteredCourses] = useState(PLACEHOLDER_COURSES);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.trim()) {
      setFilteredCourses(PLACEHOLDER_COURSES);
      return;
    }
    setFilteredCourses(
      PLACEHOLDER_COURSES.filter(
        (c) =>
          c.code.toLowerCase().includes(search.toLowerCase()) ||
          c.title.toLowerCase().includes(search.toLowerCase())
      )
    );
  }

  function handleRandomCourse() {
    const course =
      PLACEHOLDER_COURSES[
        Math.floor(Math.random() * PLACEHOLDER_COURSES.length)
      ];
    setRandomCourse(course);
  }

  return (
    <>
      <div className={"split-layout" + (selectedCourse ? " blurred" : "")}>
        {/* BLUR WHEN MODAL OPEN */}
        {/* Left: Search, Filters, Results */}
        <div className="left-panel">
          {/* Toggle Buttons */}
          <div className="toggle-btn-group pill-toggle">
            <div
              className={
                "toggle-indicator" + (mode === "recommended" ? " right" : "")
              }
            ></div>
            <button
              className={"toggle-btn" + (mode === "search" ? " active" : "")}
              onClick={() => setMode("search")}
              type="button"
            >
              Search
            </button>
            <button
              className={
                "toggle-btn" + (mode === "recommended" ? " active" : "")
              }
              onClick={() => setMode("recommended")}
              type="button"
            >
              Recommended
            </button>
          </div>
          {/* Conditionally render left panel content */}
          {mode === "search" ? (
            <>
              {/* Search Bar */}
              <form
                className="search-bar-enhanced"
                onSubmit={handleSearchSubmit}
                autoComplete="off"
              >
                <svg
                  width="24"
                  height="24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  viewBox="0 0 24 24"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Describe the course you're looking for…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="search-input-enhanced"
                />
                <button
                  type="submit"
                  className="search-submit-btn"
                  aria-label="Search"
                >
                  <svg
                    width="20"
                    height="20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    viewBox="0 0 24 24"
                  >
                    <path d="M5 12h14" />
                    <path d="M12 5l7 7-7 7" />
                  </svg>
                </button>
              </form>
              {/* Filter Buttons */}
              <div className="filter-buttons">
                <button className="filter-btn">Filter 1</button>
                <button className="filter-btn">Filter 2</button>
                <button className="filter-btn">Filter 3</button>
              </div>
              {/* Course Results */}
              <div className="course-results-grid">
                {filteredCourses.length === 0 ? (
                  <div className="no-results">No courses found.</div>
                ) : (
                  filteredCourses.slice(0, 12).map((course) => (
                    <div className="course-card" key={course.code}>
                      <div className="course-code">{course.code}</div>
                      <div className="course-title">{course.title}</div>
                      <button
                        className="details-btn"
                        onClick={() => setSelectedCourse(course)}
                      >
                        Details
                      </button>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="recommended-panel">
              {/* Recommended Courses */}
              <div className="recommended-courses-title">
                Recommended Courses
              </div>
              <div className="empty-recommendation-state modern-empty-state center-empty-state">
                <div className="empty-state-card">
                  <div className="empty-state-icon">
                    <svg width="56" height="56" fill="none" viewBox="0 0 56 56">
                      <rect
                        x="8"
                        y="8"
                        width="40"
                        height="40"
                        rx="8"
                        fill="#f3f4f6"
                      />
                      <path
                        d="M20 28h16M20 34h10"
                        stroke="#646cff"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <rect
                        x="20"
                        y="18"
                        width="16"
                        height="4"
                        rx="2"
                        fill="#646cff"
                      />
                    </svg>
                  </div>
                  <div className="empty-state-texts">
                    <div
                      className="empty-state-title"
                      style={{
                        fontWeight: 700,
                        fontSize: "1.2em",
                        marginBottom: "0.3em",
                        color: "#222",
                      }}
                    >
                      No recommendations yet
                    </div>
                    <div
                      className="empty-state-desc"
                      style={{ color: "#666", marginBottom: "1em" }}
                    >
                      Add your resume to see personalized course
                      recommendations.
                    </div>
                    <button
                      className="resume-upload-btn"
                      style={{
                        background: "#646cff",
                        color: "white",
                        border: "none",
                        borderRadius: "6px",
                        padding: "0.6em 1.4em",
                        fontWeight: 600,
                        fontSize: "1em",
                        cursor: "pointer",
                        boxShadow: "0 2px 8px rgba(100,108,255,0.08)",
                      }}
                      onClick={() => navigate("/profile")}
                    >
                      Upload Resume
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        {/* Right: Random Course Generator */}
        <div className="right-panel stretch-column">
          <div className="random-generator-column">
            <div className="icon-container">
              <svg
                width="24"
                height="24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                viewBox="0 0 24 24"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <circle cx="15.5" cy="8.5" r="1.5" />
                <circle cx="8.5" cy="15.5" r="1.5" />
                <circle cx="15.5" cy="15.5" r="1.5" />
              </svg>
            </div>
            <h2>Random Course Generator</h2>
            <button className="random-btn" onClick={handleRandomCourse}>
              Generate Random Course
            </button>
            {randomCourse && (
              <div className="random-course-result">
                <h3>{randomCourse.code}</h3>
                <p>{randomCourse.title}</p>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Course Details Modal */}
      {selectedCourse && (
        <div className="modal-overlay" onClick={() => setSelectedCourse(null)}>
          <div
            className="modal details-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close-btn"
              onClick={() => setSelectedCourse(null)}
              aria-label="Close"
            >
              &times;
            </button>
            <h3
              style={{
                fontWeight: 700,
                color: "#646cff",
                fontSize: "1.3em",
                marginBottom: "0.5em",
                textAlign: "center",
              }}
            >
              {selectedCourse.code}: {selectedCourse.title}
            </h3>
            <p>Course details go here. (Add real details as needed.)</p>
          </div>
        </div>
      )}
    </>
  );
}
