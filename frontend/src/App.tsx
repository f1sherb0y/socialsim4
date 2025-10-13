import { Suspense } from "react";
import i18n from "./i18n";
import { Navigate, Route, Routes } from "react-router-dom";

import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SavedSimulationsPage } from "./pages/SavedSimulationsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SimulationWizardPage } from "./pages/SimulationWizardPage";
import { SimulationPage } from "./pages/SimulationPage";
import { RequireAuth } from "./components/RequireAuth";
import { Layout } from "./components/Layout";

export default function App() {
  return (
    <Suspense fallback={<div className="app-loading">{i18n.t('common.loading')}</div>}>
      <Routes>
        <Route path="/" element={<Layout><LandingPage /></Layout>} />
        <Route path="/login" element={<Layout><LoginPage /></Layout>} />
        <Route path="/register" element={<Layout><RegisterPage /></Layout>} />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Layout>
                <DashboardPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/new/*"
          element={
            <RequireAuth>
              <Layout>
                <SimulationWizardPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/saved"
          element={
            <RequireAuth>
              <Layout>
                <SavedSimulationsPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/simulations/:id"
          element={
            <RequireAuth>
              <Layout>
                <SimulationPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route
          path="/settings/*"
          element={
            <RequireAuth>
              <Layout>
                <SettingsPage />
              </Layout>
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
