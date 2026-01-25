import React from "react";
import Navigation from "./Navigation";
import { useWebSocket } from "../services/useWebSocket";
import { NotificationManager } from "./NotificationManager"; // <-- Імпорт

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isConnected } = useWebSocket();

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Navigation />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Підключаємо менеджер сповіщень тут */}
        <NotificationManager />

        {!isConnected && (
          <div className="bg-red-500 text-white text-xs p-1 text-center font-medium shadow-sm z-10">
            З'єднання з сервером втрачено. Спроба відновлення...
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-8 scroll-smooth">
          <div className="max-w-[1600px] mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
