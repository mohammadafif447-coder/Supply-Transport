export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-smoke px-4">
      <div className="w-full max-w-sm rounded-lg border border-silver bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-center text-xl font-semibold text-iron">Supply Transport</h1>
        {children}
      </div>
    </div>
  );
}
