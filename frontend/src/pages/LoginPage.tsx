import { useState, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PATH_ADVISOR, PATH_REGISTER } from "../routes/paths";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const { login, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (email && name) {
      await login(email, name);
      navigate(PATH_ADVISOR);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand-mark">UTA</div>
        <h1>Welcome Back</h1>
        <p className="auth-subtitle">Sign in to access your AI academic advisor.</p>
        
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
          
          <button type="submit" className="send-button" disabled={loading}>
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>
        
        <p className="auth-footer">
          Don't have an account? <Link to={PATH_REGISTER}>Register</Link>
        </p>
      </div>
    </div>
  );
}
