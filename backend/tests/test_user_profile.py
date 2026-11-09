P = "/api/v1"


def test_user_can_update_own_profile_contacts(clients):
    response = clients["no_grant"].put(
        P + "/me/profile",
        json={
            "display_name": "Pessoa Interna",
            "contact_email": "Pessoa@exemplo.com",
            "contact_phone": "+55 (85) 99999-1234",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "username": "no_grant",
        "display_name": "Pessoa Interna",
        "contact_email": "pessoa@exemplo.com",
        "contact_phone": "+55 (85) 99999-1234",
        "photo_url": None,
    }


def test_supplier_can_manage_only_its_own_profile(clients):
    response = clients["supplier"].put(
        P + "/me/profile",
        json={"display_name": "Contato fornecedor", "contact_email": "dev@example.com", "contact_phone": "85999990000"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["username"] == "supplier"
    assert clients["other"].get(P + "/me/profile").json()["contact_email"] == ""


def test_user_can_upload_and_remove_profile_photo(clients):
    # The route validates the PNG signature and stores only bytes under 2 MiB.
    png = b"\x89PNG\r\n\x1a\n" + b"profile-image-test"
    uploaded = clients["manager"].put(
        P + "/me/profile/photo",
        content=png,
        headers={"Content-Type": "image/png"},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["photo_url"].startswith(P + "/me/profile/photo?v=")

    photo = clients["manager"].get(P + "/me/profile/photo")
    assert photo.status_code == 200
    assert photo.content == png
    assert photo.headers["content-type"] == "image/png"
    assert photo.headers["cache-control"] == "private, no-store"

    removed = clients["manager"].delete(P + "/me/profile/photo")
    assert removed.status_code == 200, removed.text
    assert removed.json()["photo_url"] is None
    assert clients["manager"].get(P + "/me/profile/photo").status_code == 404


def test_profile_photo_rejects_wrong_signature_and_oversized_upload(clients):
    invalid = clients["admin"].put(
        P + "/me/profile/photo",
        content=b"not-an-image",
        headers={"Content-Type": "image/png"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["message"] == "Envie uma imagem JPG, PNG ou WebP válida."

    oversized = clients["admin"].put(
        P + "/me/profile/photo",
        content=b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024),
        headers={"Content-Type": "image/png"},
    )
    assert oversized.status_code == 413
