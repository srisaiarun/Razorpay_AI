import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  CreditCard,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* ---------------------------------------------------------------- */}
      {/* Header                                                           */}
      {/* ---------------------------------------------------------------- */}

      <header className="landing-header">
        <Link to="/" className="landing-brand">
          <div className="landing-brand-mark">
            R
          </div>

          <div>
            <strong>RazorRecover</strong>
            <span>AI</span>
          </div>
        </Link>

        <nav className="landing-nav">
          <a href="#solutions">Solutions</a>
          <a href="#offers">Offers</a>
          <a href="#security">Security</a>

          <Link
            to="/customer/login"
            className="landing-nav-button secondary"
          >
            Customer Sign In
          </Link>

          <Link
            to="/management/login"
            className="landing-nav-button primary"
          >
            Management Sign In
          </Link>
        </nav>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Hero                                                             */}
      {/* ---------------------------------------------------------------- */}

      <main>
        <section className="landing-hero">
          <div className="landing-hero-content">
            <div className="landing-eyebrow">
              <Sparkles size={15} />
              POWERING SMARTER PAYMENTS
            </div>

            <h1>
              Welcome to
              <br />
              <span>RazorRecover AI</span>
            </h1>

            <p className="landing-hero-description">
              A smarter payment recovery experience that
              helps businesses recover failed transactions
              while giving customers a simple and secure
              way to get back on track.
            </p>

            <div className="landing-hero-actions">
              <Link
                to="/customer/login"
                className="landing-primary-button"
              >
                Continue as Customer
                <ArrowRight size={18} />
              </Link>

              <Link
                to="/management/login"
                className="landing-secondary-button"
              >
                Management Portal
              </Link>
            </div>

            <div className="landing-trust-row">
              <span>
                <CheckCircle2 size={15} />
                Secure payments
              </span>

              <span>
                <CheckCircle2 size={15} />
                Intelligent recovery
              </span>

              <span>
                <CheckCircle2 size={15} />
                Human-controlled actions
              </span>
            </div>
          </div>

          <div className="landing-hero-visual">
            <div className="hero-glow" />

            <div className="payment-card">
              <div className="payment-card-header">
                <span>Payment Recovery</span>

                <ShieldCheck size={20} />
              </div>

              <div className="payment-amount">
                ₹24,850
              </div>

              <div className="payment-status">
                <span className="payment-status-dot" />
                Recovery opportunity detected
              </div>

              <div className="payment-progress">
                <div className="payment-progress-bar" />
              </div>

              <div className="payment-card-footer">
                <span>AI recovery confidence</span>
                <strong>87.4%</strong>
              </div>
            </div>

            <div className="floating-card floating-card-one">
              <TrendingUp size={18} />
              <div>
                <strong>Recovery +24%</strong>
                <span>This month</span>
              </div>
            </div>

            <div className="floating-card floating-card-two">
              <CheckCircle2 size={18} />
              <div>
                <strong>Payment recovered</strong>
                <span>Just now</span>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Stats                                                            */}
        {/* ---------------------------------------------------------------- */}

        <section className="landing-stats">
          <div>
            <strong>99.9%</strong>
            <span>Payment infrastructure reliability</span>
          </div>

          <div>
            <strong>24/7</strong>
            <span>Intelligent recovery monitoring</span>
          </div>

          <div>
            <strong>AI</strong>
            <span>Data-driven recovery decisions</span>
          </div>

          <div>
            <strong>Secure</strong>
            <span>Controlled payment operations</span>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Solutions                                                        */}
        {/* ---------------------------------------------------------------- */}

        <section
          id="solutions"
          className="landing-section"
        >
          <div className="landing-section-heading">
            <div className="landing-eyebrow">
              PAYMENT EXPERIENCE
            </div>

            <h2>
              Everything you need to
              <span> recover revenue.</span>
            </h2>

            <p>
              RazorRecover AI combines payment intelligence,
              recovery prediction, and controlled automation
              into one operational platform.
            </p>
          </div>

          <div className="solution-grid">
            <article className="solution-card">
              <div className="solution-icon">
                <CreditCard size={22} />
              </div>

              <h3>Payment Intelligence</h3>

              <p>
                Understand failed transactions and identify
                the customers most likely to recover.
              </p>
            </article>

            <article className="solution-card">
              <div className="solution-icon">
                <BarChart3 size={22} />
              </div>

              <h3>AI Recovery Decisions</h3>

              <p>
                Use recovery probability and amount at risk
                to prioritize the right recovery strategy.
              </p>
            </article>

            <article className="solution-card">
              <div className="solution-icon">
                <WalletCards size={22} />
              </div>

              <h3>Revenue Recovery</h3>

              <p>
                Turn eligible failed payments into actionable
                recovery opportunities.
              </p>
            </article>

            <article className="solution-card">
              <div className="solution-icon">
                <LockKeyhole size={22} />
              </div>

              <h3>Controlled Execution</h3>

              <p>
                Sensitive recovery actions can remain behind
                human approval and audit controls.
              </p>
            </article>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Offers                                                           */}
        {/* ---------------------------------------------------------------- */}

        <section
          id="offers"
          className="landing-offers"
        >
          <div className="landing-section-heading">
            <div className="landing-eyebrow">
              CUSTOMER BENEFITS
            </div>

            <h2>
              Offers designed for
              <span> better payments.</span>
            </h2>

            <p>
              Explore the types of customer incentives that
              can be surfaced alongside eligible payment
              recovery opportunities.
            </p>
          </div>

          <div className="offers-grid">
            <article className="offer-card">
              <div className="offer-label">
                LIMITED OFFER
              </div>

              <h3>Retry & Save</h3>

              <p>
                Eligible customers may receive a special
                retry incentive when recovering a failed
                payment.
              </p>

              <span className="offer-action">
                View eligible offers
                <ArrowRight size={16} />
              </span>
            </article>

            <article className="offer-card">
              <div className="offer-label">
                PAYMENT BENEFIT
              </div>

              <h3>Flexible Recovery</h3>

              <p>
                Give customers a clearer path to resolving
                unsuccessful payments without unnecessary
                friction.
              </p>

              <span className="offer-action">
                Explore benefits
                <ArrowRight size={16} />
              </span>
            </article>

            <article className="offer-card">
              <div className="offer-label">
                SMART PAYMENTS
              </div>

              <h3>Secure Retry</h3>

              <p>
                Keep payment recovery simple while
                maintaining strong security and transaction
                controls.
              </p>

              <span className="offer-action">
                Learn more
                <ArrowRight size={16} />
              </span>
            </article>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Security                                                         */}
        {/* ---------------------------------------------------------------- */}

        <section
          id="security"
          className="landing-security"
        >
          <div>
            <div className="landing-eyebrow">
              BUILT FOR TRUST
            </div>

            <h2>
              Intelligent automation with
              <span> human control.</span>
            </h2>

            <p>
              Recovery decisions can be automated, while
              sensitive actions remain subject to management
              approval and a complete audit trail.
            </p>
          </div>

          <div className="security-points">
            <div>
              <ShieldCheck size={20} />

              <div>
                <strong>Role-based access</strong>

                <span>
                  Separate customer and management
                  experiences.
                </span>
              </div>
            </div>

            <div>
              <LockKeyhole size={20} />

              <div>
                <strong>Controlled execution</strong>

                <span>
                  Approval can be required before sensitive
                  recovery actions execute.
                </span>
              </div>
            </div>

            <div>
              <BarChart3 size={20} />

              <div>
                <strong>Auditable decisions</strong>

                <span>
                  Recovery decisions and actions remain
                  traceable.
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* CTA                                                              */}
        {/* ---------------------------------------------------------------- */}

        <section className="landing-cta">
          <div>
            <div className="landing-eyebrow">
              GET STARTED
            </div>

            <h2>
              Ready to make every payment
              <span> count?</span>
            </h2>

            <p>
              Choose your portal to continue.
            </p>
          </div>

          <div className="landing-cta-actions">
            <Link
              to="/customer/login"
              className="landing-primary-button"
            >
              Customer Sign In
              <ArrowRight size={18} />
            </Link>

            <Link
              to="/management/login"
              className="landing-secondary-button"
            >
              Management Sign In
            </Link>
          </div>
        </section>
      </main>

      {/* ---------------------------------------------------------------- */}
      {/* Footer                                                           */}
      {/* ---------------------------------------------------------------- */}

      <footer className="landing-footer">
        <div className="landing-brand">
          <div className="landing-brand-mark">
            R
          </div>

          <div>
            <strong>RazorRecover</strong>
            <span>AI</span>
          </div>
        </div>

        <span>
          AI-powered payment recovery platform
        </span>

        <span>
          © 2026 RazorRecover AI
        </span>
      </footer>
    </div>
  );
}