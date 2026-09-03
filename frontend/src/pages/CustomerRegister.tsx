import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function CustomerRegister() {
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
            CUSTOMER REGISTRATION
          </div>

          <h1>Create your account</h1>

          <p>
            Create a secure account to view payments,
            manage recovery opportunities, and access
            eligible offers.
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={(event) =>
            event.preventDefault()
          }
        >
          <label htmlFor="customer-name">
            Full name
          </label>

          <input
            id="customer-name"
            type="text"
            placeholder="Your full name"
            autoComplete="name"
          />

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
            placeholder="Create a password"
            autoComplete="new-password"
          />

          <label htmlFor="customer-confirm-password">
            Confirm password
          </label>

          <input
            id="customer-confirm-password"
            type="password"
            placeholder="Confirm your password"
            autoComplete="new-password"
          />

          <button
            type="submit"
            className="landing-primary-button auth-submit"
          >
            Create Account
            <ArrowRight size={18} />
          </button>
        </form>

        <div className="auth-security">
          <ShieldCheck size={17} />

          <span>
            Your account information is protected.
          </span>
        </div>

        <div className="auth-switch">
          <span>Already have an account?</span>

          <Link to="/customer/login">
            Sign In
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
        <CheckCircle2 size={32} />

        <h2>
          One account.
          <br />
          Complete payment visibility.
        </h2>

        <p>
          Keep track of your payment activity, discover
          eligible recovery options, and manage your
          payment experience from one secure portal.
        </p>
      </div>
    </div>
  );
}