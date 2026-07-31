"""Admin panel + import API tests (v2 §4/§5): RBAC, trust tiers, review flow."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.exercises.models import ExerciseTemplate
from apps.users.models import User

from .models import AdminUser, APIKey, ImportLog


@pytest.fixture
def level(db):
    return Level.objects.create(code="A1", name="Breakthrough", order=1)


def make_admin(role, email):
    admin = AdminUser(email=email, role=role)
    admin.set_password("panelpass123")
    admin.save()
    return admin


def login(client, email):
    resp = client.post(
        reverse("v1:adminpanel:admin-login"),
        {"email": email, "password": "panelpass123"},
        format="json",
    )
    assert resp.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")
    return resp.data


@pytest.fixture
def super_client(db):
    make_admin(AdminUser.Role.SUPER, "super@panel.test")
    c = APIClient()
    login(c, "super@panel.test")
    return c


@pytest.fixture
def content_client(db):
    make_admin(AdminUser.Role.CONTENT, "content@panel.test")
    c = APIClient()
    login(c, "content@panel.test")
    return c


@pytest.fixture
def support_client(db):
    make_admin(AdminUser.Role.SUPPORT, "support@panel.test")
    c = APIClient()
    login(c, "support@panel.test")
    return c


# --------------------------------------------------------------------------- #
# RBAC (§4.2) — enforced in the backend, not just hidden UI
# --------------------------------------------------------------------------- #
def test_login_bad_password_rejected(db):
    make_admin(AdminUser.Role.SUPER, "s@panel.test")
    resp = APIClient().post(
        reverse("v1:adminpanel:admin-login"),
        {"email": "s@panel.test", "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401


def test_end_user_jwt_cannot_access_admin_api(db):
    user = User.objects.create_user(email="u@test.com", password="pass12345")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(reverse("v1:adminpanel:admin-stats")).status_code == 403


def test_content_admin_cannot_touch_users(content_client):
    assert content_client.get(
        reverse("v1:adminpanel:admin-users")
    ).status_code == 403
    assert content_client.post(
        reverse("v1:adminpanel:admin-premium-activate"), {}, format="json"
    ).status_code == 403


def test_support_admin_cannot_touch_content(support_client):
    assert support_client.get(
        reverse("v1:adminpanel:admin-content-tree")
    ).status_code == 403
    assert support_client.get(
        reverse("v1:adminpanel:admin-review-articles")
    ).status_code == 403


def test_only_super_manages_admins_and_keys(content_client, support_client):
    for client in (content_client, support_client):
        assert client.get(
            reverse("v1:adminpanel:admin-admins")
        ).status_code == 403
        assert client.get(
            reverse("v1:adminpanel:admin-api-keys")
        ).status_code == 403


def test_manual_premium_activation(support_client, db):
    user = User.objects.create_user(email="pay@test.com", password="pass12345")
    resp = support_client.post(
        reverse("v1:adminpanel:admin-premium-activate"),
        {"email": "pay@test.com", "plan_type": "monthly", "duration_days": 30},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["user"]["premium_active"] is True
    from apps.billing.models import PremiumGrant

    grant = PremiumGrant.objects.get(user=user)
    assert grant.source == PremiumGrant.Source.MANUAL_ADMIN


# --------------------------------------------------------------------------- #
# Content Import API (§5.1) — trust tiers + logging + review queue
# --------------------------------------------------------------------------- #
def _seed_templates():
    for code in ("multiple_choice", "true_false"):
        ExerciseTemplate.objects.get_or_create(code=code, defaults={"name": code})


def _lesson_payload(**overrides):
    payload = {
        "level": "A1",
        "unit": {"title": "Imported Unit", "order": 1},
        "lesson": {"title": "Imported Lesson", "order": 1},
        "components": [
            {"type": "text", "order": 1, "content": "# Hello"},
            {"type": "exercise", "order": 2, "exercises": [
                {"template": "multiple_choice",
                 "content": {"question": "?", "options": ["a", "b"],
                             "correct_index": 0}},
            ]},
        ],
    }
    payload.update(overrides)
    return payload


def make_key(trust):
    raw, prefix, key_hash = APIKey.generate()
    APIKey.objects.create(
        name=f"key-{trust}", prefix=prefix, key_hash=key_hash, trust_level=trust
    )
    return raw


def test_import_requires_api_key(level):
    resp = APIClient().post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    )
    assert resp.status_code in (401, 403)


def test_import_defaults_to_draft_and_hides_from_students(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"
    lesson = Lesson.objects.get(id=resp.data["lesson_id"])
    assert lesson.status == Lesson.Status.DRAFT

    # Draft is invisible to the student API until approved.
    student = User.objects.create_user(email="s2@test.com", password="pass12345")
    sc = APIClient()
    sc.force_authenticate(student)
    assert sc.get(
        reverse("v1:lesson-detail", args=[lesson.id])
    ).status_code == 404


def test_low_trust_key_cannot_publish_direct(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        _lesson_payload(publish_mode="direct"),
        format="json",
    )
    assert resp.status_code == 403


def test_high_trust_key_publishes_direct_and_is_logged(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DIRECT_PUBLISH)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        _lesson_payload(publish_mode="direct"),
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "published"
    log = ImportLog.objects.get()
    assert log.publish_mode == "direct"
    assert log.content_id == resp.data["lesson_id"]  # traceability (§5.1)


def test_import_validates_schema(level, db):
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        {"level": "Z9", "components": [{"type": "hologram"}]},
        format="json",
    )
    assert resp.status_code == 400
    assert any("Z9" in e for e in resp.data["errors"])
    assert any("hologram" in e for e in resp.data["errors"])


def test_review_queue_approve_flow(content_client, level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    ic = APIClient()
    ic.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    lesson_id = ic.post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    ).data["lesson_id"]

    queue = content_client.get(reverse("v1:adminpanel:admin-review-lessons"))
    assert any(row["id"] == lesson_id for row in queue.data)

    resp = content_client.post(
        reverse("v1:adminpanel:admin-review-lesson-act",
                args=[lesson_id, "approve"])
    )
    assert resp.status_code == 200
    assert Lesson.objects.get(id=lesson_id).status == Lesson.Status.PUBLISHED


# --------------------------------------------------------------------------- #
# Idempotent import — retry-safe batch pipelines
# --------------------------------------------------------------------------- #
def _import_client(trust=APIKey.Trust.DRAFT_ONLY):
    raw = make_key(trust)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


def _post(client, payload):
    return client.post(
        reverse("v1:content-lessons-import"), payload, format="json"
    )


def test_import_without_key_still_creates_every_time(level, db):
    """Unchanged default behaviour: no idempotency_key -> always 201/create."""
    _seed_templates()
    client = _import_client()

    first = _post(client, _lesson_payload())
    second = _post(client, _lesson_payload())

    assert first.status_code == 201 and second.status_code == 201
    assert first.data["action"] == "created"
    assert first.data["duplicate"] is False
    assert first.data["lesson_id"] != second.data["lesson_id"]
    assert Lesson.objects.count() == 2


def test_idempotency_key_skips_duplicate(level, db):
    _seed_templates()
    client = _import_client()
    payload = _lesson_payload(idempotency_key="batch-001")

    first = _post(client, payload)
    second = _post(client, payload)

    assert first.status_code == 201 and first.data["action"] == "created"
    assert second.status_code == 200
    assert second.data["action"] == "skipped"
    assert second.data["duplicate"] is True
    assert second.data["lesson_id"] == first.data["lesson_id"]
    assert Lesson.objects.count() == 1
    # Skip must not touch the stored components.
    assert Lesson.objects.get().components.count() == 2


def test_on_duplicate_replace_rebuilds_in_place(level, db):
    _seed_templates()
    client = _import_client()
    first = _post(client, _lesson_payload(idempotency_key="batch-002"))

    replacement = _lesson_payload(
        idempotency_key="batch-002",
        on_duplicate="replace",
        lesson={"title": "Rewritten lesson", "order": 7},
        components=[{"type": "text", "order": 1, "content": "# Replaced"}],
    )
    second = _post(client, replacement)

    assert second.status_code == 200
    assert second.data["action"] == "replaced"
    assert second.data["duplicate"] is True
    # Same row, rebuilt contents.
    assert second.data["lesson_id"] == first.data["lesson_id"]
    assert Lesson.objects.count() == 1
    lesson = Lesson.objects.get()
    assert lesson.title == "Rewritten lesson"
    assert lesson.components.count() == 1
    block = lesson.components.get().text_block
    assert block.content == "# Replaced"
    # The old exercise component is gone, not orphaned.
    from apps.exercises.models import Exercise

    assert Exercise.objects.count() == 0


def test_invalid_on_duplicate_rejected(level, db):
    _seed_templates()
    client = _import_client()
    resp = _post(
        client,
        _lesson_payload(idempotency_key="batch-003", on_duplicate="explode"),
    )
    assert resp.status_code == 400
    assert any("on_duplicate" in e for e in resp.data["errors"])


def test_blank_idempotency_key_rejected(level, db):
    _seed_templates()
    resp = _post(_import_client(), _lesson_payload(idempotency_key="   "))
    assert resp.status_code == 400


def test_distinct_keys_create_distinct_lessons(level, db):
    _seed_templates()
    client = _import_client()
    a = _post(client, _lesson_payload(idempotency_key="a"))
    b = _post(client, _lesson_payload(idempotency_key="b"))
    assert a.data["lesson_id"] != b.data["lesson_id"]
    assert Lesson.objects.count() == 2


def test_concurrent_post_race_resolves_instead_of_500(level, db, monkeypatch):
    """Two simultaneous POSTs with the same key: the loser's INSERT hits the
    unique constraint, and must resolve to the winner's row rather than 500."""
    from django.db import IntegrityError

    from apps.content import importer

    _seed_templates()
    client = _import_client()
    payload = _lesson_payload(idempotency_key="race-1")
    first = _post(client, payload)
    assert first.status_code == 201

    real_find = importer._find_existing
    state = {"precheck_done": False, "creates": 0}

    def blind_first_lookup(key):
        # Simulate the racing window: this request's pre-check runs before the
        # other transaction commits, so it sees nothing. The post-INSERT
        # lookup in the except branch then finds the winner.
        if not state["precheck_done"]:
            state["precheck_done"] = True
            return None
        return real_find(key)

    def racing_create(*args, **kwargs):
        state["creates"] += 1
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(importer, "_find_existing", blind_first_lookup)
    monkeypatch.setattr(importer.Lesson.objects, "create", racing_create)

    second = _post(client, payload)

    assert state["creates"] == 1, "the INSERT must actually have been attempted"
    assert second.status_code == 200
    assert second.data["action"] == "skipped"
    assert second.data["lesson_id"] == first.data["lesson_id"]
    assert Lesson.objects.count() == 1


def test_import_log_records_action_for_every_branch(level, db):
    _seed_templates()
    client = _import_client()
    payload = _lesson_payload(idempotency_key="logged-1")
    _post(client, payload)
    _post(client, payload)
    _post(client, _lesson_payload(
        idempotency_key="logged-1", on_duplicate="replace"
    ))

    actions = list(ImportLog.objects.order_by("created_at")
                   .values_list("action", flat=True))
    assert actions == ["created", "skipped", "replaced"]
    # Skips are logged too, so a retry storm is visible.
    assert ImportLog.objects.filter(success=True).count() == 3


# --------------------------------------------------------------------------- #
# Media upload
# --------------------------------------------------------------------------- #
def _upload(client, *, content=b"binary-bytes", kind="image",
            filename="pic.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return client.post(
        reverse("v1:content-media-upload"),
        {
            "file": SimpleUploadedFile(filename, content),
            "kind": kind,
            "filename": filename,
        },
        format="multipart",
    )


def test_media_upload_requires_api_key(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    assert _upload(APIClient()).status_code in (401, 403)


def test_media_upload_stores_file_and_returns_both_forms(db, tmp_path,
                                                         settings):
    settings.MEDIA_ROOT = tmp_path
    settings.VIDEO_PLAYBACK_BASE_URL = "http://testserver/media/"
    resp = _upload(_import_client(), content=b"png-data", kind="image")

    assert resp.status_code == 201
    assert resp.data["kind"] == "image"
    assert resp.data["size"] == len(b"png-data")
    assert resp.data["deduplicated"] is False
    # Relative key for Video.storage_key…
    key = resp.data["storage_key"]
    assert key.startswith("images/") and key.endswith(".png")
    # …absolute URL for the vocabulary URLFields.
    assert resp.data["url"] == f"http://testserver/media/{key}"
    assert (tmp_path / key).exists()
    assert (tmp_path / key).read_bytes() == b"png-data"


def test_media_upload_deduplicates_identical_bytes(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    client = _import_client()
    first = _upload(client, content=b"same-bytes", kind="audio",
                    filename="a.mp3")
    path = tmp_path / first.data["storage_key"]
    mtime = path.stat().st_mtime_ns

    # Different source filename, identical content.
    second = _upload(client, content=b"same-bytes", kind="audio",
                     filename="totally-different.mp3")

    assert second.status_code == 201
    assert second.data["deduplicated"] is True
    assert second.data["storage_key"] == first.data["storage_key"]
    assert second.data["sha256"] == first.data["sha256"]
    # The original file was not rewritten.
    assert path.stat().st_mtime_ns == mtime
    assert len(list((tmp_path / "audio").iterdir())) == 1


def test_media_upload_rejects_bad_kind_and_extension(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    client = _import_client()

    assert _upload(client, kind="hologram").status_code == 400
    # .exe is on no allowlist
    bad = _upload(client, kind="image", filename="payload.exe")
    assert bad.status_code == 400
    assert "not allowed" in bad.data["detail"]
    # right extension, wrong kind
    assert _upload(client, kind="audio", filename="pic.png").status_code == 400


def test_media_upload_rejects_oversized_file(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_MAX_IMAGE_MB = 1
    resp = _upload(
        _import_client(), content=b"x" * (1024 * 1024 + 10), kind="image"
    )
    assert resp.status_code == 400
    assert "limit" in resp.data["detail"]
    # Nothing partial left behind.
    assert not any((tmp_path / "images").glob("*")) if (
        tmp_path / "images").exists() else True


def test_media_upload_rejects_missing_file(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    resp = _import_client().post(
        reverse("v1:content-media-upload"), {"kind": "image"},
        format="multipart",
    )
    assert resp.status_code == 400


def test_media_upload_blocks_path_traversal(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    resp = _upload(
        _import_client(), kind="image", filename="../../../etc/passwd.png"
    )
    assert resp.status_code == 201
    key = resp.data["storage_key"]
    # Everything stays inside MEDIA_ROOT/images/ and the hostile name is gone.
    assert key.startswith("images/")
    assert ".." not in key and "etc" not in key
    resolved = (tmp_path / key).resolve()
    assert str(resolved).startswith(str(tmp_path.resolve()))


def test_media_upload_rejects_empty_file(db, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    resp = _upload(_import_client(), content=b"", kind="image")
    assert resp.status_code == 400
