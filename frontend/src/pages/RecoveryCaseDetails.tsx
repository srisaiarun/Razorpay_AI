import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";

import {
  approveRecoveryAction,
  createRecoveryDecision,
  executeRecoveryAction,
  getRecoveryActions,
  getRecoveryAudit,
  getRecoveryCase,
  getRecoveryDecision,
} from "../services/api";

import type {
  AuditLog,
  RecoveryAction,
  RecoveryCase,
  RecoveryDecisionResponse,
} from "../types/recovery";

function money(value: number) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    minimumFractionDigits: 2,
  }).format(value);
}

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function statusClass(status: string) {
  switch (status) {
    case "RECOVERED":
    case "COMPLETED":
      return "status-pill status-success";

    case "PENDING_APPROVAL":
      return "status-pill status-warning";

    case "PENDING":
      return "status-pill status-info";

    case "FAILED":
      return "status-pill status-danger";

    default:
      return "status-pill status-neutral";
  }
}


export default function RecoveryCaseDetails() {
  const { recoveryCaseId } = useParams();
  const navigate = useNavigate();

  const caseId = Number(recoveryCaseId);

  const [recoveryCase, setRecoveryCase] =
    useState<RecoveryCase | null>(null);

  const [decision, setDecision] =
    useState<RecoveryDecisionResponse | null>(null);

  const [actions, setActions] =
    useState<RecoveryAction[]>([]);

  const [auditLogs, setAuditLogs] =
    useState<AuditLog[]>([]);

  const [loading, setLoading] = useState(true);

  const [working, setWorking] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [approvalReason, setApprovalReason] = useState(
    "Approved for recovery execution."
  );

  async function loadCase() {
    if (!Number.isInteger(caseId) || caseId <= 0) {
      setError("Invalid recovery case ID.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [
        caseData,
        decisionData,
        actionData,
        auditData,
      ] = await Promise.all([
        getRecoveryCase(caseId),
        getRecoveryDecision(caseId).catch(() => null),
        getRecoveryActions(caseId),
        getRecoveryAudit(caseId),
      ]);

      setRecoveryCase(caseData);
      setDecision(decisionData);
      setActions(actionData);
      setAuditLogs(auditData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load recovery case."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCase();
  }, [caseId]);

  async function handleCreateDecision() {
    try {
      setWorking(true);
      setError(null);

      await createRecoveryDecision(caseId);

      await loadCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to create recovery decision."
      );
    } finally {
      setWorking(false);
    }
  }

  async function handleApprove(actionId: number) {
    try {
      setWorking(true);
      setError(null);

      await approveRecoveryAction(actionId, {
        approver_id: "admin_demo",
        approval_reason: approvalReason.trim() || null,
      });

      await loadCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to approve recovery action."
      );
    } finally {
      setWorking(false);
    }
  }

  async function handleExecute(actionId: number) {
    try {
      setWorking(true);
      setError(null);

      await executeRecoveryAction(actionId);

      await loadCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to execute recovery action."
      );
    } finally {
      setWorking(false);
    }
  }

  if (loading) {
    return (
      <div className="page-shell">
        <div className="loading-state">
          <Loader2 className="spin" size={22} />
          <span>Loading recovery case...</span>
        </div>
      </div>
    );
  }

  if (error && !recoveryCase) {
    return (
      <div className="page-shell">
        <div className="error-panel">
          <CircleAlert size={28} />

          <h2>Unable to load recovery case</h2>

          <p>{error}</p>

          <button
            className="secondary-button"
            onClick={() => navigate("/recovery-queue")}
          >
            <ArrowLeft size={16} />
            Back to Recovery Queue
          </button>
        </div>
      </div>
    );
  }

  if (!recoveryCase) {
    return null;
  }

  const latestAction =
    actions.length > 0
      ? actions[actions.length - 1]
      : null;

  return (
    <div className="page-shell">
      <div className="page-container">
        {/* -------------------------------------------------- */}
        {/* HEADER */}
        {/* -------------------------------------------------- */}

        <div className="case-header">
          <div>
            <Link
              to="/recovery-queue"
              className="back-link"
            >
              <ArrowLeft size={16} />
              Recovery Queue
            </Link>

            <div className="eyebrow">
              RAZORRECOVER AI
            </div>

            <h1>
              Recovery Case #{recoveryCase.id}
            </h1>

            <p className="page-subtitle">
              Customer #{recoveryCase.customer_id}
              {" • "}
              Transaction #{recoveryCase.transaction_id}
            </p>
          </div>

          <div>
            <span
              className={statusClass(
                recoveryCase.status
              )}
            >
              {recoveryCase.status}
            </span>
          </div>
        </div>

        {error && (
          <div className="inline-error">
            <CircleAlert size={16} />
            {error}
          </div>
        )}

        {/* -------------------------------------------------- */}
        {/* CASE OVERVIEW */}
        {/* -------------------------------------------------- */}

        <section className="dashboard-card">
          <div className="section-heading">
            <div>
              <div className="section-kicker">
                CASE OVERVIEW
              </div>

              <h2>Recovery exposure</h2>
            </div>

            <FileText size={20} />
          </div>

          <div className="metric-grid">
            <div className="metric-card">
              <span>Amount at Risk</span>
              <strong>
                {money(
                  Number(
                    recoveryCase.amount_at_risk
                  )
                )}
              </strong>
            </div>

            <div className="metric-card">
              <span>Recovery Probability</span>
              <strong>
                {percent(
                  recoveryCase.recovery_probability
                )}
              </strong>
            </div>

            <div className="metric-card">
              <span>Risk Score</span>
              <strong>
                {percent(
                  recoveryCase.risk_score
                )}
              </strong>
            </div>

            <div className="metric-card">
              <span>Attempts</span>
              <strong>
                {recoveryCase.attempt_count}
              </strong>
            </div>
          </div>

          <div className="case-meta-grid">
            <div>
              <span>Failure Class</span>
              <strong>
                {recoveryCase.failure_class}
              </strong>
            </div>

            <div>
              <span>Created</span>
              <strong>
                {formatDate(
                  recoveryCase.created_at
                )}
              </strong>
            </div>

            <div>
              <span>Next Action</span>
              <strong>
                {formatDate(
                  recoveryCase.next_action_at
                )}
              </strong>
            </div>

            <div>
              <span>Resolved</span>
              <strong>
                {formatDate(
                  recoveryCase.resolved_at
                )}
              </strong>
            </div>
          </div>
        </section>

        {/* -------------------------------------------------- */}
        {/* AI DECISION */}
        {/* -------------------------------------------------- */}

        <section className="dashboard-card">
          <div className="section-heading">
            <div>
              <div className="section-kicker">
                AI DECISION
              </div>

              <h2>Recovery recommendation</h2>
            </div>

            {decision && (
              <span
                className={statusClass(
                  decision.action_status
                )}
              >
                {decision.action_status}
              </span>
            )}
          </div>

          {!decision ? (
            <div className="empty-state">
              <CircleAlert size={24} />

              <h3>No decision created yet</h3>

              <p>
                Run the deterministic recovery decision
                engine for this case.
              </p>

              <button
                className="primary-button"
                disabled={working}
                onClick={handleCreateDecision}
              >
                {working ? (
                  <Loader2
                    size={16}
                    className="spin"
                  />
                ) : (
                  <Play size={16} />
                )}

                Create AI Decision
              </button>
            </div>
          ) : (
            <>
              <div className="decision-highlight">
                <div>
                  <span>Recommended Action</span>

                  <strong>
                    {decision.decision}
                  </strong>
                </div>

                <div>
                  <span>Confidence</span>

                  <strong>
                    {percent(decision.confidence)}
                  </strong>
                </div>

                <div>
                  <span>Expected Recovery</span>

                  <strong>
                    {money(
                      Number(
                        decision.expected_recovery_amount
                      )
                    )}
                  </strong>
                </div>
              </div>

              <div className="reasoning-box">
                <div className="reasoning-title">
                  <ShieldCheck size={17} />
                  AI reasoning
                </div>

                <p>
                  {decision.reasoning_summary}
                </p>
              </div>

              <div className="policy-grid">
                <div>
                  <span>Policy</span>
                  <strong>
                    {decision.policy_status}
                  </strong>
                </div>

                <div>
                  <span>Human Approval</span>
                  <strong>
                    {decision.requires_human_approval
                      ? "Required"
                      : "Not Required"}
                  </strong>
                </div>

                <div>
                  <span>Action Type</span>
                  <strong>
                    {decision.action_type}
                  </strong>
                </div>

                <div>
                  <span>Created</span>
                  <strong>
                    {formatDate(
                      decision.created_at
                    )}
                  </strong>
                </div>
              </div>
            </>
          )}
        </section>

        {/* -------------------------------------------------- */}
        {/* RECOVERY ACTION */}
        {/* -------------------------------------------------- */}

        <section className="dashboard-card">
          <div className="section-heading">
            <div>
              <div className="section-kicker">
                RECOVERY ACTION
              </div>

              <h2>Operational workflow</h2>
            </div>

            {latestAction && (
              <span
                className={statusClass(
                  latestAction.status
                )}
              >
                {latestAction.status}
              </span>
            )}
          </div>

          {!latestAction ? (
            <div className="empty-state">
              <Clock3 size={24} />

              <h3>No recovery action</h3>

              <p>
                A recovery action will appear after an
                AI decision is created.
              </p>
            </div>
          ) : (
            <>
              <div className="action-summary">
                <div>
                  <span>Action</span>

                  <strong>
                    {latestAction.action_type}
                  </strong>
                </div>

                <div>
                  <span>Amount</span>

                  <strong>
                    {money(
                      Number(
                        latestAction.amount
                      )
                    )}
                  </strong>
                </div>

                <div>
                  <span>Attempt</span>

                  <strong>
                    #{latestAction.attempt_number}
                  </strong>
                </div>

                <div>
                  <span>Created</span>

                  <strong>
                    {formatDate(
                      latestAction.created_at
                    )}
                  </strong>
                </div>
              </div>

              {latestAction.status ===
                "PENDING_APPROVAL" && (
                <div className="approval-panel">
                  <div className="approval-icon">
                    <UserCheck size={20} />
                  </div>

                  <div className="approval-content">
                    <h3>
                      Human approval required
                    </h3>

                    <p>
                      This action cannot be executed
                      until an authorized reviewer approves
                      it.
                    </p>

                    <label>
                      Approval reason

                      <textarea
                        value={approvalReason}
                        onChange={(event) =>
                          setApprovalReason(
                            event.target.value
                          )
                        }
                        rows={3}
                      />
                    </label>

                    <button
                      className="primary-button"
                      disabled={working}
                      onClick={() =>
                        handleApprove(
                          latestAction.id
                        )
                      }
                    >
                      {working ? (
                        <Loader2
                          size={16}
                          className="spin"
                        />
                      ) : (
                        <UserCheck size={16} />
                      )}

                      Approve Recovery Action
                    </button>
                  </div>
                </div>
              )}

              {latestAction.status === "PENDING" && (
                <div className="execution-panel">
                  <div>
                    <CheckCircle2 size={22} />

                    <div>
                      <h3>
                        Action authorized
                      </h3>

                      <p>
                        The recovery action has been
                        approved and is ready for execution.
                      </p>
                    </div>
                  </div>

                  <button
                    className="primary-button"
                    disabled={working}
                    onClick={() =>
                      handleExecute(
                        latestAction.id
                      )
                    }
                  >
                    {working ? (
                      <Loader2
                        size={16}
                        className="spin"
                      />
                    ) : (
                      <Play size={16} />
                    )}

                    Execute Recovery
                  </button>
                </div>
              )}

              {latestAction.status === "COMPLETED" && (
                <div className="success-panel">
                  <CheckCircle2 size={22} />

                  <div>
                    <h3>
                      Recovery completed successfully
                    </h3>

                    <p>
                      The simulated recovery action was
                      executed and the recovery case was
                      marked recovered.
                    </p>

                    <span>
                      Completed{" "}
                      {formatDate(
                        latestAction.completed_at
                      )}
                    </span>
                  </div>
                </div>
              )}

              {latestAction.status === "FAILED" && (
                <div className="failure-panel">
                  <XCircle size={22} />

                  <div>
                    <h3>
                      Recovery action failed
                    </h3>

                    <p>
                      {latestAction.failure_reason ??
                        "No failure reason was recorded."}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        {/* -------------------------------------------------- */}
        {/* AUDIT TIMELINE */}
        {/* -------------------------------------------------- */}

        <section className="dashboard-card">
          <div className="section-heading">
            <div>
              <div className="section-kicker">
                AUDIT TRAIL
              </div>

              <h2>Decision and execution history</h2>
            </div>

            <ShieldCheck size={20} />
          </div>

          {auditLogs.length === 0 ? (
            <div className="empty-state">
              <Clock3 size={24} />

              <h3>No audit events</h3>

              <p>
                Audit events will appear as the recovery
                workflow progresses.
              </p>
            </div>
          ) : (
            <div className="timeline">
              {auditLogs.map((audit) => (
                <div
                  className="timeline-item"
                  key={audit.id}
                >
                  <div className="timeline-dot">
                    <CheckCircle2 size={14} />
                  </div>

                  <div className="timeline-content">
                    <div className="timeline-top">
                      <strong>
                        {audit.event_type}
                      </strong>

                      <span>
                        {formatDate(
                          audit.created_at
                        )}
                      </span>
                    </div>

                    <p>{audit.message}</p>

                    <div className="timeline-meta">
                      <span>
                        Actor: {audit.actor_type}
                      </span>

                      <span>
                        ID: {audit.actor_id}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}