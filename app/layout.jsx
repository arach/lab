import { Fraunces, JetBrains_Mono, Space_Grotesk } from 'next/font/google'
import { createLabMetadata } from '../lib/site-metadata'
import './globals.css'

const grotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const jetmono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
})

export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Ideas, experiments, benchmark notes, and daily TILs from Training Lab.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${grotesk.variable} ${jetmono.variable} ${fraunces.variable}`}
      suppressHydrationWarning
    >
      <body className={grotesk.className}>{children}</body>
    </html>
  )
}
