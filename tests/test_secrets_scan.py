from pathlib import Path

from repo_health.secrets_scan import scan_path


def test_clean_repo_has_no_findings(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello world')\n")
    (tmp_path / "README.md").write_text("# Hello\n\nA normal readme.\n")

    result = scan_path(tmp_path)

    assert result.clean
    assert result.files_scanned == 2


def test_detects_dotenv_filename(tmp_path: Path):
    (tmp_path / ".env").write_text("DB_PASSWORD=hunter2\n")

    result = scan_path(tmp_path)

    assert not result.clean
    assert any("suspicious filename" in f.reason for f in result.findings)


def test_detects_mongodb_connection_string_with_credentials(tmp_path: Path):
    (tmp_path / "config.py").write_text(
        "MONGO_URI = 'mongodb+srv://admin:S3cretPass@cluster0.mongodb.net/prod'\n"
    )

    result = scan_path(tmp_path)

    assert not result.clean
    assert any("connection string" in f.reason.lower() for f in result.findings)


def test_detects_aws_access_key(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("key: AKIAABCDEFGHIJKLMNOP\n")

    result = scan_path(tmp_path)

    assert any("AWS Access Key" in f.reason for f in result.findings)


def test_detects_private_key_block(tmp_path: Path):
    (tmp_path / "id_rsa_backup.txt").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK...\n-----END RSA PRIVATE KEY-----\n"
    )

    result = scan_path(tmp_path)

    assert any("private key" in f.reason.lower() for f in result.findings)


def test_ignores_node_modules_by_default(tmp_path: Path):
    nested = tmp_path / "node_modules" / "some-lib"
    nested.mkdir(parents=True)
    (nested / "index.js").write_text("const token = 'AKIAABCDEFGHIJKLMNOP';\n")

    result = scan_path(tmp_path)

    assert result.clean


def test_env_example_with_placeholder_is_not_flagged_for_content(tmp_path: Path):
    (tmp_path / ".env.example").write_text("DB_PASSWORD=your-password-here\nAPI_KEY=changeme\n")

    result = scan_path(tmp_path)

    assert result.clean
