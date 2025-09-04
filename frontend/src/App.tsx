import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Queue from "./pages/Queue";
import JobDetail from "./pages/JobDetail";
import "./index.css";

function App() {
    return (
        <Router>
            <div className="min-h-screen" style={{ backgroundColor: "var(--dark-bg)", color: "var(--text-light)" }}>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/queue" element={<Queue />} />
                    <Route path="/job/:jobId" element={<JobDetail />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
