import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { PATH_LOGIN } from "../paths";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="loading-screen">Authenticating...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to={PATH_LOGIN} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
