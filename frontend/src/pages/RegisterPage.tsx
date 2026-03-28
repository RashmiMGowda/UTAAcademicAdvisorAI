import { useState, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PATH_ADVISOR, PATH_LOGIN } from "../routes/paths";

export function RegisterPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [program, setProgram] = useState("CSE");
  const { login, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (email && name) {
      // Mock registration
      await login(email, name);
      navigate(PATH_ADVISOR);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand-mark">UTA</div>
        <h1>Create Account</h1>
        <p className="auth-subtitle">Get personalized degree guidance at UTA.</p>
        
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span>Full Name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              required
            />
          </label>
          <label className="field">
            <span>Email Address</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="student@uta.edu"
              required
            />
          </label>
          <label className="field">
            <span>Major Program</span>
            <select value={program} onChange={(e) => setProgram(e.target.value)}>
              <option value="CSE">Computer Science</option>
              <option value="SE">Software Engineering</option>
              <option value="CompE">Computer Engineering</option>
            </select>
          </label>
          
          <button type="submit" className="send-button" disabled={loading}>
            {loading ? "Registering..." : "Create Account"}
          </button>
        </form>
        
        <p className="auth-footer">
          Already have an account? <Link to={PATH_LOGIN}>Sign In</Link>
        </p>
      </div>
    </div>
  );
}
