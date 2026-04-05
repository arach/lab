export default function EvalIntroPanel({ cards }) {
  return (
    <section className="data-band">
      <div className="data-band-header">
        <div>
          <p className="section-kicker">Core Eval v2</p>
          <h2>A smaller benchmark built for real workflow usefulness.</h2>
          <p>
            These are the current sanity-check tasks. They are intentionally small,
            product-real, and designed to separate task success from strict schema obedience.
          </p>
        </div>
        <span className="tiny-chip">{cards.length} core cards</span>
      </div>
      <div className="data-band-body table-wrap">
        <table className="cards-table">
          <thead>
            <tr>
              <th>Card</th>
              <th>Category</th>
              <th>Why it matters</th>
            </tr>
          </thead>
          <tbody>
            {cards.map((card) => (
              <tr key={card.id}>
                <td className="col-identifier">{card.title}</td>
                <td><span className="category-chip">{card.benchmarkCategory}</span></td>
                <td>{card.objective}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
