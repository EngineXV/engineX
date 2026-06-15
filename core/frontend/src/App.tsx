import { Navigate, Route, Routes, useParams } from "react-router-dom";
import DashboardLayout from "./layout/DashboardLayout";
import WelcomePage from "./pages/WelcomePage";
import SessionPage from "./pages/SessionPage";
import CredentialsPage from "./pages/CredentialsPage";
import SkillsPage from "./pages/SkillsPage";
import OrgChartPage from "./pages/OrgChartPage";

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="/org-chart" element={<OrgChartPage />} />
        <Route path="/credentials" element={<CredentialsPage />} />
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/agent/:sessionId" element={<LegacyAgentRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function LegacyAgentRedirect() {
  const { sessionId } = useParams();
  return <Navigate to={`/session/${sessionId}`} replace />;
}
