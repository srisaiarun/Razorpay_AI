import {
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function ManagementRequestAccess() {
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
            MANAGEMENT ACCESS
          </div>

          <h1>Request access</h1>

          <p>
            Management access is restricted. Submit your
            details and an authorized administrator can
            review your request.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={(event) =>
            event.preventDefault()
          }
        >
          <label htmlFor="management-name">
            Full name
          </label>

          <input
            id="management-name"
            type="text"
            placeholder="Your full name"
            autoComplete="name"
          />

          <label htmlFor="management-email">
            Work email
          </label>

          <input
            id="management-email"
            type="email"
            placeholder="you@company.com"
            autoComplete="email"
          />

          <label htmlFor="management-role">
            Role
          </label>

          <input
            id="management-role"
            type="text"
            placeholder="Operations / Finance / Admin"
          />

          <label htmlFor="management-reason">
            Reason for access
          </label>

          <textarea
            id="management-reason"
            className="auth-textarea"
            placeholder="Tell us why management access is required."
            rows={4}
          />

          <button
            type="submit"
            className="landing-primary-button auth-submit"
          >
            Submit Access Request
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="auth-security">
          <ShieldCheck size={17} />

          <span>
            Management access requires authorization.
          </span>
        </div>

        <div className="auth-switch">
          <span>Already authorized?</span>

          <Link to="/management/login">
            Management Sign In
          </Link>
        </div>

        <div className="auth-switch">
          <span>Are you a customer?</span>

          <Link to="/customer/login">
            Customer Sign In
          </Link>
        </div>
      </div>

      <div className="auth-side management">
        <LockKeyhole size={32} />

        <h2>
          Secure access.
          <br />
          Controlled operations.
        </h2>

        <p>
          Management access provides visibility into AI
          recovery decisions and controlled recovery
          operations.
        </p>
      </div>
    </div>
  );
}