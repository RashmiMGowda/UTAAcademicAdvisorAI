import { useState, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PATH_ADVISOR, PATH_LOGIN } from "../routes/paths";

export function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [program, setProgram] = useState("CSE");
  const [error, setError] = useState<string | null>(null);
  const { signUp, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (email && password && name) {
      const { error: signUpError } = await signUp(email, password, name);
      if (signUpError) {
        setError(signUpError.message);
      } else {
        // In Supabase, if email confirmation is required, the user might not be signed in yet.
        // But for a demo, redirecting is fine or we could show a check email message.
        navigate(PATH_ADVISOR);
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand-mark">UTA</div>
        <h1>Create Account</h1>
        <p className="auth-subtitle">Get personalized degree guidance at UTA.</p>
        
        {error && <div className="error-message">{error}</div>}
        
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
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
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
