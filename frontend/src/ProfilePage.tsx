import React, { useState, useContext } from "react";
import { RecommendationsContext } from "./RecommendationsContext";
import { useNavigate } from "react-router-dom";

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
  const navigate = useNavigate();

  async function handleResumeUpload(file: File) {
    setLoading(true);
    setError(null);
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
      setError("Could not get recommendations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="profile-split-layout">
      {/* Left: Resume and Transcript Inputs */}
      <div className="profile-left-panel">
        <div style={{ width: "100%" }}>
          <div className="profile-upload-heading">Upload your resume</div>
          <div
            className="resume-dropbox"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleResumeUpload(e.dataTransfer.files[0]);
              }
            }}
          >
            <span>Drop your resume here or click to upload</span>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              className="resume-file-input"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleResumeUpload(e.target.files[0]);
                }
              }}
            />
          </div>
          {loading && <div>Uploading and analyzing resume...</div>}
          {error && <div style={{ color: "red" }}>{error}</div>}
        </div>
        <div style={{ width: "100%", marginTop: "1.5rem" }}>
          <div className="profile-upload-heading">Upload your transcript</div>
          <div
            className="resume-dropbox transcript-dropbox"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              alert(
                "Transcript uploaded: " +
                  (e.dataTransfer.files[0]?.name || "No file")
              );
            }}
          >
            <span>Drop your transcript here or click to upload</span>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              className="resume-file-input"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  alert("Transcript uploaded: " + e.target.files[0].name);
                }
              }}
            />
          </div>
        </div>
      </div>
      {/* Right: Profile Picture (Avatar) and General Info */}
      <div className="profile-right-panel profile-avatar-panel">
        <div className="profile-avatar-container">
          <svg
            width="96"
            height="96"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            viewBox="0 0 24 24"
            className="profile-avatar-svg"
          >
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4 8-4 8-4s8 0 8 4" />
          </svg>
        </div>
        <ul className="profile-info-list">
          <li>
            <strong>Name:</strong> John Doe
          </li>
          <li>
            <strong>Email:</strong> johndoe@email.com
          </li>
          <li>
            <strong>Program:</strong> Management Engineering
          </li>
          <li>
            <strong>Year:</strong> 3
          </li>
          {/* Add more info as needed */}
        </ul>
      </div>
      {/* Confirmation Modal */}
      {showConfirmation && (
        <div
          className="modal-overlay"
          onClick={() => setShowConfirmation(false)}
        >
          <div
            className="modal resume-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close-btn"
              onClick={() => setShowConfirmation(false)}
              aria-label="Close"
            >
              &times;
            </button>
            <h3
              style={{
                fontWeight: 700,
                color: "#646cff",
                fontSize: "1.2em",
                marginBottom: "0.5em",
                textAlign: "center",
              }}
            >
              Resume uploaded!
            </h3>
            <p style={{ textAlign: "center", marginBottom: "1em" }}>
              Recommendations are now available in the <b>Recommended</b> tab.
            </p>
            <div
              style={{ display: "flex", justifyContent: "center", gap: "1em" }}
            >
              <button
                style={{
                  background: "#646cff",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0.6em 1.4em",
                  fontWeight: 600,
                  fontSize: "1em",
                  cursor: "pointer",
                }}
                onClick={() => {
                  setShowConfirmation(false);
                  navigate("/recommendations");
                }}
              >
                Go to Recommendations
              </button>
              <button
                style={{
                  background: "#eee",
                  color: "#333",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0.6em 1.4em",
                  fontWeight: 600,
                  fontSize: "1em",
                  cursor: "pointer",
                }}
                onClick={() => setShowConfirmation(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
