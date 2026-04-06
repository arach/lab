export default function BenchmarkRepairPanel({ summary }) {
  const headline = [
    {
      label: 'Original v1',
      value: summary.v1.pass,
      note: summary.v1.note,
    },
    {
      label: 'Fixed v1.1',
      value: summary.v1_1.pass,
      note: summary.v1_1.note,
    },
    {
      label: 'Model',
      value: summary.model,
      note: summary.provider,
    },
  ]

  return (
    <section className="data-band repair-band">
      <div className="data-band-header">
        <div>
          <p className="section-kicker">Benchmark Repair</p>
          <h3>Same model. Same broad pack. Much saner benchmark.</h3>
          <p>
            This is the clearest proof we have that the old benchmark was the
            problem. Once we accepted reasonable output variants and fixed the
            miscalibrated checks, the score jumped without changing the model.
          </p>
        </div>
        <span className="tiny-chip">v1 → v1.1</span>
      </div>

      <div className="repair-hero-grid">
        {headline.map((item) => (
          <div key={item.label} className="repair-hero-card">
            <span className="stat-label">{item.label}</span>
            <span className="stat-value">{item.value}</span>
            <div className="metric-note">{item.note}</div>
          </div>
        ))}
      </div>

      <div className="repair-delta-row">
        <div className="repair-delta-card">
          <span className="repair-delta-label">Full Pack</span>
          <div className="repair-delta-main">
            <span className="repair-old">{summary.v1.pass}</span>
            <span className="repair-arrow">→</span>
            <span className="repair-new">{summary.v1_1.pass}</span>
          </div>
          <p>{summary.v1_1.delta_note}</p>
        </div>

        <div className="repair-delta-card">
          <span className="repair-delta-label">Ship-Soon Slice</span>
          <div className="repair-delta-main">
            <span className="repair-old">{summary.ship_soon.before}</span>
            <span className="repair-arrow">→</span>
            <span className="repair-new">{summary.ship_soon.after}</span>
          </div>
          <p>{summary.ship_soon.note}</p>
        </div>
      </div>

      <div className="table-wrap">
        <table className="scores-table">
          <thead>
            <tr>
              <th>Layer</th>
              <th>v1.1 Score</th>
              <th>Why it matters</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="col-identifier">Task</td>
              <td className="col-score">{summary.v1_1.task}</td>
              <td>Did the model actually do the job?</td>
            </tr>
            <tr>
              <td className="col-identifier">Usable</td>
              <td className="col-score">{summary.v1_1.usable}</td>
              <td>Could the product use the output with light normalization?</td>
            </tr>
            <tr>
              <td className="col-identifier">Contract</td>
              <td className="col-score">{summary.v1_1.contract}</td>
              <td>Did it match our preferred schema exactly?</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}
