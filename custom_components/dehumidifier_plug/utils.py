import re

def slugify(name: str) -> str:
    """Convert a string to a slug-safe format for entity_id construction."""
    return re.sub(r'[^a-z0-9_]', '_', name.lower()).strip('_')