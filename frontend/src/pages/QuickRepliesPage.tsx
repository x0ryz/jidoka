import React, { useState, useEffect } from "react";
import { QuickReply, QuickReplyCreate, QuickReplyUpdate } from "../types";
import { apiClient } from "../api";
import {
  Zap,
  Plus,
  Edit2,
  Trash2,
  Search,
  X,
  Globe,
  Save,
  Languages,
} from "lucide-react";

const QuickRepliesPage: React.FC = () => {
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredReplies, setFilteredReplies] = useState<QuickReply[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingReply, setEditingReply] = useState<QuickReply | null>(null);

  useEffect(() => {
    loadQuickReplies();
  }, []);

  useEffect(() => {
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

  const handleDelete = async (id: string) => {
    if (!confirm("Ви впевнені, що хочете видалити цю швидку відповідь?")) {
      return;
    }

    try {
      await apiClient.deleteQuickReply(id);
      loadQuickReplies();
    } catch (error) {
      console.error("Failed to delete quick reply:", error);
      alert("Не вдалося видалити швидку відповідь");
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)]">
      <div className="h-full border border-gray-200 rounded-lg bg-white overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">

            <h2 className="text-lg font-semibold text-gray-800">Швидкі відповіді</h2>

            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Додати
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Пошук за назвою..."
              className="w-full pl-9 pr-9 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-500">
              <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2" />
              Завантаження...
            </div>
          ) : filteredReplies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Zap className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">
                {searchQuery
                  ? "Нічого не знайдено"
                  : "Немає швидких відповідей"}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setIsCreateModalOpen(true)}
                  className="mt-3 text-sm text-blue-600 hover:text-blue-700 underline"
                >
                  Створити першу відповідь
                </button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredReplies.map((reply) => (
                <QuickReplyItem
                  key={reply.id}
                  reply={reply}
                  onEdit={() => setEditingReply(reply)}
                  onDelete={() => handleDelete(reply.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {(isCreateModalOpen || editingReply) && (
        <QuickReplyModal
          reply={editingReply}
          onClose={() => {
            setIsCreateModalOpen(false);
            setEditingReply(null);
          }}
          onSave={() => {
            loadQuickReplies();
            setIsCreateModalOpen(false);
            setEditingReply(null);
          }}
        />
      )}
    </div>
  );
};

// Quick Reply Item Component
interface QuickReplyItemProps {
  reply: QuickReply;
  onEdit: () => void;
  onDelete: () => void;
}

const QuickReplyItem: React.FC<QuickReplyItemProps> = ({
  reply,
  onEdit,
  onDelete,
}) => {
  const languages = Object.keys(reply.content || {});
  const previewText = Object.values(reply.content)[0] || "";

  return (
    <div className="p-4 hover:bg-gray-50 transition-colors cursor-pointer" onClick={onEdit}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900">
              {reply.title}
            </h3>
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Languages className="w-3 h-3" />
              <span>{languages.length}</span>
            </div>
          </div>
          <p className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-2">
            {previewText}
          </p>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {languages.map((lang) => (
              <span
                key={lang}
                className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded"
                title={reply.content?.[lang]}
              >
                {lang}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Редагувати"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Видалити"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Quick Reply Modal Component
interface QuickReplyModalProps {
  reply: QuickReply | null;
  onClose: () => void;
  onSave: () => void;
}

const QuickReplyModal: React.FC<QuickReplyModalProps> = ({
  reply,
  onClose,
  onSave,
}) => {
  const [title, setTitle] = useState(reply?.title || "");
  const [content, setContent] = useState<Record<string, string>>(
    reply?.content || { pl: "" }
  );
  const [saving, setSaving] = useState(false);
  const [currentLang, setCurrentLang] = useState("pl");
  const [newLang, setNewLang] = useState("");

  const languages = Object.keys(content);

  const handleSave = async () => {
    if (!title.trim()) {
      alert("Заповніть всі обов'язкові поля");
      return;
    }

    if (Object.keys(content).length === 0) {
      alert("Додайте хоча б одну мову");
      return;
    }

    setSaving(true);
    try {
      const data = {
        title: title.trim(),
        content,
      };

      if (reply) {
        await apiClient.updateQuickReply(reply.id, data);
      } else {
        await apiClient.createQuickReply(data as QuickReplyCreate);
      }

      onSave();
    } catch (error: any) {
      console.error("Failed to save quick reply:", error);
      alert(
        error.response?.data?.detail ||
        "Не вдалося зберегти швидку відповідь"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleAddLanguage = () => {
    if (newLang && !languages.includes(newLang)) {
      setContent({ ...content, [newLang]: "" });
      setCurrentLang(newLang);
      setNewLang("");
    }
  };

  const handleRemoveLanguage = (lang: string) => {
    if (languages.length === 1) {
      alert("Не можна видалити останню мову");
      return;
    }
    const newContent = { ...content };
    delete newContent[lang];
    setContent(newContent);
    if (currentLang === lang) {
      setCurrentLang(Object.keys(newContent)[0]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            {reply ? "Редагувати" : "Створити"} швидку відповідь
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">


          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Назва <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Привітання"
              maxLength={100}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Language Tabs */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Тексти <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {languages.map((lang) => (
                <div key={lang} className="flex items-center gap-1">
                  <button
                    onClick={() => setCurrentLang(lang)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${currentLang === lang
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                  >
                    {lang}
                  </button>
                  {languages.length > 1 && (
                    <button
                      onClick={() => handleRemoveLanguage(lang)}
                      className="p-0.5 text-red-500 hover:bg-red-50 rounded"
                      title="Видалити мову"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
              {/* Add Language */}
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  value={newLang}
                  onChange={(e) =>
                    setNewLang(e.target.value.toLowerCase().slice(0, 5))
                  }
                  placeholder="en"
                  className="w-14 px-2 py-1 border border-gray-300 rounded text-xs"
                  maxLength={5}
                />
                <button
                  onClick={handleAddLanguage}
                  disabled={!newLang || languages.includes(newLang)}
                  className="p-0.5 text-green-600 hover:bg-green-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Додати мову"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Text Area */}
            <textarea
              value={content[currentLang] || ""}
              onChange={(e) =>
                setContent({ ...content, [currentLang]: e.target.value })
              }
              placeholder={`Введіть текст для мови "${currentLang}"...`}
              rows={6}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
            <p className="text-xs text-gray-500 mt-1">
              {content[currentLang]?.length || 0} символів
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Скасувати
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !title.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Збереження...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Зберегти
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default QuickRepliesPage;
