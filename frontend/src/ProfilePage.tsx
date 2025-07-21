import React from "react";

export default function ProfilePage() {
  return (
    <div className="profile-panel">
      <h2>Profile</h2>
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
            "Resume uploaded: " + (e.dataTransfer.files[0]?.name || "No file")
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
  );
}
