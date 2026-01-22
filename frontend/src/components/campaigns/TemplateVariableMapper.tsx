import React, { useEffect, useState } from "react";
import { Template, AvailableFieldsResponse } from "../../types";

interface TemplateVariableMapperProps {
  template: Template | null;
  variableMapping: Record<string, string>;
  onChange: (mapping: Record<string, string>) => void;
  availableFields: AvailableFieldsResponse | null;
}

/**
 * Компонент для маппінгу змінних шаблону на поля контактів
 */
export const TemplateVariableMapper: React.FC<TemplateVariableMapperProps> = ({
  template,
  variableMapping,
  onChange,
  availableFields,
}) => {
  const [variables, setVariables] = useState<string[]>([]);

  useEffect(() => {
    if (!template) {
      setVariables([]);
      return;
    }

    // Витягуємо всі змінні з компонентів шаблону
    const vars = extractTemplateVariables(template);
    setVariables(vars);
  }, [template]);

  const handleMappingChange = (variable: string, field: string) => {
    const newMapping = { ...variableMapping };
    if (field) {
      newMapping[variable] = field;
    } else {
      delete newMapping[variable];
    }
    onChange(newMapping);
  };

  if (!template || variables.length === 0) {
    return null;
  }

  const allFields = [
    ...(availableFields?.standard_fields || []).map((f) => ({
      value: f,
      label: f,
      group: "Стандартні поля",
    })),
    ...(availableFields?.custom_fields || []).map((f) => ({
      value: `custom_data.${f}`,
      label: f,
      group: "Додаткові поля",
    })),
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">
          Прив'язка змінних шаблону
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Оберіть, які поля контактів підставляти в змінні шаблону
        </p>
      </div>

      <div className="space-y-3">
        {variables.map((variable) => (
          <div key={variable} className="flex items-center gap-3">
            <div className="w-32">
              <label className="text-sm text-gray-600">
                Змінна {`{{${variable}}}`}
              </label>
            </div>
            <div className="flex-1">
              <select
                value={variableMapping[variable] || ""}
                onChange={(e) => handleMappingChange(variable, e.target.value)}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              >
                <option value="">-- Оберіть поле --</option>
                {allFields.length > 0 ? (
                  <>
                    <optgroup label="Стандартні поля">
                      {allFields
                        .filter((f) => f.group === "Стандартні поля")
                        .map((field) => (
                          <option key={field.value} value={field.value}>
                            {field.label}
                          </option>
                        ))}
                    </optgroup>
                    <optgroup label="Додаткові поля">
                      {allFields
                        .filter((f) => f.group === "Додаткові поля")
                        .map((field) => (
                          <option key={field.value} value={field.value}>
                            {field.label}
                          </option>
                        ))}
                    </optgroup>
                  </>
                ) : (
                  <option value="" disabled>
                    Немає доступних полів
                  </option>
                )}
              </select>
            </div>
          </div>
        ))}
      </div>

      {availableFields && (
        <div className="text-xs text-gray-500 mt-2">
          Доступно полів: {availableFields.standard_fields.length} стандартних +{" "}
          {availableFields.custom_fields.length} додаткових (з{" "}
          {availableFields.total_contacts} контактів)
        </div>
      )}
    </div>
  );
};

/**
 * Витягує всі змінні з компонентів шаблону
 */
function extractTemplateVariables(template: Template): string[] {
  const variables = new Set<string>();

  for (const component of template.components) {
    if (component.type === "BODY" && component.text) {
      // Шукаємо всі {{1}}, {{2}}, тощо
      const matches = component.text.match(/\{\{(\d+)\}\}/g);
      if (matches) {
        matches.forEach((match) => {
          const varNum = match.replace(/[{}]/g, "");
          variables.add(varNum);
        });
      }
    }
  }

  // Повертаємо відсортовані змінні
  return Array.from(variables).sort((a, b) => parseInt(a) - parseInt(b));
}
