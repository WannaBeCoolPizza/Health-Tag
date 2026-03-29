import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import LookupPage from "./pages/LookupPage";
import PatientTxtWriterPage from "./pages/PatientTxtWriterPage";

export default function App() {
  return (
    <div className="app">
      <Navbar />

      <Routes>
        <Route path="/" element={<LookupPage />} />
        <Route path="/patient-txt-writer" element={<PatientTxtWriterPage />} />
      </Routes>
    </div>
  );
}
