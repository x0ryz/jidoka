import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { Template } from '../types';
import { FileText } from 'lucide-react';

const TemplatesPage: React.FC = () => {
    const navigate = useNavigate();
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<string>('all');

    const loadTemplates = useCallback(async () => {
        try {
            setLoading(true);
            let data: Template[];
            if (statusFilter === 'all') {
                data = await apiClient.listTemplates();
            } else {
                data = await apiClient.getTemplatesByStatus(statusFilter);
            }
            setTemplates(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Failed to load templates:', error);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        loadTemplates();
    }, [loadTemplates]);

    const getStatusColor = (status: string) => {
        const statusLower = status.toLowerCase();
        if (statusLower.includes('approved')) {
            return 'bg-green-100 text-green-700 border-green-200';
        } else if (statusLower.includes('pending')) {
            return 'bg-yellow-100 text-yellow-700 border-yellow-200';
        } else if (statusLower.includes('rejected')) {
            return 'bg-red-100 text-red-700 border-red-200';
        }
        return 'bg-gray-100 text-gray-700 border-gray-200';
    };

    const getCategoryColor = (category: string) => {
        const categoryLower = category.toLowerCase();
        if (categoryLower === 'marketing') return 'bg-purple-50 text-purple-700';
        if (categoryLower === 'utility') return 'bg-blue-50 text-blue-700';
        if (categoryLower === 'authentication') return 'bg-orange-50 text-orange-700';
        return 'bg-gray-50 text-gray-700';
    };

    const filterButtons = [
        { label: 'All', value: 'all' },
        { label: 'Approved', value: 'APPROVED' },
        { label: 'Pending', value: 'PENDING' },
        { label: 'Rejected', value: 'REJECTED' },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Message Templates</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Manage and view your WhatsApp message templates
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {filterButtons.map((btn) => (
                        <button
                            key={btn.value}
                            onClick={() => setStatusFilter(btn.value)}
                            className={`px-3 py-1.5 text-sm rounded-lg transition-all ${statusFilter === btn.value
                                ? 'bg-indigo-600 text-white shadow-sm'
                                : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                                }`}
                        >
                            {btn.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Templates Grid */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
                </div>
            ) : templates.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                    <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">No templates found</p>
                    <p className="text-sm text-gray-400 mt-1">
                        {statusFilter !== 'all' ? 'Try changing the filter' : 'Sync your templates from Meta'}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {templates.map((template) => {
                        const bodyComponent = template.components?.find((c: any) => c.type === 'BODY');
                        const previewText = bodyComponent?.text || '';

                        return (
                            <div
                                key={template.id}
                                onClick={() => navigate(`/templates/${template.id}`)}
                                className={`group bg-white rounded-xl border border-gray-200 p-6 cursor-pointer transition-all hover:shadow-lg hover:border-indigo-200 hover:-translate-y-1 flex flex-col ${template.is_deleted ? 'opacity-60' : ''
                                    }`}
                            >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex-1 min-w-0 pr-3">
                                        <h3 className="font-semibold text-gray-900 truncate mb-2 group-hover:text-indigo-700 transition-colors">
                                            {template.name}
                                        </h3>
                                        {template.is_deleted && (
                                            <span className="inline-block text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded border border-red-200 font-medium">
                                                Deleted
                                            </span>
                                        )}
                                    </div>
                                    <span className={`text-xs px-2 py-0.5 rounded border font-medium flex-shrink-0 ${getStatusColor(template.status)}`}>
                                        {template.status}
                                    </span>
                                </div>

                                {/* Meta Info */}
                                <div className="flex items-center gap-3 mb-3 text-xs text-gray-500">
                                    <span className={`px-2 py-1 rounded ${getCategoryColor(template.category)}`}>
                                        {template.category}
                                    </span>
                                    <span className="font-medium">{template.language}</span>
                                </div>

                                {/* Preview */}
                                {previewText && (
                                    <p className="text-sm text-gray-600 line-clamp-3 bg-gray-50 p-3 rounded-lg border border-gray-100 mb-3">
                                        {previewText}
                                    </p>
                                )}

                                {/* Footer */}
                                <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-auto">
                                    <span className="text-xs text-gray-400">
                                        {template.components?.length || 0} component{template.components?.length === 1 ? '' : 's'}
                                    </span>
                                    <span className="text-xs text-gray-400 font-mono">
                                        ID: {template.meta_template_id?.slice(0, 8)}...
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

export default TemplatesPage;
