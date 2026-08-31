import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import RecoveryQueue from "./pages/RecoveryQueue";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />

        <Route
          path="/recovery-queue"
          element={<RecoveryQueue />}
        />

        {/* Temporary placeholders for pages we will build next */}
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
          path="/recovery-cases/:recoveryCaseId"
          element={
            <PlaceholderPage
              title="Recovery Case"
              description="Case details, AI decision, approval, execution and audit timeline will appear here."
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
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#070d16",
        color: "#f4f7fb",
        padding: "32px",
      }}
    >
      <div
        style={{
          maxWidth: "600px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: "12px",
            letterSpacing: "0.14em",
            color: "#5b9cff",
            marginBottom: "12px",
          }}
        >
          RAZORRECOVER AI
        </div>

        <h1
          style={{
            margin: 0,
            fontSize: "32px",
          }}
        >
          {title}
        </h1>

        <p
          style={{
            marginTop: "12px",
            color: "#7187a2",
            lineHeight: 1.6,
          }}
        >
          {description}
        </p>
      </div>
    </div>
  );
}

export default App;