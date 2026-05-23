"""Tests for CSRF token generation and validation in auth/csrf.py."""
import time
from unittest.mock import patch

from app.auth.csrf import is_valid_token, new_csrf_token, verify_csrf


def test_fresh_token_is_valid():
    token = new_csrf_token()
    assert is_valid_token(token) is True


def test_manipulated_token_is_invalid():
    token = new_csrf_token()
    # Flip a character in the middle of the token
    mid = len(token) // 2
    tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1:]
    assert is_valid_token(tampered) is False


def test_expired_token_is_invalid():
    token = new_csrf_token()
    # Advance time past the 1-hour TTL
    future = time.time() + 3601
    with patch("time.time", return_value=future):
        assert is_valid_token(token) is False


def test_empty_token_is_invalid():
    assert is_valid_token("") is False


def test_verify_csrf_matching_tokens():
    token = new_csrf_token()
    assert verify_csrf(token, token) is True


def test_verify_csrf_different_nonces():
    token_a = new_csrf_token()
    token_b = new_csrf_token()
    assert verify_csrf(token_a, token_b) is False


def test_verify_csrf_empty_form_token():
    token = new_csrf_token()
    assert verify_csrf("", token) is False


def test_verify_csrf_empty_cookie_token():
    token = new_csrf_token()
    assert verify_csrf(token, "") is False


def test_verify_csrf_invalid_form_token():
    token = new_csrf_token()
    assert verify_csrf("not-a-valid-token", token) is False
