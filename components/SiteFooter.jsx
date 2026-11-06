// One thin full-width bar, matching arach.dev's footer.
const LINKS = [
  { href: '/', label: 'arach.dev' },
  { href: 'https://arach.io', label: 'arach.io' },
  { href: 'https://github.com/arach', label: 'GitHub' },
  { href: 'https://www.linkedin.com/in/arach/', label: 'LinkedIn' },
  { href: 'https://x.com/arach', label: 'X' },
]

export default function SiteFooter() {
  const year = new Date().getFullYear()
  return (
    <footer className="lab-foot">
      <div className="lab-foot-inner">
        <span>© {year} Arach Tchoupani · Montreal / SF</span>
        <ul>
          {LINKS.map((link) => (
            <li key={link.label}>
              <a href={link.href}>{link.label}</a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  )
}
