import React from "react";

export default function ProfilePage() {
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
              alert(
                "Resume uploaded: " +
                  (e.dataTransfer.files[0]?.name || "No file")
              );
            }}
          >
            <span>Drop your resume here or click to upload</span>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              className="resume-file-input"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  alert("Resume uploaded: " + e.target.files[0].name);
                }
              }}
            />
          </div>
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
    </div>
  );
}
