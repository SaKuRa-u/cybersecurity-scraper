import hashlib
import json
from typing import Dict, Any

def compute_content_hash(content: Dict[Any, Any]) -> str:
    """Generate SHA256 hash of content for change detection."""
    content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()
