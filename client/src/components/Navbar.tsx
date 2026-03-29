import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="hdr">
      <div className="brand">
        <span className="bmark">♥</span>
        <span className="bname">Heart Tag</span>
        <span className="bsub">Healthcare Guiding Badge</span>
      </div>
      <nav className="top-nav" aria-label="Main navigation">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          Find Patient RFID
        </NavLink>
        <NavLink
          to="/patient-txt-writer"
          className={({ isActive }) => (isActive ? "tab active" : "tab")}
        >
          Patient TXT Writer
        </NavLink>
      </nav>
    </header>
  );
}
