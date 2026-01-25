import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { QuickReply } from '../types';
import { Zap, Plus, Search } from 'lucide-react';

const QuickRepliesPage: React.FC = () => {
  const navigate = useNavigate();
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const loadQuickReplies = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getQuickReplies(searchQuery || undefined);
      setQuickReplies(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load quick replies:', error);
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    const debounce = setTimeout(() => {
      loadQuickReplies();
    }, 300);
    return () => clearTimeout(debounce);
  }, [loadQuickReplies]);

  const getLanguages = (content: Record<string, string>) => {
    return Object.keys(content).join(', ').toUpperCase();
  };

  const getPreviewText = (content: Record<string, string>) => {
    const firstLang = Object.keys(content)[0];
    return content[firstLang] || '';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quick Replies</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage reusable message templates for faster responses
          </p>
        </div>
        <button
          onClick={() => navigate('/quick-replies/new')}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          New Quick Reply
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search quick replies by title..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      {/* Quick Replies Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : quickReplies.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Zap className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No quick replies found</p>
          <p className="text-sm text-gray-400 mt-1">
            {searchQuery ? 'Try adjusting your search' : 'Create your first quick reply to get started'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quickReplies.map((reply) => {
            const languages = getLanguages(reply.content);
            const previewText = getPreviewText(reply.content);
            const langCount = Object.keys(reply.content).length;

            return (
              <div
                key={reply.id}
                onClick={() => navigate(`/quick-replies/${reply.id}`)}
                className="group bg-white rounded-xl border border-gray-200 p-6 cursor-pointer transition-all hover:shadow-lg hover:border-indigo-200 hover:-translate-y-1 flex flex-col"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <h3 className="font-semibold text-gray-900 truncate flex-1 pr-3 group-hover:text-indigo-700 transition-colors">
                    {reply.title}
                  </h3>
                  <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-100 font-medium flex-shrink-0">
                    {langCount} language{langCount === 1 ? '' : 's'}
                  </span>
                </div>

                {/* Languages */}
                <div className="mb-3 text-xs text-gray-500 font-medium">
                  {languages}
                </div>

                {/* Preview */}
                <p className="text-sm text-gray-600 line-clamp-3 bg-gray-50 p-3 rounded-lg border border-gray-100 mb-3">
                  {previewText}
                </p>

                {/* Footer - pinned to bottom */}
                <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-auto">
                  <span className="text-xs text-gray-400">
                    {new Date(reply.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    ID: {reply.id.slice(0, 8)}...
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default QuickRepliesPage;
