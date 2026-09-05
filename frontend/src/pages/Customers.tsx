import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  DollarSign,
  Loader2,
  Mail,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import ManagementSidebar from "../components/ManagementSidebar";

import { getAllCustomers } from "../services/api";
import type { AdminCustomer } from "../types/recovery";

function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(value);
}

function statusClass(status: string | null) {
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

export default function Customers() {
  const navigate = useNavigate();

  const [customers, setCustomers] = useState<
    AdminCustomer[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");

  async function loadCustomers(
    isRefresh = false,
  ) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError(null);

      const data = await getAllCustomers();

      setCustomers(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load customers.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadCustomers();
  }, []);

  const filteredCustomers = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return customers;
    }

    return customers.filter(
      (customer) =>
        String(customer.id).includes(query) ||
        customer.external_customer_id
          .toLowerCase()
          .includes(query) ||
        customer.name
          .toLowerCase()
          .includes(query) ||
        customer.email
          .toLowerCase()
          .includes(query),
    );
  }, [customers, search]);

  const statistics = useMemo(() => {
    const totalCustomers = customers.length;

    const customersWithOpenCases =
      customers.filter(
        (customer) => customer.open_cases > 0,
      ).length;

    const recoveredCustomers =
      customers.filter(
        (customer) =>
          customer.recovered_cases > 0 &&
          customer.open_cases === 0,
      ).length;

    const totalAtRisk = customers.reduce(
      (sum, customer) =>
        sum + customer.total_amount_at_risk,
      0,
    );

    const expectedRecovery = customers.reduce(
      (sum, customer) =>
        sum + customer.expected_recovery_value,
      0,
    );

    return {
      totalCustomers,
      customersWithOpenCases,
      recoveredCustomers,
      totalAtRisk,
      expectedRecovery,
    };
  }, [customers]);

  if (loading) {
    return (
      <div className="management-shell">
        <ManagementSidebar active="customers" />
        <main className="management-main">
          <div className="page-container">
            <div className="loading-state">
          <Loader2
            size={22}
            className="spin"
          />

              <span>
                Loading customer recovery data...
              </span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="management-shell">
      <ManagementSidebar active="customers" />
      <main className="management-main">
        <div className="page-container">
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
              CUSTOMER OPERATIONS
            </div>

            <h1>Customers</h1>

            <p className="page-description">
              Customer-level recovery exposure,
              payment history, and recovery status.
            </p>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() =>
              void loadCustomers(true)
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

        {error && (
          <div className="error-banner">
            <CircleAlert size={18} />

            <span>{error}</span>

            <button
              type="button"
              onClick={() =>
                void loadCustomers()
              }
            >
              Retry
            </button>
          </div>
        )}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Users size={20} />
            </div>

            <div>
              <div className="stat-label">
                Total Customers
              </div>

              <div className="stat-value">
                {statistics.totalCustomers}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <ShieldAlert size={20} />
            </div>

            <div>
              <div className="stat-label">
                Customers With Open Cases
              </div>

              <div className="stat-value">
                {
                  statistics.customersWithOpenCases
                }
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <CheckCircle2 size={20} />
            </div>

            <div>
              <div className="stat-label">
                Recovered Customers
              </div>

              <div className="stat-value">
                {statistics.recoveredCustomers}
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <DollarSign size={20} />
            </div>

            <div>
              <div className="stat-label">
                Total Amount At Risk
              </div>

              <div className="stat-value stat-value-money">
                {money(statistics.totalAtRisk)}
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
                {money(
                  statistics.expectedRecovery,
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="section-card">
          <div className="section-header">
            <div>
              <h2>Customer Recovery Profiles</h2>

              <p>
                {filteredCustomers.length} of{" "}
                {customers.length} customers displayed
              </p>
            </div>

            <div className="search-field">
              <Search size={17} />

              <input
                type="text"
                placeholder="Search customer..."
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />
            </div>
          </div>

          {filteredCustomers.length === 0 ? (
            <div className="table-message">
              <Users size={30} />

              <h3>
                No customers found
              </h3>

              <p>
                Try changing your search.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Contact</th>
                    <th>Cases</th>
                    <th>Recovered</th>
                    <th>Amount At Risk</th>
                    <th>Expected Recovery</th>
                    <th>Payments</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {filteredCustomers.map(
                    (customer) => (
                      <tr
                        key={customer.id}
                        className="clickable-row"
                        onClick={() => {
                          if (
                            customer.latest_case_id
                          ) {
                            navigate(
                              `/management/recovery-cases/${customer.latest_case_id}`,
                            );
                          }
                        }}
                      >
                        <td>
                          <div className="customer-cell">
                            <strong>
                              {customer.name}
                            </strong>

                            <span>
                              #{customer.id}
                            </span>
                          </div>
                        </td>

                        <td>
                          <div className="contact-cell">
                            <span>
                              <Mail size={13} />
                              {customer.email}
                            </span>

                            <small>
                              {
                                customer.external_customer_id
                              }
                            </small>
                          </div>
                        </td>

                        <td>
                          <strong>
                            {customer.total_cases}
                          </strong>

                          {customer.open_cases >
                            0 && (
                            <div className="table-subtext">
                              {
                                customer.open_cases
                              }{" "}
                              open
                            </div>
                          )}
                        </td>

                        <td>
                          <strong>
                            {
                              customer.recovered_cases
                            }
                          </strong>
                        </td>

                        <td>
                          <strong>
                            {money(
                              customer.total_amount_at_risk,
                            )}
                          </strong>
                        </td>

                        <td>
                          <strong>
                            {money(
                              customer.expected_recovery_value,
                            )}
                          </strong>
                        </td>

                        <td>
                          <div className="payment-counts">
                            <span>
                              ✓{" "}
                              {
                                customer.successful_payments
                              }
                            </span>

                            <span>
                              ✕{" "}
                              {
                                customer.failed_payments
                              }
                            </span>
                          </div>
                        </td>

                        <td>
                          <span
                            className={statusClass(
                              customer.latest_case_status,
                            )}
                          >
                            {customer.latest_case_status ??
                              "NO CASE"}
                          </span>

                          {customer.opted_out && (
                            <div className="table-subtext">
                              Recovery opted out
                            </div>
                          )}
                        </td>

                        <td>
                          <span className="row-chevron">
                            →
                          </span>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
        </div>
      </main>
    </div>
  );
}