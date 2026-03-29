import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <main className="landing">
      <div className="landing-hero">
        <span className="landing-heart">♥</span>
        <h1 className="landing-title">Heart Tag</h1>
        <p className="landing-subtitle">A New Way for Healthcare Workers to Find Patients</p>
        
        <p className="landing-description">
          Heart Tag streamlines patient access using RFID technology and intelligent patient records.
          Quickly look up patient information, allergies, medications, and medical history all in one place.
        </p>

        <div className="landing-features">
          <div className="feature-card">
            <span className="feature-icon">🔍</span>
            <h3>Quick RFID Lookup</h3>
            <p>Find patient records instantly by scanning or entering their RFID badge</p>
          </div>

          <div className="feature-card">
            <span className="feature-icon">📋</span>
            <h3>Patient Records</h3>
            <p>View comprehensive medical history, allergies, medications, and conditions</p>
          </div>

          <div className="feature-card">
            <span className="feature-icon">✏️</span>
            <h3>Easy Management</h3>
            <p>Create and manage patient records with our intuitive form interface</p>
          </div>
        </div>

        <div className="landing-cta">
          <Link to="/lookup" className="btn-primary">
            Find a Patient
          </Link>
          <Link to="/patient-txt-writer" className="btn-secondary">
            Create Patient Record
          </Link>
        </div>
      </div>
    </main>
  );
}
