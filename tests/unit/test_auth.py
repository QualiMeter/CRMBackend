from app.core.auth import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hash_roundtrip():
    password = "test-password-123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)

def test_jwt_roundtrip():
    token = create_access_token("00000000-0000-0000-0000-000000000001", ["user"])
    payload = decode_access_token(token)
    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["roles"] == ["user"]
