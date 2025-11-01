#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # Respect App Runner or Docker environment variable first
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.production")
    )

    print(f"Using settings module: {os.environ['DJANGO_SETTINGS_MODULE']}")

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django  # noqa
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise

    #  Ensure apps inside `ami/` are on sys.path
    current_path = Path(__file__).parent.resolve()
    sys.path.append(str(current_path / "ami"))

    execute_from_command_line(sys.argv)
