import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'TG Source Radar',
  description: 'Telegram Source Discovery Engine',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14 items-center">
              <a href="/" className="flex items-center gap-2 font-semibold text-lg">
                <span className="text-brand-600">TG Source Radar</span>
              </a>
              <div className="flex gap-6 text-sm">
                <a href="/" className="hover:text-brand-600 transition-colors">Dashboard</a>
                <a href="/projects" className="hover:text-brand-600 transition-colors">Projects</a>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
      </body>
    </html>
  )
}
