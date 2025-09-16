import React, { useState, useEffect, useRef } from "react";

function StartupDocumentAnalyzer() {
  const [userEmail, setUserEmail] = useState("");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const socketRef = useRef(null);

  // Replace <workspace-id> with your Gitpod workspace ID
  const WS_URL = "wss://4000-saisirisha111-agenticai-5z4jw52towo.ws-us121.gitpod.io/ws";

  // Initialize WebSocket connection
  useEffect(() => {
    socketRef.current = new WebSocket(WS_URL);

    socketRef.current.onopen = () => {
      console.log("Connected to WebSocket server!");
      setWsConnected(true);
      socketRef.current.send("Hello from client!");
    };

    socketRef.current.onmessage = (event) => {
      console.log("Server says:", event.data);
    };

    socketRef.current.onclose = () => {
      console.log("Disconnected from WebSocket server");
      setWsConnected(false);
    };

    socketRef.current.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    // Cleanup on unmount
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

    const BACKEND_URL = "https://8000-saisirisha111-agenticai-5z4jw52towo.ws-us121.gitpod.io/upload-and-analyze";
  // const BACKEND_URL = "http://127.0.0.1:8000/upload-and-analyze";

  const handleFileChange = (e) => {
    setFiles(e.target.files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userEmail || files.length === 0) {
      setError("Please provide an email and upload at least one file.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("user_email", userEmail);

    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await fetch(BACKEND_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();
      let parsedResult;
      try {
        parsedResult = JSON.parse(data.response);
      } catch {
        parsedResult = data.response;
      }
      setResult(parsedResult);

      // Optionally send result to WebSocket server
      if (wsConnected && socketRef.current) {
        socketRef.current.send(
          JSON.stringify({ type: "analysis_result", data: parsedResult })
        );
      }
    } catch (err) {
      setError(err.message || "Unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "2rem" }}>
      <h1>📊 Startup Document Analyzer</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Email:</label>
          <br />
          <input
            type="email"
            value={userEmail}
            onChange={(e) => setUserEmail(e.target.value)}
            required
          />
        </div>
        <div style={{ marginTop: "1rem" }}>
          <label>Upload Documents:</label>
          <br />
          <input
            type="file"
            accept=".pdf,.ppt,.pptx,.txt,.mp3,.wav,.m4a"
            multiple
            onChange={handleFileChange}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          style={{ marginTop: "1rem", padding: "0.5rem 1rem" }}
        >
          {loading ? "Uploading and analyzing..." : "Analyze"}
        </button>
      </form>

      {error && <div style={{ color: "red", marginTop: "1rem" }}>❌ {error}</div>}

      {result && (
        <div style={{ marginTop: "1rem" }}>
          <h3>Result:</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default StartupDocumentAnalyzer;
