import React, { useState } from "react";
import StartupDocumentAnalyzer from "./Components/startupdocumentanalyzer";
import StartupQuestionnaire from "./Components/StartupQuestionnaire";

function App() {
  const [userEmail, setUserEmail] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUploadComplete = (email) => {
    // Show spinner while backend prepares questions
    setLoading(true);
    setUserEmail(email);

    // Simulate wait for backend prep (or replace with actual status check API)
    setTimeout(() => {
      setLoading(false);
    }, 4000);
  };

  return (
    <div style={{ fontFamily: "Arial, sans-serif" }}>
      {!userEmail ? (
        <StartupDocumentAnalyzer onUploadComplete={handleUploadComplete} />
      ) : loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div className="spinner" />
          <p>Preparing your personalized questions...</p>
          <style>
            {`
              .spinner {
                margin: 20px auto;
                width: 50px;
                height: 50px;
                border: 6px solid #f3f3f3;
                border-top: 6px solid #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
              }
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}
          </style>
        </div>
      ) : (
        <StartupQuestionnaire userEmail={userEmail} />
      )}
    </div>
  );
}

export default App;
