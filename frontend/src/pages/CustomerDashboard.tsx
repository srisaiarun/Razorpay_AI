import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  CreditCard,
  LogOut,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from "lucide-react";

import "./CustomerDashboard.css";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getCurrentUser,
  getCustomerProfile,
  getCustomerRecoveryCases,
  getCustomerSummary,
  getCustomerTransactions,
  logout,
} from "../services/api";

import type {
  CustomerProfile,
  CustomerRecoveryCase,
  CustomerSummary,
  CustomerTransaction,
} from "../types/customer";

function formatCurrency(amount: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(amount || 0));
}

function formatDate(date: string | null) {
  if (!date) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));
}

function getStatusClass(status: string) {
  const normalized = status.toUpperCase();

  if (
    normalized === "SUCCESS" ||
    normalized === "SUCCEEDED" ||
    normalized === "RECOVERED" ||
    normalized === "COMPLETED"
  ) {
    return "customer-status customer-status-success";
  }

  if (
    normalized === "FAILED" ||
    normalized === "FAILURE"
  ) {
    return "customer-status customer-status-failed";
  }

  if (
    normalized === "OPEN" ||
    normalized === "PENDING" ||
    normalized === "PROCESSING"
  ) {
    return "customer-status customer-status-pending";
  }

  return "customer-status";
}

function getStatusLabel(status: string) {
  const normalized = status.toUpperCase();

  switch (normalized) {
    case "SUCCESS":
    case "SUCCEEDED":
      return "Successful";

    case "FAILED":
    case "FAILURE":
      return "Failed";

    case "RECOVERED":
      return "Recovered";

    case "COMPLETED":
      return "Completed";

    case "OPEN":
      return "Recovery in progress";

    case "PENDING":
      return "Pending";

    default:
      return status;
  }
}

export default function CustomerDashboard() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [summary, setSummary] = useState<CustomerSummary | null>(null);
  const [transactions, setTransactions] = useState<CustomerTransaction[]>([]);
  const [recoveryCases, setRecoveryCases] = useState<
    CustomerRecoveryCase[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async (isRefresh = false) => {
    try {
      setError(null);

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const user = await getCurrentUser();

      if (user.role !== "CUSTOMER") {
        logout();
        navigate("/customer/login", { replace: true });
        return;
      }

      const [
        customerProfile,
        customerSummary,
        customerTransactions,
        customerRecoveryCases,
      ] = await Promise.all([
        getCustomerProfile(),
        getCustomerSummary(),
        getCustomerTransactions(),
        getCustomerRecoveryCases(),
      ]);

      setProfile(customerProfile);
      setSummary(customerSummary);
      setTransactions(customerTransactions);
      setRecoveryCases(customerRecoveryCases);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load your customer dashboard.";

      setError(message);

      if (
        message.toLowerCase().includes("credentials") ||
        message.toLowerCase().includes("token") ||
        message.toLowerCase().includes("authentication") ||
        message.toLowerCase().includes("unauthorized")
      ) {
        logout();
        navigate("/customer/login", { replace: true });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const recentTransactions = useMemo(
    () => transactions.slice(0, 6),
    [transactions],
  );

  const recentRecoveryCases = useMemo(
    () => recoveryCases.slice(0, 4),
    [recoveryCases],
  );

  const recoveryRate = summary?.recovery_rate ?? 0;

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  if (loading) {
    return (
      <div className="customer-dashboard-page">
        <div className="customer-loading">
          <div className="customer-loading-spinner">
            <RefreshCw size={22} />
          </div>

          <h2>Loading your dashboard</h2>

          <p>
            We're securely retrieving your payment and recovery
            information.
          </p>
        </div>
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="customer-dashboard-page">
        <div className="customer-error-card">
          <AlertTriangle size={28} />

          <h2>Unable to load dashboard</h2>

          <p>{error}</p>

          <button
            className="customer-primary-button"
            onClick={() => void loadDashboard()}
          >
            <RefreshCw size={17} />
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="customer-dashboard-page">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                             */}
      {/* ------------------------------------------------------------------ */}

      <header className="customer-header">
        <div className="customer-header-inner">
          <div className="customer-brand">
            <div className="customer-brand-mark">R</div>

            <div>
              <strong>RazorRecover AI</strong>
              <span>Customer Portal</span>
            </div>
          </div>

          <div className="customer-header-actions">
            <button
              className="customer-refresh-button"
              onClick={() => void loadDashboard(true)}
              disabled={refreshing}
              title="Refresh dashboard"
            >
              <RefreshCw
                size={17}
                className={refreshing ? "customer-spin" : ""}
              />
              Refresh
            </button>

            <button
              className="customer-logout-button"
              onClick={handleLogout}
            >
              <LogOut size={17} />
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Main                                                               */}
      {/* ------------------------------------------------------------------ */}

      <main className="customer-main">
        <section className="customer-welcome">
          <div>
            <div className="customer-eyebrow">
              <ShieldCheck size={15} />
              SECURE CUSTOMER PORTAL
            </div>

            <h1>
              Welcome back
              {profile?.name ? `, ${profile.name.split(" ")[0]}` : ""}
            </h1>

            <p>
              Here's an overview of your payments and any transactions
              currently going through recovery.
            </p>
          </div>

          <div className="customer-account-chip">
            <div className="customer-account-avatar">
              {profile?.name?.charAt(0).toUpperCase() ?? "C"}
            </div>

            <div>
              <strong>{profile?.name ?? "Customer"}</strong>
              <span>{profile?.email ?? ""}</span>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Metrics                                                          */}
        {/* ---------------------------------------------------------------- */}

        <section className="customer-metrics-grid">
          <div className="customer-metric-card">
            <div className="customer-metric-icon">
              <Wallet size={20} />
            </div>

            <div className="customer-metric-label">
              Lifetime Value
            </div>

            <div className="customer-metric-value">
              {formatCurrency(profile?.lifetime_value ?? 0)}
            </div>

            <div className="customer-metric-note">
              Total value with us
            </div>
          </div>

          <div className="customer-metric-card">
            <div className="customer-metric-icon">
              <CheckCircle2 size={20} />
            </div>

            <div className="customer-metric-label">
              Successful Payments
            </div>

            <div className="customer-metric-value">
              {summary?.successful_payments ??
                profile?.successful_payments ??
                0}
            </div>

            <div className="customer-metric-note">
              Payments completed
            </div>
          </div>

          <div className="customer-metric-card">
            <div className="customer-metric-icon customer-metric-icon-warning">
              <AlertTriangle size={20} />
            </div>

            <div className="customer-metric-label">
              Failed Payments
            </div>

            <div className="customer-metric-value">
              {summary?.failed_payments ??
                profile?.failed_payments ??
                0}
            </div>

            <div className="customer-metric-note">
              Transactions needing attention
            </div>
          </div>

          <div className="customer-metric-card customer-metric-card-risk">
            <div className="customer-metric-icon customer-metric-icon-risk">
              <TrendingUp size={20} />
            </div>

            <div className="customer-metric-label">
              Amount at Risk
            </div>

            <div className="customer-metric-value">
              {formatCurrency(summary?.amount_at_risk ?? 0)}
            </div>

            <div className="customer-metric-note">
              Currently in recovery
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Recovery Overview                                                */}
        {/* ---------------------------------------------------------------- */}

        <section className="customer-recovery-card">
          <div className="customer-recovery-header">
            <div>
              <div className="customer-section-eyebrow">
                RECOVERY PROGRESS
              </div>

              <h2>Your recovery status</h2>

              <p>
                Our recovery system is working to resolve eligible
                failed payments.
              </p>
            </div>

            <div className="customer-recovery-rate">
              <strong>
                {Math.round(recoveryRate * 100)}%
              </strong>

              <span>recovery rate</span>
            </div>
          </div>

          <div className="customer-progress-track">
            <div
              className="customer-progress-fill"
              style={{
                width: `${Math.min(
                  100,
                  Math.max(0, recoveryRate * 100),
                )}%`,
              }}
            />
          </div>

          <div className="customer-recovery-stats">
            <div>
              <CheckCircle2 size={17} />
              <span>
                {summary?.recovered_cases ?? 0} recovered
              </span>
            </div>

            <div>
              <Clock3 size={17} />
              <span>
                {summary?.open_recovery_cases ?? 0} in progress
              </span>
            </div>

            <div>
              <CreditCard size={17} />
              <span>
                {summary?.total_transactions ?? 0} total transactions
              </span>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Two-column content                                               */}
        {/* ---------------------------------------------------------------- */}

        <section className="customer-content-grid">
          {/* Transactions */}

          <div className="customer-panel">
            <div className="customer-panel-header">
              <div>
                <div className="customer-section-eyebrow">
                  PAYMENT ACTIVITY
                </div>

                <h2>Recent transactions</h2>
              </div>

              <span className="customer-panel-count">
                {transactions.length}
              </span>
            </div>

            {recentTransactions.length === 0 ? (
              <div className="customer-empty-state">
                <CreditCard size={26} />
                <p>No transactions found.</p>
              </div>
            ) : (
              <div className="customer-transaction-list">
                {recentTransactions.map((transaction) => (
                  <div
                    className="customer-transaction-row"
                    key={transaction.id}
                  >
                    <div className="customer-transaction-icon">
                      {transaction.status
                        .toUpperCase()
                        .includes("SUCCESS") ? (
                        <ArrowUpRight size={17} />
                      ) : (
                        <ArrowDownRight size={17} />
                      )}
                    </div>

                    <div className="customer-transaction-main">
                      <strong>
                        {transaction.payment_method ||
                          "Payment"}
                      </strong>

                      <span>
                        {formatDate(transaction.created_at)}
                      </span>
                    </div>

                    <div className="customer-transaction-amount">
                      <strong>
                        {formatCurrency(
                          transaction.amount,
                          transaction.currency,
                        )}
                      </strong>

                      <span
                        className={getStatusClass(
                          transaction.status,
                        )}
                      >
                        {getStatusLabel(transaction.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recovery cases */}

          <div className="customer-panel">
            <div className="customer-panel-header">
              <div>
                <div className="customer-section-eyebrow">
                  RECOVERY
                </div>

                <h2>Recovery cases</h2>
              </div>

              <span className="customer-panel-count">
                {recoveryCases.length}
              </span>
            </div>

            {recentRecoveryCases.length === 0 ? (
              <div className="customer-empty-state">
                <CheckCircle2 size={26} />
                <p>No recovery cases at the moment.</p>
              </div>
            ) : (
              <div className="customer-recovery-list">
                {recentRecoveryCases.map((recoveryCase) => (
                  <div
                    className="customer-recovery-row"
                    key={recoveryCase.id}
                  >
                    <div className="customer-recovery-row-top">
                      <div>
                        <strong>
                          Recovery #{recoveryCase.id}
                        </strong>

                        <span>
                          {recoveryCase.failure_class}
                        </span>
                      </div>

                      <strong>
                        {formatCurrency(
                          recoveryCase.amount_at_risk,
                        )}
                      </strong>
                    </div>

                    <div className="customer-recovery-row-bottom">
                      <span
                        className={getStatusClass(
                          recoveryCase.status,
                        )}
                      >
                        {getStatusLabel(
                          recoveryCase.status,
                        )}
                      </span>

                      <span>
                        {recoveryCase.attempt_count}{" "}
                        {recoveryCase.attempt_count === 1
                          ? "attempt"
                          : "attempts"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Security / explanation                                           */}
        {/* ---------------------------------------------------------------- */}

        <section className="customer-info-banner">
          <div className="customer-info-icon">
            <ShieldCheck size={22} />
          </div>

          <div>
            <strong>
              Your payment information is protected
            </strong>

            <p>
              RazorRecover AI uses secure authentication and
              automated recovery workflows to help resolve
              eligible failed payments. We only show information
              associated with your account.
            </p>
          </div>
        </section>

        {error && (
          <div className="customer-inline-error">
            <AlertTriangle size={16} />
            {error}
          </div>
        )}
      </main>
    </div>
  );
}