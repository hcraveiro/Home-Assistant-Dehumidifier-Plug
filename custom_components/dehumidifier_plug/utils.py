import re
import unicodedata

def slugify(value: str) -> str:
    """Simplified slugify function for entity_id creation.

    This function normalizes and converts a string to a lowercase,
    underscore-separated slug suitable for use in entity IDs.
    """
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "_", value)  # Replace spaces and dashes with a single underscore
    return value

