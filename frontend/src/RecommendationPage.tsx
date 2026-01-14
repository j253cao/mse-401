import React, { useState, useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { RecommendationsContext } from "./RecommendationsContext";
import Select from "react-select";

export type Course = { code: string; title: string; description?: string };

export default function RecommendationPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [randomCourse, setRandomCourse] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [mode, setMode] = useState<"search" | "recommended">("search");
  const [filteredCourses, setFilteredCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeUndergrad, setIncludeUndergrad] = useState(true);
  const [includeGrad, setIncludeGrad] = useState(true);
  const [departments, setDepartments] = useState<{ [key: string]: boolean }>({
    MSE: true,
    ECE: true,
  });
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

  const departmentOptions = [
    { value: "MSE", label: "MSE" },
    { value: "ECE", label: "ECE" },
  ];

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
    setLoading(true);
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
      setLoading(false);
    }
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
              {/* Filter UI */}
              <div className="filter-section" style={{ margin: "1em 0" }}>
                <div
                  style={{
                    display: "flex",
                    gap: "1em",
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      fontSize: "1em",
                      fontWeight: "500",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={includeUndergrad}
                      onChange={() => setIncludeUndergrad((v) => !v)}
                      style={{ marginRight: "0.5em" }}
                    />
                    Undergrad
                  </label>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      fontSize: "1em",
                      fontWeight: "500",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={includeGrad}
                      onChange={() => setIncludeGrad((v) => !v)}
                      style={{ marginRight: "0.5em" }}
                    />
                    Grad
                  </label>
                  <label
                    style={{
                      marginLeft: "1em",
                      fontSize: "1em",
                      fontWeight: "500",
                      color: "#333",
                    }}
                  >
                    Department:
                  </label>
                  <div style={{ minWidth: 180, width: 180 }}>
                    <Select
                      isMulti
                      options={departmentOptions}
                      value={departmentOptions.filter(
                        (opt) => departments[opt.value]
                      )}
                      onChange={(selected) => {
                        const selectedValues = Array.isArray(selected)
                          ? selected.map((opt) => opt.value)
                          : [];
                        setDepartments({
                          MSE: selectedValues.includes("MSE"),
                          ECE: selectedValues.includes("ECE"),
                        });
                      }}
                      closeMenuOnSelect={false}
                      placeholder="Select departments..."
                      styles={{
                        control: (base) => ({
                          ...base,
                          minHeight: 36,
                          fontSize: "1em",
                        }),
                        multiValue: (base) => ({
                          ...base,
                          background: "#646cff22",
                        }),
                        option: (base, state) => ({
                          ...base,
                          color: "#222",
                          background: state.isSelected ? "#646cff22" : "#fff",
                        }),
                      }}
                    />
                  </div>
                </div>

                {/* Completed Courses Input */}
                <div style={{ marginTop: "1em" }}>
                  <label
                    style={{
                      display: "block",
                      marginBottom: "0.5em",
                      fontWeight: "500",
                      fontSize: "1em",
                      color: "#333",
                    }}
                  >
                    Completed Courses (optional):
                  </label>
                  <input
                    type="text"
                    value={completedCoursesInput}
                    onChange={(e) => setCompletedCoursesInput(e.target.value)}
                    placeholder="e.g., CS343, ECE124, MATH117"
                    style={{
                      width: "100%",
                      padding: "0.5em",
                      border: "1px solid #ccc",
                      borderRadius: "4px",
                      fontSize: "1em",
                    }}
                  />
                  <div
                    style={{
                      fontSize: "0.85em",
                      color: "#666",
                      marginTop: "0.4em",
                      lineHeight: "1.3",
                    }}
                  >
                    Enter course codes separated by commas to exclude them from
                    recommendations
                  </div>
                </div>
              </div>
              {/* Filter Buttons */}
              {/* <div className="filter-buttons">
                <button className="filter-btn">Filter 1</button>
                <button className="filter-btn">Filter 2</button>
                <button className="filter-btn">Filter 3</button>
              </div> */}
              {/* Course Results */}
              <div className="course-results-grid">
                {loading ? (
                  <div className="no-results">Loading...</div>
                ) : error ? (
                  <div className="no-results">{error}</div>
                ) : filteredCourses.length === 0 ? (
                  <div className="no-results">No courses found.</div>
                ) : (
                  filteredCourses.map((course: Course) => (
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
              {recommendedCourses && recommendedCourses.length > 0 ? (
                <div className="course-results-grid">
                  {recommendedCourses.map((course: Course) => (
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
                  ))}
                </div>
              ) : (
                <div className="empty-recommendation-state modern-empty-state center-empty-state">
                  <div className="empty-state-card">
                    <div className="empty-state-icon">
                      <svg
                        width="56"
                        height="56"
                        fill="none"
                        viewBox="0 0 56 56"
                      >
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
              )}
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
            <button
              className="random-btn"
              onClick={handleRandomCourse}
              disabled={loading}
            >
              Generate Random Course
            </button>
            {randomCourse && (
              <div className="random-course-result">
                <h3>{randomCourse.code}</h3>
                <p>{randomCourse.title}</p>
                {randomCourse.description && <p>{randomCourse.description}</p>}
              </div>
            )}
            {error && <div className="no-results">{error}</div>}
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
            {selectedCourse.description ? (
              <div className="details-modal-description">
                {selectedCourse.description}
              </div>
            ) : (
              <div
                className="details-modal-description"
                style={{ color: "#888" }}
              >
                No description available.
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
