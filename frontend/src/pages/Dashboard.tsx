import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  CircleDollarSign,
  LayoutDashboard,
  RefreshCw,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  getHealth,
  getRecoveryQueue,
} from "../services/api";

import type {
  RecoveryQueueItem,
} from "../types/recovery";

import "../App.css";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function priorityClass(priority: string): string {
  switch (priority) {
    case "P1_HIGH":
      return "priority priority-p1";

    case "P2":
      return "priority priority-p2";

    case "P3":
      return "priority priority-p3";

    default:
      return "priority priority-p4";
  }
}

function actionClass(action: string): string {
  switch (action) {
    case "HIGH_PRIORITY_RECOVERY":
      return "action action-high";

    case "STANDARD_RECOVERY":
      return "action action-standard";

    case "LOW_COST_RECOVERY":
      return "action action-low";

    case "MONITOR":
      return "action action-monitor";

    default:
      return "action action-none";
  }
}

function DashboardSidebar({
  backendHealthy,
}: {
  backendHealthy: boolean;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <ShieldCheck size={22} />
        </div>

        <div>
          <div className="brand-name">
            RazorRecover
          </div>

          <div className="brand-subtitle">
            AI Revenue Recovery
          </div>
        </div>
      </div>

      <nav className="navigation">
        <div className="nav-section-label">
          OPERATIONS
        </div>

        <Link
          to="/"
          className="nav-item nav-item-active"
        >
          <LayoutDashboard size={18} />
          Dashboard
        </Link>

        <Link
          to="/recovery-queue"
          className="nav-item"
        >
          <Target size={18} />
          Recovery Queue
        </Link>

        <Link
          to="/decisions"
          className="nav-item"
        >
          <Activity size={18} />
          Decisions
        </Link>

        <div className="nav-section-label nav-section-spaced">
          MANAGEMENT
        </div>

        <Link
          to="/customers"
          className="nav-item"
        >
          <Users size={18} />
          Customers
        </Link>

        <Link
          to="/recovery-actions"
          className="nav-item"
        >
          <CheckCircle2 size={18} />
          Recovery Actions
        </Link>
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span
            className={
              backendHealthy
                ? "status-dot status-online"
                : "status-dot status-offline"
            }
          />

          <div>
            <div className="system-status-title">
              Backend
            </div>

            <div className="system-status-value">
              {backendHealthy
                ? "Connected"
                : "Disconnected"}
            </div>
          </div>
        </div>

        <div className="version">
          RazorRecover AI · v0.1.0
        </div>
      </div>
    </aside>
  );
}

export default function Dashboard() {
  const [queue, setQueue] = useState<
    RecoveryQueueItem[]
  >([]);

  const [total, setTotal] = useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [backendHealthy, setBackendHealthy] =
    useState(false);

  async function loadDashboard() {
    setLoading(true);
    setError(null);

    try {
      const [
        queueResponse,
        health,
      ] = await Promise.all([
        getRecoveryQueue(500),
        getHealth(),
      ]);

      setQueue(queueResponse.items);
      setTotal(queueResponse.total);
      setBackendHealthy(
        health.status === "healthy",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load recovery dashboard.",
      );

      setBackendHealthy(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const metrics = useMemo(() => {
    const openCases = queue.filter(
      (item) => item.status === "OPEN",
    ).length;

    const targetedCases = queue.filter(
      (item) =>
        item.targeted_by_capacity_policy,
    ).length;

    const expectedRecovery =
      queue.reduce(
        (sum, item) =>
          sum +
          item.expected_recovery_value,
        0,
      );

    const p1Cases = queue.filter(
      (item) =>
        item.priority_band === "P1_HIGH",
    ).length;

    const p2Cases = queue.filter(
      (item) =>
        item.priority_band === "P2",
    ).length;

    const p3Cases = queue.filter(
      (item) =>
        item.priority_band === "P3",
    ).length;

    const p4Cases = queue.filter(
      (item) =>
        item.priority_band === "P4",
    ).length;

    return {
      openCases,
      targetedCases,
      expectedRecovery,
      p1Cases,
      p2Cases,
      p3Cases,
      p4Cases,
    };
  }, [queue]);

  return (
    <div className="app-shell">
      <DashboardSidebar
        backendHealthy={backendHealthy}
      />

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="eyebrow">
              RECOVERY OPERATIONS
            </div>

            <h1>
              Admin Dashboard
            </h1>

            <p>
              Monitor AI-driven recovery
              decisions, priorities, and
              execution activity.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={() =>
              void loadDashboard()
            }
            disabled={loading}
          >
            <RefreshCw
              size={16}
              className={
                loading ? "spin" : ""
              }
            />

            Refresh
          </button>
        </header>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={18} />

            <div>
              <strong>
                Unable to load dashboard
              </strong>

              <span>
                {error}
              </span>
            </div>
          </div>
        )}

        <section className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon">
              <Activity size={20} />
            </div>

            <div className="metric-label">
              Open Recovery Cases
            </div>

            <div className="metric-value">
              {loading
                ? "—"
                : metrics.openCases}
            </div>

            <div className="metric-detail">
              {total.toLocaleString(
                "en-IN",
              )}{" "}
              total cases
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">
              <Target size={20} />
            </div>

            <div className="metric-label">
              Targeted Cases
            </div>

            <div className="metric-value">
              {loading
                ? "—"
                : metrics.targetedCases}
            </div>

            <div className="metric-detail">
              5% locked capacity policy
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">
              <CircleDollarSign size={20} />
            </div>

            <div className="metric-label">
              Expected Recovery
            </div>

            <div className="metric-value metric-currency">
              {loading
                ? "—"
                : formatCurrency(
                    metrics.expectedRecovery,
                  )}
            </div>

            <div className="metric-detail">
              Current queue
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">
              <AlertTriangle size={20} />
            </div>

            <div className="metric-label">
              High Priority
            </div>

            <div className="metric-value">
              {loading
                ? "—"
                : metrics.p1Cases}
            </div>

            <div className="metric-detail">
              Human approval required
            </div>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel queue-panel">
            <div className="panel-header">
              <div>
                <h2>
                  Recovery Queue
                </h2>

                <p>
                  Ranked by expected
                  recovery value
                </p>
              </div>

              <Link
                to="/recovery-queue"
                className="queue-count"
              >
                View all
              </Link>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>CASE</th>
                    <th>
                      AMOUNT AT RISK
                    </th>
                    <th>
                      PROBABILITY
                    </th>
                    <th>
                      EXPECTED RECOVERY
                    </th>
                    <th>
                      PRIORITY
                    </th>
                    <th>ACTION</th>
                    <th>STATUS</th>
                  </tr>
                </thead>

                <tbody>
                  {loading && (
                    <tr>
                      <td
                        colSpan={7}
                        className="table-message"
                      >
                        Loading recovery
                        queue...
                      </td>
                    </tr>
                  )}

                  {!loading &&
                    queue.length === 0 && (
                      <tr>
                        <td
                          colSpan={7}
                          className="table-message"
                        >
                          No recovery
                          cases found.
                        </td>
                      </tr>
                    )}

                  {!loading &&
                    queue
                      .slice(0, 10)
                      .map((item) => (
                        <tr
                          key={
                            item.recovery_case_id
                          }
                          className={
                            item.targeted_by_capacity_policy
                              ? "targeted-row"
                              : ""
                          }
                        >
                          <td>
                            <Link
                              to={`/recovery-cases/${item.recovery_case_id}`}
                              className="case-link"
                            >
                              #
                              {
                                item.recovery_case_id
                              }
                            </Link>

                            <div className="customer-id">
                              Customer{" "}
                              {
                                item.customer_id
                              }
                            </div>
                          </td>

                          <td className="amount-cell">
                            {formatCurrency(
                              item.amount_at_risk,
                            )}
                          </td>

                          <td>
                            <div className="probability">
                              <span>
                                {formatPercentage(
                                  item.recovery_probability,
                                )}
                              </span>

                              <div className="probability-bar">
                                <div
                                  className="probability-fill"
                                  style={{
                                    width: `${Math.min(
                                      item.recovery_probability *
                                        100,
                                      100,
                                    )}%`,
                                  }}
                                />
                              </div>
                            </div>
                          </td>

                          <td className="expected-cell">
                            {formatCurrency(
                              item.expected_recovery_value,
                            )}
                          </td>

                          <td>
                            <span
                              className={priorityClass(
                                item.priority_band,
                              )}
                            >
                              {
                                item.priority_band
                              }
                            </span>
                          </td>

                          <td>
                            <span
                              className={actionClass(
                                item.recommended_action,
                              )}
                            >
                              {item.recommended_action.replaceAll(
                                "_",
                                " ",
                              )}
                            </span>
                          </td>

                          <td>
                            <div className="status-cell">
                              <span className="status-badge">
                                {item.status}
                              </span>

                              {item.targeted_by_capacity_policy && (
                                <span className="targeted-badge">
                                  TARGETED
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="panel priority-panel">
            <div className="panel-header">
              <div>
                <h2>
                  Priority Mix
                </h2>

                <p>
                  Current recovery queue
                </p>
              </div>
            </div>

            <div className="priority-list">
              <div className="priority-row">
                <span className="priority-dot dot-p1" />
                <span>
                  P1 High
                </span>
                <strong>
                  {metrics.p1Cases}
                </strong>
              </div>

              <div className="priority-row">
                <span className="priority-dot dot-p2" />
                <span>
                  P2 Standard
                </span>
                <strong>
                  {metrics.p2Cases}
                </strong>
              </div>

              <div className="priority-row">
                <span className="priority-dot dot-p3" />
                <span>
                  P3 Low Cost
                </span>
                <strong>
                  {metrics.p3Cases}
                </strong>
              </div>

              <div className="priority-row">
                <span className="priority-dot dot-p4" />
                <span>
                  P4 Monitor
                </span>
                <strong>
                  {metrics.p4Cases}
                </strong>
              </div>
            </div>

            <div className="policy-card">
              <div className="policy-icon">
                <ShieldCheck size={18} />
              </div>

              <div>
                <div className="policy-title">
                  Locked Policy
                </div>

                <div className="policy-value">
                  TOP_EXPECTED_RECOVERY_VALUE
                </div>

                <div className="policy-description">
                  Top 5% targeted using
                  validation-only policy
                  selection.
                </div>
              </div>
            </div>

            <div className="dashboard-note">
              <ArrowUpRight size={16} />

              <span>
                Higher expected recovery
                value receives higher
                operational priority.
              </span>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}