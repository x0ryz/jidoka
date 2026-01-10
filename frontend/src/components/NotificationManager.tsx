import { useLocation, useSearchParams } from "react-router-dom"; // 1. Додаємо імпорти
import toast, { Toaster } from "react-hot-toast";
import { useWSEvent } from "../services/useWebSocket";
import { EventType } from "../services/websocket";

const truncate = (str: string, length: number) => {
  if (!str) return "";
  return str.length > length ? str.substring(0, length) + "..." : str;
};

export const NotificationManager = () => {
  // 2. Отримуємо поточний URL та параметри
  const location = useLocation();
  const [searchParams] = useSearchParams();

  useWSEvent(EventType.NEW_MESSAGE, (data) => {
    // 3. Отримуємо ID відкритого контакту з URL (підставте свій параметр, наприклад 'id' або 'contactId')
    const activeContactId =
      searchParams.get("id") || searchParams.get("contact_id");

    // 4. Перевіряємо: чи ми на сторінці контактів І чи відкритий саме цей чат
    const isChatOpen =
      location.pathname.includes("/contacts") &&
      activeContactId === data.contact_id;

    // Якщо чат відкритий — виходимо і НЕ показуємо тост
    if (isChatOpen) {
      return;
    }

    // Стандартна логіка відображення
    const phone = data.phone || data.contact?.phone_number || "Невідомий";
    const body =
      data.body || (data.type === "image" ? "[Зображення]" : "[Повідомлення]");

    toast.success(
      <div>
        <p className="font-bold text-sm">Нове повідомлення</p>
        <p className="text-xs text-gray-600">Від: {phone}</p>
        <p className="text-sm mt-1">{truncate(body, 50)}</p>
      </div>,
      { duration: 4000 },
    );
  });

  // ... (решта коду без змін: CAMPAIGN_COMPLETED і т.д.)

  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        className: "bg-white shadow-lg border border-gray-100",
        style: {
          padding: "16px",
          color: "#333",
        },
      }}
    />
  );
};
