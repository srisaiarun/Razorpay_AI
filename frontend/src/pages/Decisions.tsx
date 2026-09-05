import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Loader2,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import ManagementSidebar from "../components/ManagementSidebar";

import { getAllDecisions } from "../services/api";
import type { AdminDecision } from "../types/recovery";

function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(value);
}

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function decisionClass(decision: string) {
  switch (decision) {
    case "HIGH_PRIORITY_RECOVERY":
      return "status-pill status-danger";

    case "STANDARD_RECOVERY":
      return "status-pill status-success";

    case "LOW_COST_RECOVERY":
      return "status-pill status-info";

    case "MONITOR":
      return "status-pill status-warning";

    case "NO_ACTION":
      return "status-pill status-neutral";

    default:
      return "status-pill status-neutral";
  }
}

function actionClass(status: string | null) {
  switch (status) {
    case "COMPLETED":
      return "status-pill status-success";

    case "PENDING":
      return "status-pill status-warning";

    case "PENDING_APPROVAL":
      return "status-pill status-warning";

    case "FAILED":
      return "status-pill status-danger";

    default:
      return "status-pill status-neutral";
  }
}

function caseClass(status: string) {
  switch (status) {
    case "RECOVERED":
      return "status-pill status-success";

    case "OPEN":
      return "status-pill status-warning";

    case "FAILED":
      return "status-pill status-danger";

    default:
      return "status-pill status-neutral";
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function Decisions() {
  const navigate = useNavigate();

  const [decisions, setDecisions] = useState<AdminDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState("ALL");

  async function loadDecisions(isRefresh = false) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      const data = await getAllDecisions();

      setDecisions(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load decisions.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadDecisions();
  }, []);

  const filteredDecisions = useMemo(() => {
    if (filter === "ALL") {
      return decisions;
    }

    return decisions.filter(
      (item) => item.decision === filter,
    );
  }, [decisions, filter]);

  const statistics = useMemo(() => {
    const total = decisions.length;

    const highPriority = decisions.filter(
      (item) =>
        item.decision === "HIGH_PRIORITY_RECOVERY",
    ).length;

    const pendingApproval = decisions.filter(
      (item) =>
        item.requires_human_approval &&
        item.action_status !== "COMPLETED",
    ).length;

    const recovered = decisions.filter(
      (item) => item.case_status === "RECOVERED",
    ).length;

    const expectedRecovery = decisions.reduce(
      (sum, item) =>
        sum + item.expected_recovery_amount,
      0,
    );

    return {
      total,
      highPriority,
      pendingApproval,
      recovered,
      expectedRecovery,
    };
  }, [decisions]);

  if (loading) {
    return (
      <div className="management-shell">
        <ManagementSidebar active="decisions" />
        <main className="management-main">
          <div className="page-container">
            <div className="loading-state">
          <Loader2 className="spin" size={22} />
              <span>Loading AI decisions...</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="management-shell">
      <ManagementSidebar active="decisions" />
      <main className="management-main">
        <div className="page-container">
        {/* Header */}

        <div className="page-header">
          <div>
            <Link
              to="/management"
              className="back-link"
            >
              <ArrowLeft size={16} />
              Dashboard
            </Link>

            <div className="eyebrow">
              AI DECISION INTELLIGENCE
            </div>

            <h1>Recovery Decisions</h1>

            <p className="page-description">
              Review AI-generated recovery decisions,
              confidence, policy controls, and resulting
              recovery actions.
            </p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadDecisions(true)}
            disabled={refreshing}
          >
            {refreshing ? (
              <Loader2
                size={16}
                className="spin"
              />
            ) : (
              <RefreshCw size={16} />
            )}

            Refresh
          </button>
        </div>

        {/* Error */}

        {error && (
          <div className="error-banner">
            <XCircle size={18} />
            <span>{error}</span>

            <button
              type="button"
              onClick={() => void loadDecisions()}
            >
              Retry
            </button>
          </div>
        )}

        {/* Statistics */}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <BrainCircuit size={20} />
            </div>

            <div>
              <div className="stat-label">
                Total Decisions
              </div>

              <div className="stat-value">
                {statistics.total}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck size={20} />
            </div>

            <div>
              <div className="stat-label">
                High Priority
              </div>

              <div className="stat-value">
                {statistics.highPriority}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Clock3 size={20} />
            </div>

            <div>
              <div className="stat-label">
                Awaiting Approval
              </div>

              <div className="stat-value">
                {statistics.pendingApproval}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CheckCircle2 size={20} />
            </div>

            <div>
              <div className="stat-label">
                Recovered
              </div>

              <div className="stat-value">
                {statistics.recovered}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              £
            </div>

            <div>
              <div className="stat-label">
                Expected Recovery
              </div>

              <div className="stat-value stat-value-money">
                {money(statistics.expectedRecovery)}
              </div>
            </div>
          </div>
        </div>

        {/* Filter */}

        <div className="section-card">
          <div className="section-header">
            <div>
              <h2>AI Decisions</h2>

              <p>
                {filteredDecisions.length} decision
                {filteredDecisions.length === 1
                  ? ""
                  : "s"} displayed
              </p>
            </div>

            <div className="filter-group">
              <button
                type="button"
                className={
                  filter === "ALL"
                    ? "filter-button active"
                    : "filter-button"
                }
                onClick={() => setFilter("ALL")}
              >
                All
              </button>

              <button
                type="button"
                className={
                  filter ===
                  "HIGH_PRIORITY_RECOVERY"
                    ? "filter-button active"
                    : "filter-button"
                }
                onClick={() =>
                  setFilter(
                    "HIGH_PRIORITY_RECOVERY",
                  )
                }
              >
                High Priority
              </button>

              <button
                type="button"
                className={
                  filter === "STANDARD_RECOVERY"
                    ? "filter-button active"
                    : "filter-button"
                }
                onClick={() =>
                  setFilter("STANDARD_RECOVERY")
                }
              >
                Standard
              </button>

              <button
                type="button"
                className={
                  filter === "LOW_COST_RECOVERY"
                    ? "filter-button active"
                    : "filter-button"
                }
                onClick={() =>
                  setFilter("LOW_COST_RECOVERY")
                }
              >
                Low Cost
              </button>

              <button
                type="button"
                className={
                  filter === "MONITOR"
                    ? "filter-button active"
                    : "filter-button"
                }
                onClick={() =>
                  setFilter("MONITOR")
                }
              >
                Monitor
              </button>
            </div>
          </div>

          {/* Table */}

          {filteredDecisions.length === 0 ? (
            <div className="table-message">
              <BrainCircuit size={28} />

              <h3>No decisions found</h3>

              <p>
                There are no persisted decisions for
                the selected filter.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Decision</th>
                    <th>Case</th>
                    <th>Customer</th>
                    <th>Confidence</th>
                    <th>Expected Recovery</th>
                    <th>Approval</th>
                    <th>Action</th>
                    <th>Case Status</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {filteredDecisions.map(
                    (item) => (
                      <tr
                        key={item.id}
                        className="clickable-row"
                        onClick={() =>
                          navigate(
                            `/management/recovery-cases/${item.recovery_case_id}`,
                          )
                        }
                      >
                        <td>
                          <span
                            className={decisionClass(
                              item.decision,
                            )}
                          >
                            {item.decision.replaceAll(
                              "_",
                              " ",
                            )}
                          </span>
                        </td>

                        <td>
                          <span className="case-id">
                            #{item.recovery_case_id}
                          </span>
                        </td>

                        <td>
                          <span className="customer-id">
                            #{item.customer_id}
                          </span>
                        </td>

                        <td>
                          <strong>
                            {percent(
                              item.confidence,
                            )}
                          </strong>
                        </td>

                        <td>
                          <strong>
                            {money(
                              item.expected_recovery_amount,
                            )}
                          </strong>
                        </td>

                        <td>
                          {item.requires_human_approval ? (
                            <span className="approval-required">
                              <ShieldCheck
                                size={14}
                              />
                              Required
                            </span>
                          ) : (
                            <span className="approval-not-required">
                              Not required
                            </span>
                          )}
                        </td>

                        <td>
                          {item.action_status ? (
                            <span
                              className={actionClass(
                                item.action_status,
                              )}
                            >
                              {item.action_status.replaceAll(
                                "_",
                                " ",
                              )}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>

                        <td>
                          <span
                            className={caseClass(
                              item.case_status,
                            )}
                          >
                            {item.case_status}
                          </span>
                        </td>

                        <td>
                          <span className="date-cell">
                            {formatDate(
                              item.created_at,
                            )}
                          </span>
                        </td>

                        <td>
                          <ChevronRight
                            size={18}
                            className="row-chevron"
                          />
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Decision explanation */}

        <div className="info-card">
          <div className="info-card-icon">
            <BrainCircuit size={20} />
          </div>

          <div>
            <h3>How AI decisions work</h3>

            <p>
              Recovery probability comes from the
              calibrated recovery model. The decision
              engine combines probability and amount at
              risk to calculate expected recovery value,
              assigns a priority band, and determines the
              recommended recovery action.
            </p>

            <p>
              Production targeting follows the locked
              validation-only capacity policy.
            </p>
          </div>
        </div>
        </div>
      </main>
    </div>
  );
}