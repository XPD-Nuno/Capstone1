import { Link, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/toast";
import { LeadDetailPage } from "./pages/LeadDetailPage";
import { QueuePage } from "./pages/QueuePage";

function NotFound() {
  return (
    <div className="card px-6 py-14 text-center">
      <p className="font-semibold">Page not found</p>
      <Link to="/" className="mt-2 inline-block text-sm font-medium text-brand-700 hover:underline">
        Back to the lead queue
      </Link>
    </div>
  );
}

export function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<QueuePage />} />
          <Route path="leads/:leadId" element={<LeadDetailPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}
