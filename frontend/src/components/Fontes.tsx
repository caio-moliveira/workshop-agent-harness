// Fontes citadas — o analista precisa vê-las (grounding inspecionável).

export function Fontes({ fontes }: { fontes: string[] }) {
  if (fontes.length === 0) return null;
  return (
    <section className="fontes">
      <h3>Fontes citadas ({fontes.length})</h3>
      <ul>
        {fontes.map((f) => (
          <li key={f}>
            <code>{f}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}
