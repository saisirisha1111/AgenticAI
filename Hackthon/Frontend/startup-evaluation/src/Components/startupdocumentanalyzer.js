// import React, { useCallback, useState } from "react";
// import {
//   Box,
//   Button,
//   Container,
//   Typography,
//   Paper,
//   Grid,
//   List,
//   ListItem,
//   ListItemText,
//   LinearProgress,
//   Card,
//   CardContent,
//   IconButton,
//   TextField,
//   Stack
// } from "@mui/material";
// import { Upload as UploadIcon, Delete as DeleteIcon } from "@mui/icons-material";
// import { useDropzone } from "react-dropzone";
// import axios from "axios";

// function humanFileSize(bytes) {
//   if (bytes === 0) return "0 B";
//   const i = Math.floor(Math.log(bytes) / Math.log(1024));
//   const sizes = ["B", "KB", "MB", "GB", "TB"];
//   return (bytes / Math.pow(1024, i)).toFixed(2) + " " + sizes[i];
// }

// export default function StartupDocumentAnalyzer({ onUploadComplete }) {
//   const [files, setFiles] = useState([]);
//   const [uploading, setUploading] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [error, setError] = useState(null);
//   const [founder_email, setfounder_email] = useState("");

//   const onDrop = useCallback((acceptedFiles) => {
//     setFiles(prev => {
//       const map = new Map(prev.map(f => [f.name + f.size, f]));
//       acceptedFiles.forEach(f => map.set(f.name + f.size, f));
//       return Array.from(map.values());
//     });
//   }, []);

//   const { getRootProps, getInputProps, isDragActive } = useDropzone({
//     onDrop,
//     accept: {
//       "application/pdf": [".pdf"],
//       "application/vnd.ms-powerpoint": [".ppt", ".pptx"],
//       "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
//       "application/msword": [".doc", ".docx"],
//       "text/plain": [".txt"],
//       "audio/*": [],
//       "video/*": []
//     },
//     multiple: true
//   });

//   const handleUpload = async () => {
//     if (!files.length) {
//       setError("No files selected.");
//       return;
//     }
//     if (!founder_email) {
//       setError("Please enter your email before uploading.");
//       return;
//     }

//     setUploading(true);
//     setProgress(0);
//     setError(null);

//     try {
//       const formData = new FormData();
//       files.forEach(f => formData.append("files", f));
//       formData.append("user_email", founder_email);

//       await axios.post(
//         "https://8000-pulletikusuma-agenticai-9r7yzzl7jcs.ws-us121.gitpod.io/upload-and-analyze",
//         formData,
//         {
//           headers: { "Content-Type": "multipart/form-data" },
//           onUploadProgress: (p) => setProgress(Math.round((p.loaded * 100) / (p.total || 1))),
//           timeout: 5 * 60 * 1000
//         }
//       );

//       // ✅ Call parent callback to switch to voice assistant
//       onUploadComplete(founder_email);
//     } catch (err) {
//       setError(err?.response?.data?.detail || err.message || "Upload failed");
//     } finally {
//       setUploading(false);
//     }
//   };

//   return (
//     <Container maxWidth="md" sx={{ py: 4 }}>
//       <Typography variant="h4" gutterBottom align="center">
//         AI Startup Analysis — Upload Files & Folders
//       </Typography>

//       <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
//         <Grid container spacing={2} alignItems="center">
//           <Grid item xs={12} md={8}>
//             <TextField
//               label="Your Email"
//               variant="outlined"
//               fullWidth
//               value={founder_email}
//               onChange={(e) => {
//                 const email = e.target.value;
//                 setfounder_email(email);
//                 const gmailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
//                 setError(email && !gmailRegex.test(email) ? "Please enter a valid Gmail address." : null);
//               }}
//               error={!!error}
//               helperText={error}
//               sx={{ mb: 2 }}
//             />

//             <div
//               {...getRootProps()}
//               style={{
//                 border: "2px dashed #1976d2",
//                 borderRadius: 8,
//                 padding: 20,
//                 textAlign: "center",
//                 cursor: "pointer",
//                 background: isDragActive ? "#e3f2fd" : "transparent"
//               }}
//             >
//               <input {...getInputProps()} />
//               <Typography variant="body1">
//                 {isDragActive ? "Drop the files here..." : "Drag & drop files here, or click to select files"}
//               </Typography>
//             </div>
//           </Grid>

//           <Grid item xs={12} md={4}>
//             <Stack spacing={1}>
//               <Button
//                 variant="contained"
//                 component="label"
//                 startIcon={<UploadIcon />}
//                 fullWidth
//               >
//                 Select folder
//                 <input
//                   type="file"
//                   webkitdirectory="true"
//                   directory="true"
//                   multiple
//                   hidden
//                   onChange={(e) => {
//                     const fileList = Array.from(e.target.files || []);
//                     if (fileList.length) setFiles(prev => [...prev, ...fileList]);
//                   }}
//                 />
//               </Button>
//             </Stack>
//           </Grid>
//         </Grid>
//       </Paper>

//       <Card variant="outlined">
//         <CardContent>
//           <Typography variant="h6">Selected Files ({files.length})</Typography>
//           <List dense>
//             {files.map((f, i) => (
//               <ListItem key={f.name + f.size + i}>
//                 <ListItemText
//                   primary={f.name}
//                   secondary={`${humanFileSize(f.size)} • ${f.type || "unknown"}`}
//                 />
//               </ListItem>
//             ))}
//             {files.length === 0 && <Typography variant="body2">No files selected.</Typography>}
//           </List>

//           <Box sx={{ mt: 2 }}>
//             <Button
//               variant="contained"
//               color="primary"
//               onClick={handleUpload}
//               disabled={uploading || files.length === 0}
//             >
//               {uploading ? "Uploading & Processing..." : "Send to Analysis"}
//             </Button>
//           </Box>

//           {uploading && (
//             <Box sx={{ mt: 2 }}>
//               <Typography variant="body2">Please wait, analysis is in progress: {progress}%</Typography>
//               <LinearProgress variant="determinate" value={progress} sx={{ mt: 1 }} />
//             </Box>
//           )}
//         </CardContent>
//       </Card>
//     </Container>
//   );
// }

import React, { useCallback, useState } from "react";
import {
  Box,
  Button,
  Container,
  Typography,
  Paper,
  Grid,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  Card,
  CardContent,
  IconButton,
  TextField,
  Stack
} from "@mui/material";
import { Upload as UploadIcon, Delete as DeleteIcon } from "@mui/icons-material";
import { useDropzone } from "react-dropzone";
import axios from "axios";

function humanFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  return (bytes / Math.pow(1024, i)).toFixed(2) + " " + sizes[i];
}

export default function StartupDocumentAnalyzer({ onUploadComplete }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [founder_email, setfounder_email] = useState("");

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => {
      const map = new Map(prev.map(f => [f.name + f.size, f]));
      acceptedFiles.forEach(f => map.set(f.name + f.size, f));
      return Array.from(map.values());
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.ms-powerpoint": [".ppt", ".pptx"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/msword": [".doc", ".docx"],
      "text/plain": [".txt"],
      "audio/*": [],
      "video/*": []
    },
    multiple: true
  });

  const handleUpload = async () => {
    if (!files.length) {
      setError("No files selected.");
      return;
    }
    if (!founder_email) {
      setError("Please enter your email before uploading.");
      return;
    }

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));
      formData.append("user_email", founder_email);

      await axios.post(
        "https://8000-pulletikusuma-agenticai-9r7yzzl7jcs.ws-us121.gitpod.io/upload-and-analyze",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (p) => setProgress(Math.round((p.loaded * 100) / (p.total || 1))),
          timeout: 5 * 60 * 1000
        }
      );

      // ✅ Call parent callback to switch to voice assistant
      onUploadComplete(founder_email);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom align="center">
        AI Startup Analysis — Upload Files & Folders
      </Typography>

      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <TextField
              label="Your Email"
              variant="outlined"
              fullWidth
              value={founder_email}
              onChange={(e) => {
                const email = e.target.value;
                setfounder_email(email);
                const gmailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
                setError(email && !gmailRegex.test(email) ? "Please enter a valid Gmail address." : null);
              }}
              error={!!error}
              helperText={error}
              sx={{ mb: 2 }}
            />

            <div
              {...getRootProps()}
              style={{
                border: "2px dashed #1976d2",
                borderRadius: 8,
                padding: 20,
                textAlign: "center",
                cursor: "pointer",
                background: isDragActive ? "#e3f2fd" : "transparent"
              }}
            >
              <input {...getInputProps()} />
              <Typography variant="body1">
                {isDragActive ? "Drop the files here..." : "Drag & drop files here, or click to select files"}
              </Typography>
            </div>
          </Grid>

          <Grid item xs={12} md={4}>
            <Stack spacing={1}>
              <Button
                variant="contained"
                component="label"
                startIcon={<UploadIcon />}
                fullWidth
              >
                Select folder
                <input
                  type="file"
                  webkitdirectory="true"
                  directory="true"
                  multiple
                  hidden
                  onChange={(e) => {
                    const fileList = Array.from(e.target.files || []);
                    if (fileList.length) setFiles(prev => [...prev, ...fileList]);
                  }}
                />
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6">Selected Files ({files.length})</Typography>
          <List dense>
            {files.map((f, i) => (
              <ListItem key={f.name + f.size + i}>
                <ListItemText
                  primary={f.name}
                  secondary={`${humanFileSize(f.size)} • ${f.type || "unknown"}`}
                />
              </ListItem>
            ))}
            {files.length === 0 && <Typography variant="body2">No files selected.</Typography>}
          </List>

          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
            >
              {uploading ? "Uploading & Processing..." : "Send to Analysis"}
            </Button>
          </Box>

          {uploading && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">Please wait, analysis is in progress: {progress}%</Typography>
              <LinearProgress variant="determinate" value={progress} sx={{ mt: 1 }} />
            </Box>
          )}
        </CardContent>
      </Card>
    </Container>
  );
}