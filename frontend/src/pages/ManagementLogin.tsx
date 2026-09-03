import {
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function ManagementLogin() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <Link to="/" className="auth-back">
          <ArrowLeft size={16} />
          Back to RazorRecover
        </Link>

        <div className="auth-logo">
          <div className="landing-brand-mark">
            R
          </div>

          <strong>RazorRecover AI</strong>
        </div>

        <div className="auth-heading">
          <div className="landing-eyebrow">
            MANAGEMENT PORTAL
          </div>

          <h1>Welcome back</h1>

          <p>
            Sign in to manage recovery cases, review AI
            decisions, and control recovery actions.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={(event) =>
            event.preventDefault()
          }
        >
          <label htmlFor="management-email">
            Management email
          </label>

          <input
            id="management-email"
            type="email"
            placeholder="admin@example.com"
            autoComplete="email"
          />

          <label htmlFor="management-password">
            Password
          </label>

          <input
            id="management-password"
            type="password"
            placeholder="Enter your password"
            autoComplete="current-password"
          />

          <button
            type="submit"
            className="landing-primary-button auth-submit"
          >
            Sign In
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="auth-security">
          <ShieldCheck size={17} />

          <span>
            Authorized management access only
          </span>
        </div>

        <div className="auth-switch">
            <span>Don't have a management account?</span>

            <Link to="/management/request-access">
                Request Management Access
            </Link>
        </div>

        <div className="auth-switch">
            <span>Looking for your payment account?</span>

            <Link to="/customer/login">
                Customer Sign In
            </Link>
        </div>
      </div>

      <div className="auth-side management">
        <LockKeyhole size={32} />

        <h2>
          Recover revenue.
          <br />
          Control every action.
        </h2>

        <p>
          Review AI-generated recovery decisions and
          maintain human oversight over sensitive recovery
          operations.
        </p>
      </div>
    </div>
  );
}