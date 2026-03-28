import { NavLink, Route, Routes } from "react-router-dom";
import LookupPage from "./pages/LookupPage";
import PatientTxtWriterPage from "./pages/PatientTxtWriterPage";

export default function App() {
  return (
    <div className="app">
      <header className="hdr">
        <div className="brand">
          <span className="bmark">♥</span>
          <span className="bname">Heart Tag</span>
          <span className="bsub">RFID + TXT Workflow</span>
        </div>
        <nav className="top-nav" aria-label="Main navigation">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "tab active" : "tab")}>
            Lookup
          </NavLink>
          <NavLink
            to="/patient-txt-writer"
            className={({ isActive }) => (isActive ? "tab active" : "tab")}
          >
            Patient TXT Writer
          </NavLink>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<LookupPage />} />
        <Route path="/patient-txt-writer" element={<PatientTxtWriterPage />} />
      </Routes>
    </div>
  );
}
