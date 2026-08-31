import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

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
        {/* Admin Dashboard */}
        <Route
          path="/"
          element={<Dashboard />}
        />

        {/* Recovery Queue */}
        <Route
          path="/recovery-queue"
          element={<RecoveryQueue />}
        />

        {/* AI Decisions */}
        <Route
          path="/decisions"
          element={<Decisions />}
        />

        {/* Customers */}
        <Route
          path="/customers"
          element={<Customers />}
        />

        {/* Recovery Case Details */}
        <Route
          path="/recovery-cases/:recoveryCaseId"
          element={<RecoveryCaseDetails />}
        />
        <Route
          path="/recovery-actions"
          element={<RecoveryActions />}
        />

        {/* Fallback */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;