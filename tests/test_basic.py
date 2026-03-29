import pytest
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import autowrite.handwriting_synthesis.config as config
from autowrite.handwriting_synthesis import Hand

def test_config_paths():
    assert os.path.exists(config.BASE_PATH)
    assert os.path.basename(config.BASE_PATH) == "model"

def test_hand_init():
    # Test if the model checkpoint path is found without fully running inference
    assert os.path.exists(config.checkpoint_path)
