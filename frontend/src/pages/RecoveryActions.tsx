import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import ManagementSidebar from "../components/ManagementSidebar";

import {
  approveRecoveryAction,
  executeRecoveryAction,
  getAllRecoveryActions,
} from "../services/api";

import type { RecoveryAction } from "../types/recovery";

function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(value);
}

function statusClass(status: string) {
  switch (status) {
    case "COMPLETED":
      return "status-pill status-success";

    case "PENDING":
      return "status-pill status-info";

    case "PENDING_APPROVAL":
      return "status-pill status-warning";

    case "FAILED":
      return "status-pill status-danger";

    default:
      return "status-pill status-neutral";
  }
}

function actionClass(action: string) {
  switch (action) {
    case "HIGH_PRIORITY_RECOVERY":
      return "status-pill status-danger";

    case "STANDARD_RECOVERY":
      return "status-pill status-success";

    case "LOW_COST_RECOVERY":
      return "status-pill status-info";

    default:
      return "status-pill status-neutral";
  }
}

function formatDate(
  value: string | null | undefined,
) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function RecoveryActions() {
  const navigate = useNavigate();

  const [actions, setActions] = useState<
    RecoveryAction[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState<
    number | null
  >(null);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState<
    string | null
  >(null);

  const [filter, setFilter] = useState("ALL");

  const [
    approvalReason,
    setApprovalReason,
  ] = useState(
    "Approved for recovery execution.",
  );

  async function loadActions(
    isRefresh = false,
  ) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      const data =
        await getAllRecoveryActions();

      setActions(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load recovery actions.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadActions();
  }, []);

  async function handleApprove(
    actionId: number,
  ) {
    try {
      setWorkingId(actionId);
      setError(null);

      await approveRecoveryAction(
        actionId,
        {
          approval_reason:
            approvalReason.trim() ||
            "Approved for recovery execution.",
        },
      );

      await loadActions(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to approve recovery action.",
      );
    } finally {
      setWorkingId(null);
    }
  }

  async function handleExecute(
    actionId: number,
  ) {
    try {
      setWorkingId(actionId);
      setError(null);

      await executeRecoveryAction(
        actionId,
      );

      await loadActions(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to execute recovery action.",
      );
    } finally {
      setWorkingId(null);
    }
  }

  const filteredActions = useMemo(() => {
    if (filter === "ALL") {
      return actions;
    }

    return actions.filter(
      (action) => action.status === filter,
    );
  }, [actions, filter]);

  const statistics = useMemo(() => {
    const pendingApproval =
      actions.filter(
        (action) =>
          action.status ===
          "PENDING_APPROVAL",
      ).length;

    const pending =
      actions.filter(
        (action) =>
          action.status === "PENDING",
      ).length;

    const completed =
      actions.filter(
        (action) =>
          action.status === "COMPLETED",
      ).length;

    const failed =
      actions.filter(
        (action) =>
          action.status === "FAILED",
      ).length;

    const totalAmount =
      actions.reduce(
        (sum, action) =>
          sum + action.amount,
        0,
      );

    return {
      pendingApproval,
      pending,
      completed,
      failed,
      totalAmount,
    };
  }, [actions]);

  if (loading) {
    return (
      <div className="management-shell">
        <ManagementSidebar active="actions" />
        <main className="management-main">
          <div className="page-container">
            <div className="loading-state">
          <Loader2
            size={22}
            className="spin"
          />

              <span>
                Loading recovery actions...
              </span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="management-shell">
      <ManagementSidebar active="actions" />
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
              RECOVERY OPERATIONS
            </div>

            <h1>Recovery Actions</h1>

            <p className="page-description">
              Review, approve, and execute AI-generated
              recovery actions.
            </p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() =>
              void loadActions(true)
            }
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
            <CircleAlert size={18} />

            <span>{error}</span>

            <button
              type="button"
              onClick={() =>
                void loadActions()
              }
            >
              Retry
            </button>
          </div>
        )}

        {/* Statistics */}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <ShieldCheck size={20} />
            </div>

            <div>
              <div className="stat-label">
                Awaiting Approval
              </div>

              <div className="stat-value">
                {
                  statistics.pendingApproval
                }
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Clock3 size={20} />
            </div>

            <div>
              <div className="stat-label">
                Ready to Execute
              </div>

              <div className="stat-value">
                {statistics.pending}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CheckCircle2 size={20} />
            </div>

            <div>
              <div className="stat-label">
                Completed
              </div>

              <div className="stat-value">
                {statistics.completed}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <XCircle size={20} />
            </div>

            <div>
              <div className="stat-label">
                Failed
              </div>

              <div className="stat-value">
                {statistics.failed}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              £
            </div>

            <div>
              <div className="stat-label">
                Action Value
              </div>

              <div className="stat-value stat-value-money">
                {money(
                  statistics.totalAmount,
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Approval reason */}

        <div className="section-card">
          <div className="section-header">
            <div>
              <h2>Admin Approval Settings</h2>

              <p>
                This reason is recorded in the
                approval workflow.
              </p>
            </div>
          </div>

          <div className="form-row">
            <label
              htmlFor="approval-reason"
              className="field-label"
            >
              Approval reason
            </label>

            <input
              id="approval-reason"
              className="text-input"
              value={approvalReason}
              onChange={(event) =>
                setApprovalReason(
                  event.target.value,
                )
              }
              maxLength={500}
            />
          </div>
        </div>

        {/* Actions */}

        <div className="section-card">
          <div className="section-header">
            <div>
              <h2>Recovery Action Queue</h2>

              <p>
                {filteredActions.length} action
                {filteredActions.length === 1
                  ? ""
                  : "s"} displayed
              </p>
            </div>

            <div className="filter-group">
              {[
                ["ALL", "All"],
                [
                  "PENDING_APPROVAL",
                  "Awaiting Approval",
                ],
                ["PENDING", "Ready"],
                ["COMPLETED", "Completed"],
                ["FAILED", "Failed"],
              ].map(
                ([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={
                      filter === value
                        ? "filter-button active"
                        : "filter-button"
                    }
                    onClick={() =>
                      setFilter(value)
                    }
                  >
                    {label}
                  </button>
                ),
              )}
            </div>
          </div>

          {filteredActions.length === 0 ? (
            <div className="table-message">
              <CheckCircle2 size={30} />

              <h3>
                No recovery actions
              </h3>

              <p>
                There are no actions matching
                this filter.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Case</th>
                    <th>Decision</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Attempt</th>
                    <th>Created</th>
                    <th>Completed</th>
                    <th>Operations</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredActions.map(
                    (action) => {
                      const working =
                        workingId ===
                        action.id;

                      return (
                        <tr
                          key={action.id}
                          className="clickable-row"
                          onClick={() =>
                            navigate(
                              `/management/recovery-cases/${action.recovery_case_id}`,
                            )
                          }
                        >
                          <td>
                            <strong>
                              #{action.id}
                            </strong>
                          </td>

                          <td>
                            <span className="case-id">
                              #
                              {
                                action.recovery_case_id
                              }
                            </span>
                          </td>

                          <td>
                            <span
                              className={actionClass(
                                action.action_type,
                              )}
                            >
                              {action.action_type.replaceAll(
                                "_",
                                " ",
                              )}
                            </span>
                          </td>

                          <td>
                            <strong>
                              {money(
                                action.amount,
                              )}
                            </strong>
                          </td>

                          <td>
                            <span
                              className={statusClass(
                                action.status,
                              )}
                            >
                              {action.status.replaceAll(
                                "_",
                                " ",
                              )}
                            </span>
                          </td>

                          <td>
                            {action.attempt_number}
                          </td>

                          <td>
                            {formatDate(
                              action.created_at,
                            )}
                          </td>

                          <td>
                            {formatDate(
                              action.completed_at,
                            )}
                          </td>

                          <td
                            onClick={(event) =>
                              event.stopPropagation()
                            }
                          >
                            <div className="action-buttons">
                              {action.status ===
                                "PENDING_APPROVAL" && (
                                <button
                                  type="button"
                                  className="primary-button small"
                                  disabled={working}
                                  onClick={() =>
                                    void handleApprove(
                                      action.id,
                                    )
                                  }
                                >
                                  {working ? (
                                    <Loader2
                                      size={14}
                                      className="spin"
                                    />
                                  ) : (
                                    <ShieldCheck
                                      size={14}
                                    />
                                  )}

                                  Approve
                                </button>
                              )}

                              {action.status ===
                                "PENDING" && (
                                <button
                                  type="button"
                                  className="primary-button small"
                                  disabled={working}
                                  onClick={() =>
                                    void handleExecute(
                                      action.id,
                                    )
                                  }
                                >
                                  {working ? (
                                    <Loader2
                                      size={14}
                                      className="spin"
                                    />
                                  ) : (
                                    <Play
                                      size={14}
                                    />
                                  )}

                                  Execute
                                </button>
                              )}

                              {action.status ===
                                "COMPLETED" && (
                                <span className="completed-label">
                                  <CheckCircle2
                                    size={15}
                                  />
                                  Done
                                </span>
                              )}

                              {action.status ===
                                "FAILED" && (
                                <span className="failed-label">
                                  <XCircle
                                    size={15}
                                  />
                                  Failed
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    },
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Workflow explanation */}

        <div className="info-card">
          <div className="info-card-icon">
            <ShieldCheck size={20} />
          </div>

          <div>
            <h3>
              Human-in-the-loop recovery control
            </h3>

            <p>
              AI decisions do not automatically execute
              approval-required recovery actions.
              An authorized reviewer must approve the
              action before it can execute.
            </p>

            <p>
              Every approval, blocked execution attempt,
              and successful execution is recorded in the
              recovery audit trail.
            </p>
          </div>
        </div>
        </div>
      </main>
    </div>
  );
}