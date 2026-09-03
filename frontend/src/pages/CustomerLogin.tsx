import {
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function CustomerLogin() {
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
            CUSTOMER PORTAL
          </div>

          <h1>Welcome back</h1>

          <p>
            Sign in to view your payments, recovery status,
            and available customer offers.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={(event) =>
            event.preventDefault()
          }
        >
          <label htmlFor="customer-email">
            Email address
          </label>

          <input
            id="customer-email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
          />

          <label htmlFor="customer-password">
            Password
          </label>

          <input
            id="customer-password"
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
            Secure customer authentication
          </span>
        </div>

            <div className="auth-switch">
                <span>Don't have an account?</span>

                <Link to="/customer/register">
                    Create Account
                </Link>
            </div>

            <div className="auth-switch">
                <span>Managing recovery operations?</span>

                <Link to="/management/login">
                    Management Sign In
                </Link>
            </div>
      </div>

      <div className="auth-side">
        <LockKeyhole size={32} />

        <h2>
          Your payments.
          <br />
          Your recovery.
        </h2>

        <p>
          Access your payment history and resolve eligible
          failed transactions through a secure recovery
          experience.
        </p>
      </div>
    </div>
  );
}