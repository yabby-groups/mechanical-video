"""Project defaults shared by the CLI and the local workbench."""
import os

DEFAULT_VISION_MODEL = 'gpt-6-luna'

def vision_model():
    return os.environ.get('VISION_MODEL', '').strip() or DEFAULT_VISION_MODEL
