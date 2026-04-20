import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

const configError =
  import.meta.env.VITE_SUPABASE_URL?.includes("your-project-id.supabase.co") ||
    !import.meta.env.VITE_SUPABASE_URL ||
    !import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY
    ? "Supabase isn’t set up yet.Please add your Project URL and Publishable Key in frontend/.env.local to enable sign in and registration."
    : "";
// // this code programOptions array is used to populate the dropdown 
// // menu for selecting a program during registration.
// const programOptions = [
//   { value: "CSE", label: "Computer Science" },
//   { value: "SE", label: "Software Engineering" },
//   { value: "CompE", label: "Computer Engineering" },
//   { value: "EE", label: "Electrical Engineering" },
//   { value: "ME", label: "Mechanical Engineering" },
//   { value: "IE", label: "Industrial Engineering" },
//   { value: "CivilE", label: "Civil Engineering" },
//   { value: "AREN", label: "Architectural Engineering" }
// ];

export function LoginPage() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [program, setProgram] = useState("UTA");
  const [error, setError] = useState(null);
  const { login, signUp, loading } = useAuth();

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (mode === "login") {
      const { error: loginError } = await login(email, password);
      if (loginError) {
        setError(loginError.message || String(loginError));
      }
      return;
    }

    const { error: signUpError } = await signUp(email, password, name || email, program);
    if (signUpError) {
      setError(signUpError.message || String(signUpError));
      return;
    }

    setError("Account created successfully!");
    setMode("login");
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand-mark">UTA</div>
        <h1>{mode === "login" ? "Welcome Back" : "Create Account"}</h1>
        <p className="auth-subtitle">
          {mode === "login"
            ? "Sign in to chat with your academic advisor"
            : "Create an account to save your chats and start planning your courses."}
        </p>

        {configError ? (
          <div className="error-message error-message-help">
            <strong>Setup needed before login</strong>
            <div>{configError}</div>
          </div>
        ) : null}

        <div className="auth-toggle">
          <button
            type="button"
            className={`toggle-chip ${mode === "login" ? "is-active" : ""}`}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`toggle-chip ${mode === "register" ? "is-active" : ""}`}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Register
          </button>
        </div>

        {error ? (
          <div className="error-message error-message-help">
            <strong>{mode === "login" ? "Login failed" : "Registration failed"}</strong>
            <div>{error}</div>
            <div className="error-hint">
              {mode === "login"
                ? "Login failed. Check your email and password, and try again."
                : "Registration failed. Please check your information and try again."}
            </div>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "register" ? (
            <>
              <label className="field">
                <span>Full Name</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Enter your name"
                  required
                />
              </label>
              {/* <label className="field">
                <span>Program</span>
                <select value={program} onChange={(event) => setProgram(event.target.value)}>
                  {programOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label> */}
            </>
          ) : null}

          <label className="field">
            <span>Email Address</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="student@uta.edu"
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
            />
          </label>

          <button type="submit" className="send-button" disabled={loading}>
            {loading
              ? mode === "login"
                ? "Authenticating..."
                : "Registering..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
