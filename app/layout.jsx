import { Geist, Geist_Mono } from 'next/font/google'
import { createLabMetadata } from '../lib/site-metadata'
import './globals.css'
import './lab.css'

const sans = Geist({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const mono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
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
      className={`${sans.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body className={sans.className}>{children}</body>
    </html>
  )
}
