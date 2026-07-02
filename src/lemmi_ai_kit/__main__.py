"""Allow running as `python -m lemmi_ai_kit`."""

import sys

from lemmi_ai_kit.cli import main

if __name__ == "__main__":
    sys.exit(main())
