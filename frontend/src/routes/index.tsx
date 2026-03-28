import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./guards/ProtectedRoute";
import { HomePage } from "../pages/HomePage";
import { AdvisorPage } from "../pages/AdvisorPage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import { DashboardPage } from "../pages/DashboardPage";
import { AnimatePresence } from "framer-motion";
import { PATH_ADVISOR, PATH_DASHBOARD, PATH_HOME, PATH_LOGIN, PATH_REGISTER } from "./paths";

export function AppRoutes() {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route path={PATH_HOME} element={<HomePage />} />
        <Route path={PATH_LOGIN} element={<LoginPage />} />
        <Route path={PATH_REGISTER} element={<RegisterPage />} />
        
        <Route 
          path={PATH_ADVISOR} 
          element={
            <ProtectedRoute>
              <AdvisorPage />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path={PATH_DASHBOARD} 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        
        <Route path="/" element={<Navigate to={PATH_ADVISOR} replace />} />
        <Route path="*" element={<Navigate to={PATH_ADVISOR} replace />} />
      </Routes>
    </AnimatePresence>
  );
}
