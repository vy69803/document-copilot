import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ChatLayout } from "@/components/layout/ChatLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";
import { LoginPage } from "@/pages/auth/Login";
import { ChatPage } from "@/pages/chat/ChatPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TooltipProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated workspace routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<ChatLayout />}>
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/chat/:threadId" element={<ChatPage />} />
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </TooltipProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

