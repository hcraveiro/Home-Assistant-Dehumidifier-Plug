import re
import unicodedata

def slugify(value: str) -> str:
    """Simplified slugify function for entity_id creation."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "_", value)  # Substitui espaços e traços por underscore único
    return value