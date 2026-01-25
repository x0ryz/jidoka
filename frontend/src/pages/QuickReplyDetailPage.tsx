import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { QuickReply, QuickReplyUpdate } from '../types';
import { ArrowLeft, Calendar, Globe, Save, Trash2, AlertCircle } from 'lucide-react';

const QuickReplyDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [quickReply, setQuickReply] = useState<QuickReply | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Edit state
    const [title, setTitle] = useState('');
    const [content, setContent] = useState<Record<string, string>>({});
    const [newLang, setNewLang] = useState('');

    const isNewReply = id === 'new';

    useEffect(() => {
        if (isNewReply) {
            setLoading(false);
            setContent({ uk: '', en: '' }); // Default languages
        } else {
            loadQuickReply();
        }
    }, [id]);

    const loadQuickReply = async () => {
        if (!id || id === 'new') return;
        try {
            setLoading(true);
            const data = await apiClient.getQuickReplyById(id);
            setQuickReply(data);
            setTitle(data.title);
            setContent(data.content);
        } catch (err) {
            console.error('Failed to load quick reply:', err);
            setError('Failed to load quick reply');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!title.trim()) {
            setError('Title is required');
            return;
        }

        try {
            setSaving(true);
            setError(null);

            if (isNewReply) {
                const created = await apiClient.createQuickReply({ title, content });
                navigate(`/quick-replies/${created.id}`);
            } else if (id) {
                const updated = await apiClient.updateQuickReply(id, { title, content });
                setQuickReply(updated);
            }
        } catch (err: any) {
            console.error('Failed to save quick reply:', err);
            setError(err.response?.data?.detail || 'Failed to save quick reply');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!id || isNewReply) return;
        if (!confirm('Are you sure you want to delete this quick reply?')) return;

        try {
            await apiClient.deleteQuickReply(id);
            navigate('/quick-replies');
        } catch (err: any) {
            console.error('Failed to delete quick reply:', err);
            setError(err.response?.data?.detail || 'Failed to delete quick reply');
        }
    };

    const handleAddLanguage = () => {
        if (!newLang || content[newLang] !== undefined) {
            setError('Language already exists or invalid');
            return;
        }
        setContent({ ...content, [newLang]: '' });
        setNewLang('');
    };

    const handleRemoveLanguage = (lang: string) => {
        const updatedContent = { ...content };
        delete updatedContent[lang];
        setContent(updatedContent);
    };

    const handleContentChange = (lang: string, value: string) => {
        setContent({ ...content, [lang]: value });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-12rem)]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    if (error && !isNewReply && !quickReply) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <div>
                    <p className="text-red-900 font-medium">{error}</p>
                    <button onClick={() => navigate('/quick-replies')} className="text-sm text-red-700 underline mt-1">
                        Back to Quick Replies
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Breadcrumb / Back Button */}
            <button
                onClick={() => navigate('/quick-replies')}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors group"
            >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                Back to Quick Replies
            </button>

            {/* Header */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">
                            {isNewReply ? 'New Quick Reply' : 'Edit Quick Reply'}
                        </h1>
                        {!isNewReply && quickReply && (
                            <div className="flex items-center gap-4 text-sm text-gray-600">
                                <div className="flex items-center gap-1.5">
                                    <Calendar className="w-4 h-4" />
                                    <span>Created: {new Date(quickReply.created_at).toLocaleDateString()}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <Calendar className="w-4 h-4" />
                                    <span>Updated: {new Date(quickReply.updated_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {!isNewReply && (
                            <button
                                onClick={handleDelete}
                                className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
                            >
                                <Trash2 className="w-4 h-4" />
                                Delete
                            </button>
                        )}
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
                        >
                            <Save className="w-4 h-4" />
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-red-800">{error}</p>
                    </div>
                )}
            </div>

            {/* Title Section */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Title</h2>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter quick reply title..."
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
            </div>

            {/* Content Section */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Content (Multi-language)</h2>
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={newLang}
                            onChange={(e) => setNewLang(e.target.value.toLowerCase())}
                            placeholder="Language code (e.g., uk, en)"
                            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <button
                            onClick={handleAddLanguage}
                            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                            Add Language
                        </button>
                    </div>
                </div>

                <div className="space-y-4">
                    {Object.keys(content).length === 0 ? (
                        <p className="text-center text-gray-500 py-8">No languages added yet</p>
                    ) : (
                        Object.entries(content).map(([lang, text]) => (
                            <div key={lang} className="border border-gray-200 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <Globe className="w-4 h-4 text-gray-400" />
                                        <span className="text-sm font-semibold text-gray-700 uppercase">{lang}</span>
                                    </div>
                                    <button
                                        onClick={() => handleRemoveLanguage(lang)}
                                        className="text-xs text-red-600 hover:text-red-800"
                                    >
                                        Remove
                                    </button>
                                </div>
                                <textarea
                                    value={text}
                                    onChange={(e) => handleContentChange(lang, e.target.value)}
                                    placeholder={`Enter text in ${lang.toUpperCase()}...`}
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                                />
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default QuickReplyDetailPage;
