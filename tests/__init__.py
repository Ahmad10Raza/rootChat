# Package initialization
import os
import tempfile

if "ROOTCHAT_CONFIG_FILE" not in os.environ:
    _test_tmp = tempfile.mkdtemp(prefix="rootchat_test_cfg_")
    os.environ["ROOTCHAT_CONFIG_FILE"] = os.path.join(_test_tmp, "config.json")
