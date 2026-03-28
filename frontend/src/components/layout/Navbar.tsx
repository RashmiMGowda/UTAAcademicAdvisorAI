import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { LogOut, LayoutDashboard, MessageSquare, User as UserIcon, LogIn, UserPlus } from "lucide-react";
import { PATH_ADVISOR, PATH_DASHBOARD, PATH_HOME, PATH_LOGIN, PATH_REGISTER } from "../../routes/paths";

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate(PATH_LOGIN);
  };

  return (
    <nav className="main-navbar">
      <div className="nav-brand">
        <Link to={PATH_HOME}>UTA Advisor</Link>
      </div>
      
      <div className="nav-links">
        {isAuthenticated ? (
          <>
            <Link to={PATH_ADVISOR} className="nav-item">
              <MessageSquare size={18} />
              <span>Advisor</span>
            </Link>
            <Link to={PATH_DASHBOARD} className="nav-item">
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </Link>
          </>
        ) : null}
      </div>

      <div className="nav-user">
        {isAuthenticated ? (
          <>
            <div className="user-info">
              <UserIcon size={18} />
              <span>{user?.name}</span>
            </div>
            <button onClick={handleLogout} className="logout-button" title="Logout">
              <LogOut size={18} />
            </button>
          </>
        ) : (
          <div className="auth-nav-group">
            <Link to={PATH_LOGIN} className="nav-item auth-link">
              <LogIn size={18} />
              <span>Sign In</span>
            </Link>
            <Link to={PATH_REGISTER} className="nav-item auth-link register-button">
              <UserPlus size={18} />
              <span>Register</span>
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

