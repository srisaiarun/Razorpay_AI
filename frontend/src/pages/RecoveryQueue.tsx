import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  ArrowLeft,
  CheckCircle2,
  LayoutDashboard,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Users,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

import {
  getHealth,
  getRecoveryQueue,
} from "../services/api";

import type {
  PriorityBand,
  RecoveryActionType,
  RecoveryQueueItem,
  RecoveryStatus,
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

function priorityClass(
  priority: string,
): string {
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

function actionClass(
  action: string,
): string {
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

function Sidebar() {
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
          className="nav-item"
        >
          <LayoutDashboard size={18} />
          Dashboard
        </Link>

        <Link
          to="/recovery-queue"
          className="nav-item nav-item-active"
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
          <span className="status-dot status-online" />

          <div>
            <div className="system-status-title">
              Backend
            </div>

            <div className="system-status-value">
              Connected
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

export default function RecoveryQueue() {
  const [queue, setQueue] =
    useState<RecoveryQueueItem[]>([]);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [search, setSearch] =
    useState("");

  const [priority, setPriority] =
    useState<"ALL" | PriorityBand>("ALL");

  const [action, setAction] =
    useState<
      "ALL" | RecoveryActionType
    >("ALL");

  const [status, setStatus] =
    useState<
      "ALL" | RecoveryStatus
    >("ALL");

  const [targetedOnly, setTargetedOnly] =
    useState(false);

  const [backendHealthy, setBackendHealthy] =
    useState(false);

  async function loadQueue() {
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
          : "Unable to load recovery queue.",
      );

      setBackendHealthy(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQueue();
  }, []);

  const filteredQueue =
    useMemo(() => {
      const query =
        search.trim().toLowerCase();

      return queue.filter((item) => {
        const matchesSearch =
          !query ||
          String(
            item.recovery_case_id,
          ).includes(query) ||
          String(
            item.customer_id,
          ).includes(query);

        const matchesPriority =
          priority === "ALL" ||
          item.priority_band ===
            priority;

        const matchesAction =
          action === "ALL" ||
          item.recommended_action ===
            action;

        const matchesStatus =
          status === "ALL" ||
          item.status === status;

        const matchesTargeted =
          !targetedOnly ||
          item.targeted_by_capacity_policy;

        return (
          matchesSearch &&
          matchesPriority &&
          matchesAction &&
          matchesStatus &&
          matchesTargeted
        );
      });
    }, [
      queue,
      search,
      priority,
      action,
      status,
      targetedOnly,
    ]);

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="eyebrow">
              RECOVERY OPERATIONS
            </div>

            <h1>
              Recovery Queue
            </h1>

            <p>
              Review AI-ranked recovery
              opportunities and
              operational priorities.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={() =>
              void loadQueue()
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

        <div className="queue-back">
          <Link to="/">
            <ArrowLeft size={15} />
            Back to dashboard
          </Link>
        </div>

        {error && (
          <div className="error-banner">
            <Activity size={18} />

            <div>
              <strong>
                Unable to load recovery
                queue
              </strong>

              <span>
                {error}
              </span>
            </div>
          </div>
        )}

        <section className="queue-toolbar panel">
          <div className="queue-search">
            <Search size={17} />

            <input
              type="text"
              placeholder="Search case or customer ID..."
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
            />
          </div>

          <div className="filter-group">
            <SlidersHorizontal
              size={16}
            />

            <select
              value={priority}
              onChange={(event) =>
                setPriority(
                  event.target.value as
                    | "ALL"
                    | PriorityBand,
                )
              }
            >
              <option value="ALL">
                All priorities
              </option>

              <option value="P1_HIGH">
                P1 High
              </option>

              <option value="P2">
                P2 Standard
              </option>

              <option value="P3">
                P3 Low Cost
              </option>

              <option value="P4">
                P4 Monitor
              </option>
            </select>
          </div>

          <div className="filter-group">
            <select
              value={action}
              onChange={(event) =>
                setAction(
                  event.target.value as
                    | "ALL"
                    | RecoveryActionType,
                )
              }
            >
              <option value="ALL">
                All actions
              </option>

              <option value="HIGH_PRIORITY_RECOVERY">
                High Priority Recovery
              </option>

              <option value="STANDARD_RECOVERY">
                Standard Recovery
              </option>

              <option value="LOW_COST_RECOVERY">
                Low Cost Recovery
              </option>

              <option value="MONITOR">
                Monitor
              </option>

              <option value="NO_ACTION">
                No Action
              </option>
            </select>
          </div>

          <div className="filter-group">
            <select
              value={status}
              onChange={(event) =>
                setStatus(
                  event.target.value as
                    | "ALL"
                    | RecoveryStatus,
                )
              }
            >
              <option value="ALL">
                All status
              </option>

              <option value="OPEN">
                Open
              </option>

              <option value="RECOVERED">
                Recovered
              </option>

              <option value="CLOSED">
                Closed
              </option>
            </select>
          </div>

          <label className="targeted-filter">
            <input
              type="checkbox"
              checked={targetedOnly}
              onChange={(event) =>
                setTargetedOnly(
                  event.target.checked,
                )
              }
            />

            Targeted only
          </label>
        </section>

        <section className="queue-summary">
          <div>
            <strong>
              {filteredQueue.length}
            </strong>{" "}
            matching cases
          </div>

          <div>
            {total.toLocaleString(
              "en-IN",
            )}{" "}
            total cases
          </div>

          <div>
            Backend:{" "}
            <strong>
              {backendHealthy
                ? "Connected"
                : "Disconnected"}
            </strong>
          </div>
        </section>

        <section className="panel queue-panel-full">
          <div className="panel-header">
            <div>
              <h2>
                AI Recovery Queue
              </h2>

              <p>
                Ranked by expected
                recovery value
              </p>
            </div>

            <div className="queue-count">
              5% locked capacity
              policy
            </div>
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
                  filteredQueue.length ===
                    0 && (
                    <tr>
                      <td
                        colSpan={7}
                        className="table-message"
                      >
                        No cases match
                        the selected
                        filters.
                      </td>
                    </tr>
                  )}

                {!loading &&
                  filteredQueue.map(
                    (item) => (
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
                    ),
                  )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}