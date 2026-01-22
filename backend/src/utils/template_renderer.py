"""Template parameter rendering utilities."""


def count_template_parameters(template_components: list[dict]) -> int:
    """
    Count the number of parameters in a template body component.

    Args:
        template_components: Template components from Meta API

    Returns:
        Number of parameters expected by the template
    """
    for component in template_components:
        if component.get("type") == "BODY":
            # Count {{N}} placeholders in the text
            text = component.get("text", "")
            # Find all {{1}}, {{2}}, etc.
            import re
            matches = re.findall(r'\{\{(\d+)\}\}', text)
            if matches:
                # Return the highest number (template expects 1, 2, 3, ...)
                return max(int(m) for m in matches)
    return 0


def render_template_params(
    variable_mapping: dict[str, str] | None,
    contact_data: dict,
) -> list[dict]:
    """
    Render template parameters by replacing variables with contact data.

    Args:
        variable_mapping: Dict mapping variable indices to contact field names
                         e.g., {"1": "name", "2": "custom_data.city"}
        contact_data: Contact data including name, phone_number, and custom_data

    Returns:
        List of template parameters in Meta API format
        [{"type": "text", "text": "John"}, {"type": "text", "text": "New York"}]
    """
    if not variable_mapping:
        return []

    # Sort by variable index to maintain order
    sorted_vars = sorted(variable_mapping.items(), key=lambda x: int(x[0]))

    params = []
    for var_index, field_path in sorted_vars:
        # Get value from contact data
        value = get_nested_value(contact_data, field_path)

        # Default to "-" if value not found (Meta API rejects empty strings)
        if value is None or value == "":
            value = "-"

        params.append({
            "type": "text",
            "text": str(value),
        })

    return params


def get_nested_value(data: dict, field_path: str) -> str | None:
    """
    Get value from nested dict using dot notation.

    Examples:
        - "name" -> data["name"]
        - "custom_data.city" -> data["custom_data"]["city"]

    Args:
        data: Source data dictionary
        field_path: Dot-separated path to the field

    Returns:
        Field value or None if not found
    """
    from typing import Any

    keys = field_path.split(".")
    value: Any = data

    try:
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None
        return value
    except (KeyError, TypeError, AttributeError):
        return None
