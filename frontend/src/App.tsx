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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={<Dashboard />}
        />

        <Route
          path="/recovery-queue"
          element={<RecoveryQueue />}
        />

        <Route
          path="/decisions"
          element={<Decisions />}
        />

        <Route
          path="/recovery-cases/:recoveryCaseId"
          element={<RecoveryCaseDetails />}
        />

        <Route
          path="/customers"
          element={
            <PlaceholderPage
              title="Customers"
              description="Customer recovery profiles will appear here."
            />
          }
        />

        <Route
          path="/recovery-actions"
          element={
            <PlaceholderPage
              title="Recovery Actions"
              description="Recovery approval and execution activity will appear here."
            />
          }
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page-shell">
      <div className="placeholder-page">
        <div className="eyebrow">
          RAZORRECOVER AI
        </div>

        <h1>{title}</h1>

        <p>{description}</p>

        <a
          href="/"
          className="secondary-button"
        >
          Back to Dashboard
        </a>
      </div>
    </div>
  );
}

export default App;