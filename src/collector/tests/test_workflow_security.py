import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_r2_credentials_are_only_in_storage_step_environments():
    workflow = (ROOT / ".github/workflows/refresh.yml").read_text()
    assert "R2_SECRET_ACCESS_KEY" not in workflow.split("    steps:")[0]
    allowed = {"Restore previous state from R2", "Upload flat data files, then manifest"}
    for block in workflow.split("      - name: ")[1:]:
        if "R2_SECRET_ACCESS_KEY" in block:
            assert block.splitlines()[0] in allowed
            assert "uv run --no-sync python storage.py" in block
    assert "R2_PRIVATE_BUCKET" not in workflow
    assert "awscli.zip" not in workflow
    assert "sudo" not in workflow


def test_wrangler_is_locked_and_installed_before_token_is_exposed():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
    deploy = workflow.split("  deploy:", 1)[1]
    install, execution = deploy.split("      - run: src/web/node_modules/.bin/wrangler", 1)
    assert "CLOUDFLARE_API_TOKEN" not in install
    assert "npm ci --ignore-scripts" in install
    assert "CLOUDFLARE_API_TOKEN" in execution
    assert "npx" not in deploy
    lock = json.loads((ROOT / "src/web/package-lock.json").read_text())
    assert lock["packages"]["node_modules/wrangler"]["version"] == "4.54.0"
