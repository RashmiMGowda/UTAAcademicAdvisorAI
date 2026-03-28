import { Link } from "react-router-dom";
import { PATH_ADVISOR } from "../routes/paths";
import { ArrowRight, BookOpen, GraduationCap, Map } from "lucide-react";

export function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="hero-content">
          <div className="section-kicker">UTA Academic Advisor</div>
          <h1>Navigate Your Degree with Confidence</h1>
          <p className="hero-subtitle">
            The intelligent RAG-powered assistant designed specifically for UTA students. 
            Get instant semester plans, prerequisite guidance, and degree-path insights.
          </p>
          <div className="hero-actions">
            <Link to={PATH_ADVISOR} className="send-button hero-cta">
              Get Started <ArrowRight size={18} />
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="visual-card">
            <div className="card-icon"><GraduationCap size={32} /></div>
            <h3>Smart Planning</h3>
            <p>Generate optimized semester-by-semester course plans.</p>
          </div>
          <div className="visual-card">
            <div className="card-icon"><Map size={32} /></div>
            <h3>Path Discovery</h3>
            <p>Understand complex prerequisites and course sequences.</p>
          </div>
        </div>
      </section>

      <section className="home-features">
        <div className="feature-grid">
          <div className="feature-item">
            <div className="feature-icon"><BookOpen size={24} /></div>
            <h4>Accurate Data</h4>
            <p>Pulled directly from official UTA advising documents and catalogs.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon"><Map size={24} /></div>
            <h4>Smart Pathing</h4>
            <p>Understand which courses to take next with intelligent RAG retrieval.</p>
          </div>
          <div className="feature-item">
            <div className="feature-icon"><GraduationCap size={24} /></div>
            <h4>Degree Success</h4>
            <p>Stay on track for graduation with optimized semester planning.</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="brand-mark">UTA</div>
            <p>The student-first AI advisor for University of Texas at Arlington.</p>
          </div>
          <div className="footer-links">
            <div className="footer-link-col">
              <h5>Resources</h5>
              <a href="https://www.uta.edu/academics/schools-colleges/engineering" target="_blank" rel="noreferrer">College of Engineering</a>
              <a href="https://www.uta.edu/advising" target="_blank" rel="noreferrer">University Advising</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} RAG Advisor. Not an official UTA application.</p>
        </div>
      </footer>
    </div>
  );
}

