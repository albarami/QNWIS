interface HeaderProps {
  title?: string
  subtitle?: string
}

export const Header = ({
  title = 'QNWIS Intelligence System',
  subtitle = 'Qatar Ministry of Labour – Multi-Agent Strategic Council',
}: HeaderProps) => (
  <header className="bg-white border-b border-gray-200 shadow-sm">
    <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5">
      <div>
        <p className="text-xs uppercase tracking-widest text-blue-600">Ministry of Labour – QNWIS</p>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        <p className="text-sm text-gray-600">{subtitle}</p>
      </div>
      <img
        src="/logo.png"
        alt="QNWIS"
        className="h-10 w-10 rounded-full border border-gray-200 object-cover"
        onError={(e) => {
          // hide if logo missing
          ;(e.currentTarget as HTMLImageElement).style.display = 'none'
        }}
      />
    </div>
  </header>
)
