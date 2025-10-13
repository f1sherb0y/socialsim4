import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <section className="panel" style={{ maxWidth: 960, margin: "0 auto", gap: "0.75rem" }}>
      <h1 style={{ fontSize: "2.25rem", fontWeight: 700, margin: 0 }}>
        Design, run, and explore social simulations driven by large language models.
      </h1>
      <p style={{ fontSize: "1rem", color: "var(--muted)", margin: 0 }}>
        Coordinate agents, branch timelines, and share live results with an interface built for experimentation teams.
      </p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <Link to="/register" className="button">Launch your first simulation</Link>
        <Link to="/login" className="button" style={{ background: "linear-gradient(135deg, rgba(148,163,184,0.6), rgba(148,163,184,0.4))" }}>
          Resume your work
        </Link>
      </div>
    </section>
  );
}
