"""Build the rules vector index."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xwing_agent.config import get_settings
from xwing_agent.tools.rules import build_rules_index

settings = get_settings()

if __name__ == "__main__":
    rules_dir = Path(__file__).parent.parent / "src" / "xwing_agent" / "rules" / "documents"

    if not rules_dir.exists():
        print(f"Rules directory not found: {rules_dir}")
        print("Create markdown files with X-Wing rules in that directory first.")
        sys.exit(1)

    build_rules_index(rules_dir, settings.rules_index_path)
    print(f"Index built at {settings.rules_index_path}")
