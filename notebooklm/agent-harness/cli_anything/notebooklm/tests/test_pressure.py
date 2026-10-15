from cli_anything.notebooklm.utils.notebooklm_backend import sanitize_error


def test_sanitize_windows_auth_path_with_single_backslashes():
    message = r"Login failed while reading C:\Users\Alice\.notebooklm\storage_state.json"

    sanitized = sanitize_error(message)

    assert "Alice" not in sanitized
    assert "storage_state.json" not in sanitized
    assert "[redacted-auth-path]" in sanitized
