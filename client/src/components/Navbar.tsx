import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="hdr">
      <NavLink to="/" className="brand-link">
        <div className="brand">
          <span className="bmark">♥</span>
          <span className="bname">Heart Tag</span>
          <span className="bsub">Healthcare Guiding Badge</span>
        </div>
      </NavLink>
      <nav className="top-nav" aria-label="Main navigation">
        <NavLink to="/lookup" className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          Find Patient RFID
        </NavLink>
        <NavLink
          to="/patient-txt-writer"
          className={({ isActive }) => (isActive ? "tab active" : "tab")}
        >
          Patient TXT Writer
        </NavLink>
      </nav>
      <div className="nav-user">
        <span className="user-name">{user?.name}</span>
        <button onClick={handleLogout} className="logout-btn">
          Logout
        </button>
      </div>
    </header>
  );
}
