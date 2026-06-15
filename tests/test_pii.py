from app.pii import scrub_text, scrub_data


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_phone_vn() -> None:
    out = scrub_text("Sđt của tôi là 0987654321")
    assert "0987654321" not in out
    assert "REDACTED_PHONE_VN" in out


def test_scrub_credit_card() -> None:
    out = scrub_text("My card is 4111 1111 1111 1111.")
    assert "4111" not in out
    assert "REDACTED_CREDIT_CARD" in out


def test_scrub_cccd() -> None:
    out = scrub_text("Số CCCD: 038202001234")
    assert "038202001234" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_passport() -> None:
    out = scrub_text("Passport number is B1234567")
    assert "B1234567" not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_address_cases() -> None:
    # 1. Valid address (should be redacted)
    addr = "Địa chỉ: số 12 ngõ 5 đường Nguyễn Trãi, quận Thanh Xuân"
    out = scrub_text(addr)
    assert "Nguyễn Trãi" not in out
    assert "REDACTED_ADDRESS" in out

    # 2. General context phrase with keyword 'đường' (should NOT be redacted)
    phrase = "đường đi của request trong middleware"
    out_phrase = scrub_text(phrase)
    assert out_phrase == phrase
    assert "REDACTED" not in out_phrase


def test_scrub_recursive_data() -> None:
    data = {
        "user_email": "test@domain.com",
        "nested": {
            "card": "4111-1111-1111-1111",
            "info": ["Phone: 0987654321", "Normal text here"]
        }
    }
    cleaned = scrub_data(data)
    assert cleaned["user_email"] == "[REDACTED_EMAIL]"
    assert cleaned["nested"]["card"] == "[REDACTED_CREDIT_CARD]"
    assert cleaned["nested"]["info"][0] == "Phone: [REDACTED_PHONE_VN]"
    assert cleaned["nested"]["info"][1] == "Normal text here"
