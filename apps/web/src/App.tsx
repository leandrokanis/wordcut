import { useEffect, useState } from "react";

import { fetchHealth } from "./api";

const CHECKING = "verificando…";
const UNAVAILABLE = "indisponível";

export function App() {
  const [status, setStatus] = useState(CHECKING);

  useEffect(() => {
    fetchHealth().then(
      (health) => setStatus(health.status),
      () => setStatus(UNAVAILABLE),
    );
  }, []);

  return (
    <main>
      <h1>Wordcut</h1>
      <p>API: {status}</p>
    </main>
  );
}
