import { useAuth } from "../context/AuthContext";
import { LayoutDashboard, BookOpen, Clock, Settings, Bell } from "lucide-react";

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>Student Dashboard</h1>
        <p>Welcome back, {user?.name}! Here's your degree progress at a glance.</p>
      </header>
      
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <div className="card-icon"><LayoutDashboard size={24} /></div>
          <h3>Degree Progress</h3>
          <div className="progress-placeholder">
            <div className="progress-bar" style={{ width: "65%" }}></div>
            <span>65% Complete</span>
          </div>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon"><BookOpen size={24} /></div>
          <h3>Saved Plans</h3>
          <p className="placeholder-text">You haven't saved any course plans yet. Ask the advisor for a plan and save it to see it here!</p>
        </div>
        
        <div className="dashboard-card">
          <div className="card-icon"><Clock size={24} /></div>
          <h3>Recent Activity</h3>
          <ul className="activity-list">
            <li>Asked about "Senior Fall CSE Electives"</li>
            <li>Viewed "Prerequisites for CSE 3318"</li>
          </ul>
        </div>
        
        <div className="dashboard-card action-card">
          <div className="card-icon"><Settings size={24} /></div>
          <h3>Settings</h3>
          <p>Manage your account and program preferences.</p>
        </div>
      </div>
      
      <div className="notification-center">
        <div className="section-kicker"><Bell size={16} /> Notifications</div>
        <div className="notification-item">Register for Fall 2026 by April 15th!</div>
      </div>
    </div>
  );
}
