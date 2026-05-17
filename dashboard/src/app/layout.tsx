import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'EthioBio AI Assistant - Teacher Dashboard',
  description: 'Biology education platform for Ethiopian middle and high schools',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground font-sans">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 p-6 lg:p-8 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
