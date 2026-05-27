import './globals.css'

export const metadata = {
  title: 'BookBrain - Agentic RAG',
  description: 'Your personal AI-powered library',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
