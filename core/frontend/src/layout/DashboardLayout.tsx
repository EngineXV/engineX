import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import { DashboardProvider } from "../context/DashboardContext";

export default function DashboardLayout() {
  return (
    <DashboardProvider>
      <div className="dashboard-shell">
        <Sidebar />
        <div className="dashboard-main">
          <Outlet />
        </div>
      </div>
    </DashboardProvider>
  );
}
