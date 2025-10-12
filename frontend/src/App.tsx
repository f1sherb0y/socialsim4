import { Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SavedSimulationsPage } from "./pages/SavedSimulationsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SimulationWizardPage } from "./pages/SimulationWizardPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { RequireAuth } from "./components/RequireAuth";

export default function App() {
  return (
    <Suspense fallback={<div className="app-loading">Loading…</div>}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/new/*"
          element={
            <RequireAuth>
              <SimulationWizardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/saved"
          element={
            <RequireAuth>
              <SavedSimulationsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/:id"
          element={
            <RequireAuth>
              <WorkspacePage />
            </RequireAuth>
          }
        />
        <Route
          path="/settings/*"
          element={
            <RequireAuth>
              <SettingsPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
