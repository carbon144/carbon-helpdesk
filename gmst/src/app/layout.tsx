import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Get My Shit Together',
  description: 'Organize your tasks, habits, and goals',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  )
}
