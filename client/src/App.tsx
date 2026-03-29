import { Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import LandingPage from "./pages/LandingPage";
import LookupPage from "./pages/LookupPage";
import PatientTxtWriterPage from "./pages/PatientTxtWriterPage";

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="app">
      {isAuthenticated && <Navbar />}

      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <LandingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/lookup"
          element={
            <ProtectedRoute>
              <LookupPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/patient-txt-writer"
          element={
            <ProtectedRoute>
              <PatientTxtWriterPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}
