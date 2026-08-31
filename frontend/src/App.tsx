import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import RecoveryQueue from "./pages/RecoveryQueue";
import RecoveryCaseDetails from "./pages/RecoveryCaseDetails";

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
          path="/recovery-cases/:recoveryCaseId"
          element={<RecoveryCaseDetails />}
        />

        <Route
          path="/decisions"
          element={
            <PlaceholderPage
              title="Decisions"
              description="AI recovery decisions and reasoning will appear here."
            />
          }
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

        <NavigateBack />
      </div>
    </div>
  );
}

function NavigateBack() {
  return (
    <a
      href="/"
      className="secondary-button"
    >
      Back to Dashboard
    </a>
  );
}

export default App;