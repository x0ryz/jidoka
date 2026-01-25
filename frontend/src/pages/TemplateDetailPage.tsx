import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { Template } from '../types';
import { ArrowLeft, Calendar, Globe, Tag, FileText, AlertCircle } from 'lucide-react';
import TemplateDefaultMappingEditor from '../components/templates/TemplateDefaultMappingEditor';

const TemplateDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [template, setTemplate] = useState<Template | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadTemplate = async () => {
            if (!id) return;
            try {
                setLoading(true);
                const data = await apiClient.getTemplate(id);
                setTemplate(data);
            } catch (err) {
                console.error('Failed to load template:', err);
                setError('Failed to load template details');
            } finally {
                setLoading(false);
            }
        };
        loadTemplate();
    }, [id]);

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

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-12rem)]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    if (error || !template) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <div>
                    <p className="text-red-900 font-medium">{error || 'Template not found'}</p>
                    <button onClick={() => navigate('/templates')} className="text-sm text-red-700 underline mt-1">
                        Back to Templates
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Breadcrumb / Back Button */}
            <button
                onClick={() => navigate('/templates')}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors group"
            >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                Back to Templates
            </button>

            {/* Header */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                            <h1 className="text-2xl font-bold text-gray-900">{template.name}</h1>
                            {template.is_deleted && (
                                <span className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded-lg border border-red-200 font-medium">
                                    Deleted from Meta
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1.5">
                                <Globe className="w-4 h-4" />
                                <span className="font-medium">Language:</span> {template.language}
                            </div>
                            <div className="flex items-center gap-1.5">
                                <Tag className="w-4 h-4" />
                                <span className="font-medium">Category:</span> {template.category}
                            </div>
                        </div>
                    </div>
                    <span className={`text-sm px-3 py-1.5 rounded-lg border font-medium ${getStatusColor(template.status)}`}>
                        {template.status}
                    </span>
                </div>

                {/* Meta Info Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div>
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Meta Template ID</span>
                        <p className="text-sm text-gray-900 font-mono mt-1">{template.meta_template_id}</p>
                    </div>
                    <div>
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">WABA ID</span>
                        <p className="text-sm text-gray-900 font-mono mt-1">{template.waba_id}</p>
                    </div>
                    <div>
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Created
                        </span>
                        <p className="text-sm text-gray-900 mt-1">
                            {new Date(template.created_at).toLocaleString('en-US', {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                            })}
                        </p>
                    </div>
                    <div>
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Updated
                        </span>
                        <p className="text-sm text-gray-900 mt-1">
                            {new Date(template.updated_at).toLocaleString('en-US', {
                                day: '2-digit',
                                month: 'short',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                            })}
                        </p>
                    </div>
                </div>

                {/* Sync Status */}
                {template.is_deleted && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                        <div className="text-sm text-red-800">
                            <p className="font-medium">This template has been deleted from Meta</p>
                            <p className="text-red-700 mt-0.5">It remains in history but cannot be used for new campaigns.</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Default Variable Mapping */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                    <FileText className="w-5 h-5 text-gray-500" />
                    <h2 className="text-lg font-semibold text-gray-900">Default Variable Mapping</h2>
                </div>
                <TemplateDefaultMappingEditor
                    template={template}
                    onUpdate={(updatedTemplate) => {
                        setTemplate(updatedTemplate);
                    }}
                />
            </div>

            {/* Template Components */}
            {template.components && template.components.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <FileText className="w-5 h-5 text-gray-500" />
                        <h2 className="text-lg font-semibold text-gray-900">Template Components</h2>
                    </div>
                    <div className="space-y-4">
                        {template.components.map((component: any, index: number) => (
                            <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                {/* Component Type Badge */}
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="inline-block px-2.5 py-1 text-xs font-semibold bg-indigo-100 text-indigo-800 rounded-md">
                                        {component.type}
                                    </span>
                                    {component.format && (
                                        <span className="inline-block px-2.5 py-1 text-xs bg-gray-200 text-gray-700 rounded-md">
                                            {component.format}
                                        </span>
                                    )}
                                </div>

                                {/* Text Content */}
                                {component.text && (
                                    <div className="mt-3">
                                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Text:</p>
                                        <p className="text-sm text-gray-900 whitespace-pre-wrap bg-white p-3 rounded-lg border border-gray-200">
                                            {component.text}
                                        </p>
                                    </div>
                                )}

                                {/* Example */}
                                {component.example && (
                                    <div className="mt-3">
                                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Example:</p>
                                        <div className="text-sm text-gray-600 bg-white p-3 rounded-lg border border-gray-200">
                                            <pre className="whitespace-pre-wrap font-mono text-xs">{JSON.stringify(component.example, null, 2)}</pre>
                                        </div>
                                    </div>
                                )}

                                {/* Buttons */}
                                {component.buttons && component.buttons.length > 0 && (
                                    <div className="mt-3">
                                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Buttons:</p>
                                        <div className="space-y-2">
                                            {component.buttons.map((button: any, btnIndex: number) => (
                                                <div key={btnIndex} className="bg-white p-3 rounded-lg border border-gray-200 text-sm flex items-center justify-between">
                                                    <span className="font-medium text-gray-700">{button.type}</span>
                                                    <span className="text-gray-900">{button.text || button.url || button.phone_number}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Full JSON (Collapsed) */}
                                <details className="mt-3">
                                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 font-medium">
                                        View Full JSON
                                    </summary>
                                    <pre className="text-xs text-gray-600 mt-2 p-3 bg-white rounded-lg border border-gray-200 overflow-x-auto font-mono">
                                        {JSON.stringify(component, null, 2)}
                                    </pre>
                                </details>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TemplateDetailPage;
