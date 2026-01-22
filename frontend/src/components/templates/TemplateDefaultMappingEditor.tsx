import React, { useState, useEffect } from 'react';
import { Template } from '../../types';
import { apiClient } from '../../api';

interface TemplateDefaultMappingEditorProps {
  template: Template;
  onUpdate: (template: Template) => void;
}

const TemplateDefaultMappingEditor: React.FC<TemplateDefaultMappingEditorProps> = ({
  template,
  onUpdate,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [mapping, setMapping] = useState<Record<string, string>>(
    template.default_variable_mapping || {}
  );
  const [availableFields, setAvailableFields] = useState<
    Array<{ value: string; label: string; group: string }>
  >([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadAvailableFields();
  }, []);

  useEffect(() => {
    setMapping(template.default_variable_mapping || {});
  }, [template]);

  const loadAvailableFields = async () => {
    try {
      const response = await apiClient.getAvailableFields();
      const fields = [];

      // Standard fields
      for (const field of response.standard_fields) {
        fields.push({
          value: field,
          label: field === 'name' ? "Ім'я" : field === 'phone_number' ? 'Телефон' : field,
          group: 'Стандартні поля',
        });
      }

      // Custom fields
      for (const field of response.custom_fields) {
        fields.push({
          value: `custom_data.${field}`,
          label: field,
          group: 'Додаткові поля',
        });
      }

      setAvailableFields(fields);
    } catch (error) {
      console.error('Помилка завантаження полів:', error);
    }
  };

  const extractVariables = (): string[] => {
    const variables: string[] = [];
    const bodyComponent = template.components.find((c) => c.type === 'BODY');
    if (bodyComponent?.text) {
      const matches = bodyComponent.text.match(/\{\{(\d+)\}\}/g);
      if (matches) {
        matches.forEach((match) => {
          const num = match.replace(/\{\{|\}\}/g, '');
          if (!variables.includes(num)) {
            variables.push(num);
          }
        });
      }
    }
    return variables.sort((a, b) => parseInt(a) - parseInt(b));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updatedTemplate = await apiClient.updateTemplate(template.id, {
        default_variable_mapping: Object.keys(mapping).length > 0 ? mapping : undefined,
      });
      onUpdate(updatedTemplate);
      setIsEditing(false);
    } catch (error) {
      console.error('Помилка збереження маппінгу:', error);
    } finally {
      setSaving(false);
    }
  };

  const variables = extractVariables();

  if (variables.length === 0) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-sm text-gray-600">
          Цей шаблон не містить змінних для підстановки
        </p>
      </div>
    );
  }

  if (!isEditing) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-medium text-gray-900">Дефолтний маппінг змінних</h4>
          <button
            onClick={() => setIsEditing(true)}
            className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            {Object.keys(mapping).length > 0 ? 'Редагувати' : 'Налаштувати'}
          </button>
        </div>

        {Object.keys(mapping).length > 0 ? (
          <div className="space-y-2">
            {variables.map((varIndex) => (
              <div key={varIndex} className="text-sm">
                <span className="font-mono text-blue-600">{`{{${varIndex}}}`}</span>
                <span className="text-gray-400 mx-2">→</span>
                <span className="text-gray-700">
                  {mapping[varIndex]
                    ? availableFields.find((f) => f.value === mapping[varIndex])?.label ||
                      mapping[varIndex]
                    : '-'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Маппінг не налаштовано</p>
        )}
      </div>
    );
  }

  const groupedFields = availableFields.reduce(
    (acc, field) => {
      if (!acc[field.group]) {
        acc[field.group] = [];
      }
      acc[field.group].push(field);
      return acc;
    },
    {} as Record<string, typeof availableFields>
  );

  return (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-medium text-gray-900">Налаштування маппінгу</h4>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setMapping(template.default_variable_mapping || {});
              setIsEditing(false);
            }}
            disabled={saving}
            className="text-sm px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors disabled:opacity-50"
          >
            Скасувати
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {saving ? 'Збереження...' : 'Зберегти'}
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {variables.map((varIndex) => (
          <div key={varIndex} className="flex items-center gap-3">
            <span className="font-mono text-blue-600 min-w-[60px]">{`{{${varIndex}}}`}</span>
            <span className="text-gray-400">→</span>
            <select
              value={mapping[varIndex] || ''}
              onChange={(e) =>
                setMapping({ ...mapping, [varIndex]: e.target.value })
              }
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">Не вибрано</option>
              {Object.entries(groupedFields).map(([group, fields]) => (
                <optgroup key={group} label={group}>
                  {fields.map((field) => (
                    <option key={field.value} value={field.value}>
                      {field.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-500 mt-3">
        Цей маппінг буде автоматично підставлятися при створенні нової кампанії з цим шаблоном
      </p>
    </div>
  );
};

export default TemplateDefaultMappingEditor;
