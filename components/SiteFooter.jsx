import Link from 'next/link'

export default function SiteFooter({ note = 'Experiments with models and training' }) {
  return (
    <footer className="lab-footer">
      <div className="lab-shell lab-footer-inner">
        <Link href="/" className="brand lab-brand">
          <span className="lab-brand-dot" aria-hidden="true" />
          Training Lab
        </Link>
        <span>{note}</span>
      </div>
    </footer>
  )
}
