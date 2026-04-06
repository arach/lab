export default function SemanticEvalPanel({ summary }) {
  return (
    <section className="data-band semantic-band">
      <div className="data-band-header">
        <div>
          <p className="section-kicker">Semantic Eval</p>
          <h3>Tiny models should be judged on semantic usefulness.</h3>
          <p>
            This pack stops asking local models for machine-perfect structure and
            instead asks whether they understand the memo, identify the user’s
            intent, and offer the right help.
          </p>
        </div>
        <span className="tiny-chip">semantic-core-v1</span>
      </div>

      <div className="semantic-principles">
        {summary.principles.map((item) => (
          <div key={item.label} className="semantic-principle-card">
            <span className="stat-label">{item.label}</span>
            <p>{item.text}</p>
          </div>
        ))}
      </div>

      <div className="semantic-card-row">
        <div className="semantic-card-list">
          <span className="stat-label">Core moments</span>
          <ul>
            {summary.cards.map((card) => (
              <li key={card}>{card}</li>
            ))}
          </ul>
        </div>

        <div className="semantic-card-list">
          <span className="stat-label">What we stopped measuring</span>
          <ul>
            {summary.exclusions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="table-wrap">
        <table className="scores-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Pass</th>
              <th>Task</th>
              <th>Clarity</th>
              <th>Discipline</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {summary.results.map((row) => (
              <tr key={row.model}>
                <td className="col-identifier">{row.model}</td>
                <td className="col-score">{row.pass}</td>
                <td>{row.task}</td>
                <td>{row.clarity}</td>
                <td>{row.discipline}</td>
                <td>{row.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
