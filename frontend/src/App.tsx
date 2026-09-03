import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import LandingPage from "./pages/LandingPage";
import CustomerLogin from "./pages/CustomerLogin";
import CustomerDashboard from "./pages/CustomerDashboard";
import ManagementLogin from "./pages/ManagementLogin";
import ManagementRequestAccess from "./pages/ManagementRequestAccess";
import Dashboard from "./pages/Dashboard";
import RecoveryQueue from "./pages/RecoveryQueue";
import RecoveryCaseDetails from "./pages/RecoveryCaseDetails";
import Decisions from "./pages/Decisions";
import Customers from "./pages/Customers";
import RecoveryActions from "./pages/RecoveryActions";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ============================================================ */}
        {/* PUBLIC                                                       */}
        {/* ============================================================ */}

        <Route
          path="/"
          element={<LandingPage />}
        />

        {/* ============================================================ */}
        {/* CUSTOMER AUTH                                                */}
        {/* ============================================================ */}

        <Route
          path="/customer/login"
          element={<CustomerLogin />}
        />

        {/* ============================================================ */}
        {/* CUSTOMER PORTAL                                              */}
        {/* ============================================================ */}

        <Route
          path="/customer/dashboard"
          element={<CustomerDashboard />}
        />

        {/* ============================================================ */}
        {/* MANAGEMENT AUTH                                               */}
        {/* ============================================================ */}

        <Route
          path="/management/login"
          element={<ManagementLogin />}
        />

        <Route
          path="/management/request-access"
          element={<ManagementRequestAccess />}
        />

        {/* ============================================================ */}
        {/* MANAGEMENT / ADMIN                                            */}
        {/* ============================================================ */}

        <Route
          path="/management"
          element={<Dashboard />}
        />

        <Route
          path="/management/recovery-queue"
          element={<RecoveryQueue />}
        />

        <Route
          path="/management/decisions"
          element={<Decisions />}
        />

        <Route
          path="/management/customers"
          element={<Customers />}
        />

        <Route
          path="/management/recovery-actions"
          element={<RecoveryActions />}
        />

        <Route
          path="/management/recovery-cases/:recoveryCaseId"
          element={<RecoveryCaseDetails />}
        />

        {/* ============================================================ */}
        {/* BACKWARD-COMPATIBILITY ROUTES                                 */}
        {/* ============================================================ */}

        <Route
          path="/recovery-queue"
          element={
            <Navigate
              to="/management/recovery-queue"
              replace
            />
          }
        />

        <Route
          path="/decisions"
          element={
            <Navigate
              to="/management/decisions"
              replace
            />
          }
        />

        <Route
          path="/customers"
          element={
            <Navigate
              to="/management/customers"
              replace
            />
          }
        />

        <Route
          path="/recovery-actions"
          element={
            <Navigate
              to="/management/recovery-actions"
              replace
            />
          }
        />

        <Route
          path="/recovery-cases/:recoveryCaseId"
          element={
            <Navigate
              to="/management/recovery-cases/:recoveryCaseId"
              replace
            />
          }
        />

        {/* ============================================================ */}
        {/* FALLBACK                                                      */}
        {/* ============================================================ */}

        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;