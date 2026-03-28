import { BrowserRouter as Router } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Navbar } from "./components/layout/Navbar";
import { AppRoutes } from "./routes";

import "./styles.css";

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="layout-root">
          <Navbar />
          <AppRoutes />
        </div>
      </Router>
    </AuthProvider>
  );
}


