import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";

import { useState } from "react";
import type { FormEvent } from "react";

import { Link, useNavigate } from "react-router-dom";

import { login } from "../services/api";

export default function ManagementLogin() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setError("");

    if (!email.trim() || !password) {
      setError("Please enter your management email and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await login(
        email.trim(),
        password,
      );

      /*
       * Management login must only accept MANAGEMENT accounts.
       */
      if (response.user.role !== "MANAGEMENT") {
        setError(
          "This account is not a management account. Please use Customer Sign In.",
        );
        return;
      }

      /*
       * Store JWT for authenticated management API requests.
       */
      sessionStorage.setItem(
        "razorrecover_access_token",
        response.access_token,
      );

      /*
       * Store authenticated user information.
       */
      sessionStorage.setItem(
        "razorrecover_user",
        JSON.stringify(response.user),
      );

      /*
       * Redirect to the existing management dashboard.
       */
      navigate("/management", {
        replace: true,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in. Please check your credentials.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Back */}
        <Link to="/" className="auth-back">
          <ArrowLeft size={16} />
          Back to RazorRecover
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <div className="landing-brand-mark">
            R
          </div>

          <strong>RazorRecover AI</strong>
        </div>

        {/* Heading */}
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

        {/* Login Form */}
        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <label htmlFor="management-email">
            Management email
          </label>

          <input
            id="management-email"
            type="email"
            placeholder="admin@example.com"
            autoComplete="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            disabled={loading}
          />

          <label htmlFor="management-password">
            Password
          </label>

          <input
            id="management-password"
            type="password"
            placeholder="Enter your password"
            autoComplete="current-password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            disabled={loading}
          />

          {/* Error */}
          {error && (
            <div
              className="auth-error"
              role="alert"
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className="landing-primary-button auth-submit"
            disabled={loading}
          >
            {loading ? (
              "Signing In..."
            ) : (
              <>
                Sign In
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {/* Security */}
        <div className="auth-security">
          <ShieldCheck size={17} />

          <span>
            Authorized management access only
          </span>
        </div>

        {/* Request Access */}
        <div className="auth-switch">
          <span>
            Don't have a management account?
          </span>

          <Link to="/management/request-access">
            Request Management Access
          </Link>
        </div>

        {/* Customer Login */}
        <div className="auth-switch">
          <span>
            Looking for your payment account?
          </span>

          <Link to="/customer/login">
            Customer Sign In
          </Link>
        </div>
      </div>

      {/* Right Side */}
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