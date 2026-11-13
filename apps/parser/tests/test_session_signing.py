"""Signing-key regressions for both independently runnable parser copies."""
import importlib.util
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import jwt

ROOT = Path(__file__).resolve().parents[3]
PUBLIC_KEYS = (
    "leadhunter-super-secret-production-key-change-me-in-env",
    "change-this-to-a-super-secret-hex-key-in-production",
    "castleweb_secret_key_1234567890",
    "super-secret-castleweb-key-change-in-production",
)


class SigningKeyTests(unittest.TestCase):
    def modules(self):
        for folder in (ROOT / "apps/parser", ROOT / "парсеп/parser"):
            # The legacy local copy is ignored by Git and absent in clean CI checkouts.
            if not (folder / "app/core/security.py").is_file():
                continue
            spec = importlib.util.spec_from_file_location("isolated_security", folder / "app/core/security.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            yield module

    def test_unsafe_config_cannot_issue_or_accept_tokens(self):
        for key in (None, "", "short", *PUBLIC_KEYS):
            with self.subTest(key=key), patch.dict(os.environ):
                os.environ.pop("SECRET_KEY", None)
                if key is not None:
                    os.environ["SECRET_KEY"] = key
                forged = jwt.encode({"sub": "1", "role": "admin"}, key or PUBLIC_KEYS[0], algorithm="HS256")
                for module in self.modules():
                    self.assertIsNone(module.decode_session_token(forged))
                    with self.assertRaises(RuntimeError):
                        module.create_session_token(1, "admin@example.test")

    def test_linux_migration_replaces_unsafe_keys_and_preserves_valid_key(self):
        bash = shutil.which("bash")
        if os.name == "nt":
            bash = r"C:\Program Files\Git\bin\bash.exe"
        if not bash or not Path(bash).is_file():
            self.skipTest("Bash unavailable")
        auto = (ROOT / "scripts/auto-deploy.sh").read_text(encoding="utf-8")
        manual = (ROOT / "scripts/deploy.sh").read_text(encoding="utf-8")
        blocks = (
            auto[auto.index("parser_signing_key=$("):auto.index("webhook_secret=$(")],
            manual[manual.index("    local parser_signing_key"):manual.index('    if [ ! -f "$PARSER_ENV_FILE" ]; then')],
        )
        valid = "isolated-migration-test-key-at-least-32-characters"
        for block in blocks:
            for old_key in (None, "", "short", *PUBLIC_KEYS, valid):
                with self.subTest(key=old_key), tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / "parser.env"
                    path.write_text("UNCHANGED=yes\n" + (f"SECRET_KEY={old_key}\n" if old_key is not None else ""), encoding="utf-8")
                    env = dict(os.environ, PARSER_ENV=path.as_posix(), PARSER_ENV_FILE=path.as_posix())
                    script = "set -e\nfail() { exit 1; }\nlog() { :; }\nlog_warn() { :; }\nmigrate() {\n" + block + "\n}\nmigrate\n"
                    subprocess.run([bash, "-s"], input=script, text=True, env=env, check=True, capture_output=True)
                    lines = path.read_text(encoding="utf-8").splitlines()
                    self.assertIn("UNCHANGED=yes", lines)
                    keys = [line.split("=", 1)[1] for line in lines if line.startswith("SECRET_KEY=")]
                    self.assertEqual(len(keys), 1)
                    if old_key == valid:
                        self.assertEqual(keys[0], valid)
                    else:
                        self.assertRegex(keys[0], r"^[0-9a-f]{64}$")
    def test_valid_config_preserves_sessions_and_rejects_public_keys(self):
        with patch.dict(os.environ, SECRET_KEY="isolated-signing-test-key-at-least-32-characters"):
            for module in self.modules():
                token = module.create_session_token(7, "user@example.test", "paid")
                self.assertEqual(module.decode_session_token(token)["sub"], "7")
                for key in PUBLIC_KEYS:
                    forged = jwt.encode({"sub": "7", "role": "admin"}, key, algorithm="HS256")
                    self.assertIsNone(module.decode_session_token(forged))


if __name__ == "__main__":
    unittest.main()
