import { Building2, ShieldCheck } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2.5" aria-label="Lead Desk home">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white shadow-sm">
              <Building2 className="h-5 w-5" aria-hidden />
            </span>
            <span className="leading-tight">
              <span className="block text-base font-bold tracking-tight">Lead Desk</span>
              <span className="hidden text-xs text-slate-500 sm:block">Agency review desk</span>
            </span>
          </Link>
          <div
            className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 ring-1 ring-inset ring-emerald-600/20"
            title="Lead Desk never messages customers. You approve, then send the draft yourself."
          >
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
            <span className="hidden sm:inline">Human decides · nothing auto-sent</span>
            <span className="sm:hidden">No auto-send</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 sm:pb-12 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
