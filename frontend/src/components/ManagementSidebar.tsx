import {
  Activity,
  CheckCircle2,
  LayoutDashboard,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

export type ManagementSection =
  | "dashboard"
  | "queue"
  | "decisions"
  | "customers"
  | "actions";

interface ManagementSidebarProps {
  active: ManagementSection;
}

export default function ManagementSidebar({
  active,
}: ManagementSidebarProps) {
  const navClass = (section: ManagementSection) =>
    active === section
      ? "nav-item nav-item-active"
      : "nav-item";

  return (
    <aside className="sidebar">
      <Link to="/management" className="brand brand-link">
        <div className="brand-mark">
          <ShieldCheck size={22} />
        </div>
        <div>
          <div className="brand-name">RazorRecover</div>
          <div className="brand-subtitle">
            AI Revenue Recovery
          </div>
        </div>
      </Link>

      <nav className="navigation">
        <div className="nav-section-label">
          OPERATIONS
        </div>

        <Link
          to="/management"
          className={navClass("dashboard")}
        >
          <LayoutDashboard size={18} />
          Dashboard
        </Link>

        <Link
          to="/management/recovery-queue"
          className={navClass("queue")}
        >
          <Target size={18} />
          Recovery Queue
        </Link>

        <Link
          to="/management/decisions"
          className={navClass("decisions")}
        >
          <Activity size={18} />
          Decisions
        </Link>

        <div className="nav-section-label nav-section-spaced">
          MANAGEMENT
        </div>

        <Link
          to="/management/customers"
          className={navClass("customers")}
        >
          <Users size={18} />
          Customers
        </Link>

        <Link
          to="/management/recovery-actions"
          className={navClass("actions")}
        >
          <CheckCircle2 size={18} />
          Recovery Actions
        </Link>
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot status-online" />
          <div>
            <div className="system-status-title">
              Backend
            </div>
            <div className="system-status-value">
              Connected
            </div>
          </div>
        </div>

        <div className="version">
          RazorRecover AI · v0.1.0
        </div>
      </div>
    </aside>
  );
}
