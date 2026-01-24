import React, { useState, useEffect, useRef } from "react";
import { QuickReply } from "../../types";
import { apiClient } from "../../api";
import { Zap, Search, X, Languages } from "lucide-react";
import { AVAILABLE_LANGUAGES } from "../../utils/languageDetector";

interface QuickReplyPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (text: string) => void;
  language?: string;
  buttonRef?: React.RefObject<HTMLButtonElement>;
}

const QuickReplyPicker: React.FC<QuickReplyPickerProps> = ({
  isOpen,
  onClose,
  onSelect,
  language = "pl",
  buttonRef,
}) => {
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredReplies, setFilteredReplies] = useState<QuickReply[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState(language);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ bottom: 0, left: 0 });

  // Оновлюємо мову при зміні пропсу
  useEffect(() => {
    setSelectedLanguage(language);
  }, [language]);

  useEffect(() => {
    if (isOpen) {
      loadQuickReplies();
      // Розраховуємо позицію відносно кнопки (зверху кнопки)
      if (buttonRef?.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        const windowHeight = window.innerHeight;
        setPosition({
          bottom: windowHeight - rect.top + 8,
          left: rect.left,
        });
      }
      // Фокус на поле пошуку при відкритті
      setTimeout(() => searchInputRef.current?.focus(), 100);
    } else {
      setSearchQuery("");
    }
  }, [isOpen, buttonRef]);

  useEffect(() => {
    // Фільтрація по title або shortcut
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const filtered = quickReplies.filter(
        (reply) =>
          reply.title.toLowerCase().includes(query)
      );
      setFilteredReplies(filtered);
    } else {
      setFilteredReplies(quickReplies);
    }
  }, [searchQuery, quickReplies]);

  // Закриття по кліку поза модальним вікном
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  const loadQuickReplies = async () => {
    setLoading(true);
    try {
      const replies = await apiClient.getQuickReplies();
      setQuickReplies(replies);
      setFilteredReplies(replies);
    } catch (error) {
      console.error("Failed to load quick replies:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (reply: QuickReply) => {
    try {
      // Отримуємо текст на потрібній мові
      const response = await apiClient.getQuickReplyText(reply.id, selectedLanguage);
      onSelect(response.text);
      onClose();
    } catch (error) {
      console.error("Failed to get quick reply text:", error);
      // Fallback - беремо текст на запитаній мові або першу доступну
      const text = reply.content[selectedLanguage] || Object.values(reply.content)[0] || "";
      if (text) {
        onSelect(text);
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  const currentLang = AVAILABLE_LANGUAGES.find(l => l.code === selectedLanguage);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Dropdown */}
      <div
        ref={modalRef}
        className="fixed z-50 bg-white rounded-lg shadow-xl border border-gray-200 flex flex-col"
        style={{
          bottom: `${position.bottom}px`,
          left: `${position.left}px`,
          width: "400px",
          maxHeight: "500px",
        }}
      >
        {/* Header with Language Selector */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">Швидкі відповіді</h3>

          <div className="flex items-center gap-2">
            {/* Language Dropdown */}
            <div className="relative group">
              <button className="flex items-center gap-1.5 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors">
                <Languages className="w-3.5 h-3.5" />
                <span className="font-medium">{currentLang?.flag} {selectedLanguage.toUpperCase()}</span>
              </button>

              <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10 min-w-[160px] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                {AVAILABLE_LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => setSelectedLanguage(lang.code)}
                    className={`w-full text-left px-3 py-1.5 hover:bg-gray-50 transition-colors flex items-center gap-2 text-xs ${selectedLanguage === lang.code ? "bg-blue-50 text-blue-600" : ""
                      }`}
                  >
                    <span>{lang.flag}</span>
                    <span>{lang.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Пошук..."
              className="w-full pl-8 pr-8 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500">
              <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2" />
              Завантаження...
            </div>
          ) : filteredReplies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-400">
              <Zap className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-sm">
                {searchQuery
                  ? "Нічого не знайдено"
                  : "Немає швидких відповідей"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredReplies.map((reply) => {
                const text =
                  reply.content?.[selectedLanguage] ||
                  Object.values(reply.content)[0] ||
                  "";
                return (
                  <button
                    key={reply.id}
                    onClick={() => handleSelect(reply)}
                    className="w-full text-left p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-gray-900">
                            {reply.title}
                          </h4>
                        </div>
                        <p className="text-xs text-gray-500 line-clamp-2 mt-1">
                          {text || "Немає тексту"}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default QuickReplyPicker;
