import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <div className="app-container">
      <header className="app-header">
        <div>SocialSim4</div>
        <div>
          <Link to="/login" className="button" style={{ marginRight: "0.75rem" }}>
            Sign in
          </Link>
          <Link to="/register" className="button">
            Get started
          </Link>
        </div>
      </header>
      <main className="app-main">
        <section style={{ display: "grid", gap: "1.5rem", maxWidth: "900px" }}>
          <h1 style={{ fontSize: "3rem", fontWeight: 700 }}>Design, run, and explore social simulations driven by large language models.</h1>
          <p style={{ fontSize: "1.25rem", color: "#94a3b8" }}>
            Coordinate agents, branch timelines, and share live results with an interface built for experimentation teams.
          </p>
          <div style={{ display: "flex", gap: "1rem" }}>
            <Link to="/register" className="button">
              Launch your first simulation
            </Link>
            <Link to="/login" className="button" style={{ background: "rgba(148, 163, 184, 0.2)", color: "#e2e8f0" }}>
              Resume your work
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
