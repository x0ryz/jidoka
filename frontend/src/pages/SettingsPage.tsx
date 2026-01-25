import React, { useState, useEffect } from 'react';
import { apiClient } from '../api';
import { WabaSettingsResponse } from '../types';
import { Settings, Globe, Database, Save, RefreshCw, AlertCircle, Check } from 'lucide-react';

interface WabaSettings {
  waba_id: string;
  name: string;
  access_token?: string;
  app_secret?: string;
  verify_token?: string;
  graph_api_version?: string;
}

const SettingsPage: React.FC = () => {
  const [account, setAccount] = useState<WabaSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const [formData, setFormData] = useState<WabaSettings>({
    waba_id: '',
    name: 'Golden Cars',
    access_token: '',
    app_secret: '',
    verify_token: '',
    graph_api_version: 'v21.0',
  });

  useEffect(() => {
    loadAccountData();
  }, []);

  const loadAccountData = async () => {
    try {
      setLoading(true);
      setError(null);

      const settings = await apiClient.getWabaSettings();

      if (settings) {
        setAccount(settings);
        setFormData({
          waba_id: settings.waba_id || '',
          name: settings.name || 'Golden Cars',
          access_token: '',
          app_secret: '',
          verify_token: '',
          graph_api_version: settings.graph_api_version || 'v21.0',
        });
      }
    } catch (err: any) {
      console.error('Failed to load settings:', err);
      if (err.response?.status !== 404) {
        setError('Failed to load account data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setSuccess(false);
  };

  const handleSync = async () => {
    try {
      setIsSyncing(true);
      setError(null);
      setSuccess(false);

      await apiClient.triggerWabaSync();

      setSuccess(true);
      setTimeout(() => loadAccountData(), 2000);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to trigger sync:', err);
      setError(err.response?.data?.detail || 'Failed to sync');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!formData.waba_id.trim()) {
      setError('WABA ID is required');
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      setSuccess(false);

      const payload: any = {
        waba_id: formData.waba_id.trim(),
        name: formData.name.trim(),
        graph_api_version: formData.graph_api_version,
      };

      if (formData.access_token?.trim()) payload.access_token = formData.access_token.trim();
      if (formData.app_secret?.trim()) payload.app_secret = formData.app_secret.trim();
      if (formData.verify_token?.trim()) payload.verify_token = formData.verify_token.trim();

      const response = await apiClient.updateWabaSettings(payload);

      setAccount(response);
      setSuccess(true);

      setFormData((prev) => ({
        ...prev,
        access_token: '',
        app_secret: '',
        verify_token: '',
      }));

      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update settings:', err);
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure WhatsApp Business API and system settings
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={isSyncing}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          {isSyncing ? 'Syncing...' : 'Sync WABA'}
        </button>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-900">Error</h3>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl flex items-start gap-3">
          <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-green-900">Success</h3>
            <p className="text-sm text-green-700">Settings saved successfully</p>
          </div>
        </div>
      )}

      {/* WABA Configuration */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-green-50 rounded-lg">
            <Globe className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">WhatsApp Business Account</h2>
            <p className="text-sm text-gray-500">Configure your WABA credentials</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="waba_id" className="block text-sm font-medium text-gray-700 mb-2">
                WABA ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="waba_id"
                name="waba_id"
                value={formData.waba_id}
                onChange={handleInputChange}
                placeholder="1234567890"
                required
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <p className="mt-1 text-xs text-gray-500">WhatsApp Business Account ID from Meta</p>
            </div>

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                Business Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Golden Cars"
                required
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label htmlFor="access_token" className="block text-sm font-medium text-gray-700 mb-2">
              Access Token
            </label>
            <input
              type="password"
              id="access_token"
              name="access_token"
              value={formData.access_token}
              onChange={handleInputChange}
              placeholder="Leave empty if not changing"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">System User Access Token from Meta Business Manager</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="app_secret" className="block text-sm font-medium text-gray-700 mb-2">
                App Secret
              </label>
              <input
                type="password"
                id="app_secret"
                name="app_secret"
                value={formData.app_secret}
                onChange={handleInputChange}
                placeholder="Leave empty if not changing"
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="verify_token" className="block text-sm font-medium text-gray-700 mb-2">
                Verify Token
              </label>
              <input
                type="password"
                id="verify_token"
                name="verify_token"
                value={formData.verify_token}
                onChange={handleInputChange}
                placeholder="Leave empty if not changing"
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label htmlFor="graph_api_version" className="block text-sm font-medium text-gray-700 mb-2">
              Graph API Version
            </label>
            <input
              type="text"
              id="graph_api_version"
              name="graph_api_version"
              value={formData.graph_api_version}
              onChange={handleInputChange}
              placeholder="v21.0"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>

      {/* System Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-purple-50 rounded-lg">
            <Database className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">System Information</h2>
            <p className="text-sm text-gray-500">Current system status and configuration</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Database Status</p>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm font-medium text-gray-900">Connected</span>
            </div>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Message Broker</p>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm font-medium text-gray-900">NATS Connected</span>
            </div>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">API Version</p>
            <span className="text-sm font-medium text-gray-900">v1.0.0</span>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Environment</p>
            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded border border-blue-200 font-medium">
              Development
            </span>
          </div>
        </div>
      </div>

      {/* Security Notice */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-50 rounded-lg">
            <Settings className="w-5 h-5 text-blue-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Security & Information</h2>
        </div>

        <div className="space-y-2 text-sm text-gray-600">
          <p>• Tokens and secrets are automatically encrypted when saved</p>
          <p>• Token fields are cleared after saving for security</p>
          <p>• Sync updates account and phone number information from Meta</p>
          <p>
            • Visit{' '}
            <a
              href="https://developers.facebook.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:underline font-medium"
            >
              Meta for Developers
            </a>{' '}
            to obtain your credentials
          </p>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
