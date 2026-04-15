"""
Tool: Notion Portfolio — шаблон и запись в базу данных.

Назначение:
  Формирует детерминированный payload для портфолио и, если настроен Notion,
  создает страницу в выбранной database с мягким schema-mapping.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"


def _normalize_technologies(technologies: list[str] | None) -> list[str]:
    if not technologies:
        return []
    return [item.strip() for item in technologies if item and item.strip()]


def _normalize_name(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _property_matches(property_name: str, aliases: tuple[str, ...]) -> bool:
    normalized = _normalize_name(property_name)
    return normalized in {_normalize_name(alias) for alias in aliases}


def _notion_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _is_placeholder(value: str | None, placeholder: str) -> bool:
    return not value or value == placeholder


def _build_rich_text(text: str) -> list[dict]:
    if not text:
        return []
    chunks = [text[i:i + 1900] for i in range(0, len(text), 1900)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def _first_database_title(database: dict) -> str:
    title = database.get("title", [])
    if title:
        return "".join(part.get("plain_text", "") for part in title).strip()
    return ""


def build_portfolio_template(
    title: str,
    description: str,
    category: str = "other",
    technologies: list[str] | None = None,
    result_url: str | None = None,
    source: str = "manual",
    status: str = "draft",
) -> dict:
    tech_list = _normalize_technologies(technologies)

    payload = {
        "Title": title,
        "Description": description,
        "Category": category,
        "Technologies": tech_list,
        "Result URL": result_url or "",
        "Status": status,
        "Source": source,
    }

    preview_lines = [
        f"# {title}",
        "",
        f"Status: {status}",
        f"Category: {category}",
        f"Source: {source}",
    ]

    if tech_list:
        preview_lines.append(f"Technologies: {', '.join(tech_list)}")

    if result_url:
        preview_lines.append(f"Result URL: {result_url}")

    preview_lines.extend(["", description])

    return {
        "ok": True,
        "template": payload,
        "preview": "\n".join(preview_lines),
    }


def _find_title_property(properties: dict) -> str | None:
    for property_name, meta in properties.items():
        if meta.get("type") == "title":
            return property_name
    return None


def _find_property_by_alias(properties: dict, expected_type: str, aliases: tuple[str, ...]) -> str | None:
    for property_name, meta in properties.items():
        if meta.get("type") == expected_type and _property_matches(property_name, aliases):
            return property_name
    return None


def _set_property_value(target: dict, property_name: str | None, property_type: str, value):
    if not property_name:
        return
    if property_type == "title":
        target[property_name] = {"title": _build_rich_text(str(value))}
    elif property_type == "rich_text":
        target[property_name] = {"rich_text": _build_rich_text(str(value))}
    elif property_type == "select":
        target[property_name] = {"select": {"name": str(value)}}
    elif property_type == "multi_select":
        target[property_name] = {"multi_select": [{"name": item} for item in value]}
    elif property_type == "url":
        target[property_name] = {"url": str(value)}


def _build_page_children(template: dict, included_property_names: set[str]) -> list[dict]:
    lines = []

    if "Description" not in included_property_names and template["Description"]:
        lines.append(template["Description"])
    if "Technologies" not in included_property_names and template["Technologies"]:
        lines.append(f"Technologies: {', '.join(template['Technologies'])}")
    if "Category" not in included_property_names and template["Category"]:
        lines.append(f"Category: {template['Category']}")
    if "Status" not in included_property_names and template["Status"]:
        lines.append(f"Status: {template['Status']}")
    if "Source" not in included_property_names and template["Source"]:
        lines.append(f"Source: {template['Source']}")
    if "Result URL" not in included_property_names and template["Result URL"]:
        lines.append(f"Result URL: {template['Result URL']}")

    children = []
    for line in lines:
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _build_rich_text(line)},
            }
        )
    return children


def create_notion_portfolio_page(
    title: str,
    description: str,
    category: str = "other",
    technologies: list[str] | None = None,
    result_url: str | None = None,
    source: str = "manual",
    status: str = "draft",
    database_id: str | None = None,
) -> dict:
    template_result = build_portfolio_template(
        title=title,
        description=description,
        category=category,
        technologies=technologies,
        result_url=result_url,
        source=source,
        status=status,
    )
    template = template_result["template"]

    api_key = os.environ.get("NOTION_API_KEY")
    database_id = database_id or os.environ.get("NOTION_DATABASE_ID")

    if _is_placeholder(api_key, "secret_your-notion-key"):
        return {
            "ok": True,
            "status": "skipped",
            "page_id": None,
            "url": None,
            "error": None,
            "reason": "NOTION_API_KEY не настроен",
            "template": template,
            "preview": template_result["preview"],
        }

    if _is_placeholder(database_id, "your-database-id"):
        return {
            "ok": True,
            "status": "skipped",
            "page_id": None,
            "url": None,
            "error": None,
            "reason": "NOTION_DATABASE_ID не настроен",
            "template": template,
            "preview": template_result["preview"],
        }

    try:
        database_response = requests.get(
            f"{NOTION_API_BASE}/databases/{database_id}",
            headers=_notion_headers(api_key),
            timeout=15,
        )
        if database_response.status_code != 200:
            return {
                "ok": False,
                "status": "error",
                "page_id": None,
                "url": None,
                "error": f"Не удалось прочитать Notion database: {database_response.status_code}",
                "reason": None,
                "template": template,
                "preview": template_result["preview"],
            }

        database = database_response.json()
        properties = database.get("properties", {})
        title_property = _find_title_property(properties)
        if not title_property:
            return {
                "ok": False,
                "status": "error",
                "page_id": None,
                "url": None,
                "error": "В Notion database не найден title property",
                "reason": None,
                "template": template,
                "preview": template_result["preview"],
            }

        notion_properties = {}
        included_template_fields = {"Title"}
        _set_property_value(notion_properties, title_property, "title", template["Title"])

        description_property = _find_property_by_alias(
            properties,
            "rich_text",
            ("Description", "Summary", "Details", "Content"),
        )
        category_property = _find_property_by_alias(
            properties,
            "select",
            ("Category", "Type", "Project Type"),
        ) or _find_property_by_alias(
            properties,
            "rich_text",
            ("Category", "Type", "Project Type"),
        )
        technologies_property = _find_property_by_alias(
            properties,
            "multi_select",
            ("Technologies", "Tech Stack", "Stack", "Tools"),
        ) or _find_property_by_alias(
            properties,
            "rich_text",
            ("Technologies", "Tech Stack", "Stack", "Tools"),
        )
        result_url_property = _find_property_by_alias(
            properties,
            "url",
            ("Result URL", "URL", "Link", "Project URL", "Demo URL"),
        )
        status_property = _find_property_by_alias(
            properties,
            "select",
            ("Status", "State"),
        ) or _find_property_by_alias(
            properties,
            "rich_text",
            ("Status", "State"),
        )
        source_property = _find_property_by_alias(
            properties,
            "select",
            ("Source", "Origin"),
        ) or _find_property_by_alias(
            properties,
            "rich_text",
            ("Source", "Origin"),
        )

        if description_property:
            included_template_fields.add("Description")
            _set_property_value(
                notion_properties,
                description_property,
                properties[description_property]["type"],
                template["Description"],
            )
        if category_property:
            included_template_fields.add("Category")
            _set_property_value(
                notion_properties,
                category_property,
                properties[category_property]["type"],
                template["Category"],
            )
        if technologies_property and template["Technologies"]:
            included_template_fields.add("Technologies")
            value = template["Technologies"]
            if properties[technologies_property]["type"] == "rich_text":
                value = ", ".join(value)
            _set_property_value(
                notion_properties,
                technologies_property,
                properties[technologies_property]["type"],
                value,
            )
        if result_url_property and template["Result URL"]:
            included_template_fields.add("Result URL")
            _set_property_value(
                notion_properties,
                result_url_property,
                "url",
                template["Result URL"],
            )
        if status_property:
            included_template_fields.add("Status")
            _set_property_value(
                notion_properties,
                status_property,
                properties[status_property]["type"],
                template["Status"],
            )
        if source_property:
            included_template_fields.add("Source")
            _set_property_value(
                notion_properties,
                source_property,
                properties[source_property]["type"],
                template["Source"],
            )

        page_payload = {
            "parent": {"database_id": database_id},
            "properties": notion_properties,
            "children": _build_page_children(template, included_template_fields),
        }

        page_response = requests.post(
            f"{NOTION_API_BASE}/pages",
            headers=_notion_headers(api_key),
            json=page_payload,
            timeout=15,
        )

        if page_response.status_code not in (200, 201):
            return {
                "ok": False,
                "status": "error",
                "page_id": None,
                "url": None,
                "error": f"Notion page create failed: {page_response.status_code} {page_response.text[:300]}",
                "reason": None,
                "template": template,
                "preview": template_result["preview"],
            }

        page = page_response.json()
        return {
            "ok": True,
            "status": "success",
            "page_id": page.get("id"),
            "url": page.get("url"),
            "error": None,
            "reason": None,
            "database_title": _first_database_title(database),
            "template": template,
            "preview": template_result["preview"],
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "page_id": None,
            "url": None,
            "error": str(exc),
            "reason": None,
            "template": template,
            "preview": template_result["preview"],
        }
