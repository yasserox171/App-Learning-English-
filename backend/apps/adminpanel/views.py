"""Admin panel API (v2 §4) + Content Import API (v2 §5).

All /admin-api/ endpoints authenticate with the dedicated AdminUser JWT and
enforce roles server-side:
  Super   → everything, incl. admin accounts + API keys
  Content → lessons / articles / question bank only
  Support → users + manual subscription activation only
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services as billing_services
from apps.billing.models import PremiumGrant
from apps.content.importer import ImportValidationError, import_lesson
from apps.content.models import Lesson, Level, Unit
from apps.content.serializers import LessonDetailSerializer
from apps.news.models import NewsArticle
from apps.news.serializers import NewsArticleSerializer
from apps.progress.models import PlacementQuestion
from apps.tutor.models import AITutorSession
from apps.users.models import User

from .auth import (
    AdminJWTAuthentication,
    APIKeyAuthentication,
    HasValidAPIKey,
    IsAnyAdmin,
    IsContentAdmin,
    IsSuperAdmin,
    IsSupportAdmin,
    issue_admin_token,
)
from .models import AdminActionLog, AdminUser, APIKey, ImportLog


class AdminAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]


def _admin_payload(admin: AdminUser) -> dict:
    return {
        "id": str(admin.id),
        "email": admin.email,
        "full_name": admin.full_name,
        "role": admin.role,
        "is_active": admin.is_active,
        "last_login": admin.last_login,
    }


def _log(admin, action, target="", **detail):
    AdminActionLog.objects.create(
        admin=admin, action=action, target=str(target), detail=detail
    )


# =========================================================================== #
# Auth
# =========================================================================== #
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))
        admin = AdminUser.objects.filter(
            email__iexact=email, is_active=True
        ).first()
        if admin is None or not admin.check_password(password):
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        admin.last_login = timezone.now()
        admin.save(update_fields=["last_login"])
        return Response(
            {"token": issue_admin_token(admin), "admin": _admin_payload(admin)}
        )


class MeView(AdminAPIView):
    permission_classes = [IsAnyAdmin]

    def get(self, request):
        return Response(_admin_payload(request.user))


# =========================================================================== #
# Stats dashboard (§4.1.6)
# =========================================================================== #
class StatsView(AdminAPIView):
    permission_classes = [IsAnyAdmin]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        users = User.objects.all()
        active_grants = PremiumGrant.objects.filter(
            start_date__lte=now, end_date__gt=now
        )
        subs_by_source = {
            row["source"]: row["n"]
            for row in active_grants.values("source").annotate(n=Count("id"))
        }

        tutor_week = AITutorSession.objects.filter(
            created_at__gte=week_ago
        ).count()
        # Rough cost estimate per session: STT + LLM + TTS (config override).
        est_cost_per_session = 0.05
        signups = (
            users.filter(created_at__gte=month_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return Response({
            "users": {
                "total": users.count(),
                "new_this_week": users.filter(created_at__gte=week_ago).count(),
                "active_this_week": users.filter(
                    last_login__gte=week_ago
                ).count(),
                "guests": users.filter(is_guest=True).count(),
            },
            "subscriptions": {
                "active_total": active_grants.count(),
                "by_source": subs_by_source,
            },
            "ai_tutor": {
                "sessions_this_week": tutor_week,
                "estimated_weekly_cost_usd": round(
                    tutor_week * est_cost_per_session, 2
                ),
            },
            "content": {
                "lessons_published": Lesson.objects.filter(
                    status=Lesson.Status.PUBLISHED
                ).count(),
                "lessons_pending_review": Lesson.objects.filter(
                    status=Lesson.Status.DRAFT
                ).count(),
                "articles_pending_review": NewsArticle.objects.filter(
                    status=NewsArticle.Status.DRAFT
                ).count(),
            },
            "daily_signups": [
                {"day": row["day"], "count": row["count"]} for row in signups
            ],
        })


# =========================================================================== #
# Users & subscriptions (§4.1.5) — Support/Super
# =========================================================================== #
def _user_payload(user: User, *, detailed=False) -> dict:
    data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_guest": user.is_guest,
        "country": user.country,
        "created_at": user.created_at,
        "premium_active": billing_services.has_active_premium(user),
    }
    if detailed:
        until = billing_services.premium_until(user)
        data.update({
            "premium_until": until,
            "coin_balance": billing_services.balance(user),
            "grants": [
                {
                    "id": str(g.id),
                    "source": g.source,
                    "start_date": g.start_date,
                    "end_date": g.end_date,
                    "is_active": g.is_active,
                }
                for g in user.premium_grants.all()[:20]
            ],
        })
    return data


class UserSearchView(AdminAPIView):
    permission_classes = [IsSupportAdmin]

    def get(self, request):
        qs = User.objects.all().prefetch_related("premium_grants")
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search) | Q(full_name__icontains=search)
            )
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
        except ValueError:
            page = 1
        size = 25
        total = qs.count()
        rows = qs[(page - 1) * size : page * size]
        return Response({
            "total": total,
            "page": page,
            "results": [_user_payload(u) for u in rows],
        })


class UserDetailView(AdminAPIView):
    permission_classes = [IsSupportAdmin]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response(_user_payload(user, detailed=True))


class ManualActivationView(AdminAPIView):
    """§4.1.5: WhatsApp/bank-transfer payments — admin enters user email +
    plan + duration; grant lands with source='manual_admin'."""

    permission_classes = [IsSupportAdmin]

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        try:
            days = int(request.data.get("duration_days", 0))
        except (TypeError, ValueError):
            days = 0
        plan_type = str(request.data.get("plan_type", "manual"))
        if not email or days <= 0:
            return Response(
                {"detail": "email and a positive duration_days are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {"detail": f"No user with email {email}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        grant = billing_services.grant_premium(
            user, days, PremiumGrant.Source.MANUAL_ADMIN
        )
        _log(request.user, "manual_premium_activation", user.email,
             plan_type=plan_type, days=days, grant_id=str(grant.id))
        return Response(
            {
                "granted_until": grant.end_date,
                "user": _user_payload(user, detailed=True),
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================================================== #
# Content tree (§4.1.1) — Content/Super
# =========================================================================== #
class ContentTreeView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def get(self, request):
        levels = Level.objects.prefetch_related("units__lessons").order_by("order")
        return Response([
            {
                "id": str(level.id),
                "code": level.code,
                "name": level.name,
                "units": [
                    {
                        "id": str(unit.id),
                        "title": unit.title,
                        "order": unit.order,
                        "lessons": [
                            {
                                "id": str(lesson.id),
                                "title": lesson.title,
                                "order": lesson.order,
                                "status": lesson.status,
                            }
                            for lesson in unit.lessons.all()
                        ],
                    }
                    for unit in level.units.all()
                ],
            }
            for level in levels
        ])


class AdminLessonDetailView(AdminAPIView):
    """Full lesson JSON (same shape the app renders → live preview pane)."""

    permission_classes = [IsContentAdmin]

    def get(self, request, pk):
        lesson = get_object_or_404(
            Lesson.objects.prefetch_related(
                "components__vocabulary_items",
                "components__exercises__template",
                "components__video",
                "components__text_block",
            ),
            pk=pk,
        )
        data = LessonDetailSerializer(lesson).data
        data["status"] = lesson.status
        return Response(data)

    def patch(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        for field in ("title", "description", "order"):
            if field in request.data:
                setattr(lesson, field, request.data[field])
        if "status" in request.data and request.data["status"] in (
            Lesson.Status.DRAFT, Lesson.Status.PUBLISHED, Lesson.Status.REJECTED
        ):
            lesson.status = request.data["status"]
        lesson.save()
        _log(request.user, "lesson_updated", lesson.id)
        return Response({"ok": True, "status": lesson.status})


# =========================================================================== #
# Review queues (§4.1.3 lessons, §4.1.4 articles) — Content/Super
# =========================================================================== #
class LessonReviewQueueView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def get(self, request):
        drafts = Lesson.objects.filter(
            status=Lesson.Status.DRAFT
        ).select_related("unit__level")
        return Response([
            {
                "id": str(lesson.id),
                "title": lesson.title,
                "level": lesson.unit.level.code,
                "unit": lesson.unit.title,
                "created_at": lesson.created_at,
            }
            for lesson in drafts
        ])


class LessonReviewActionView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def post(self, request, pk, action):
        lesson = get_object_or_404(Lesson, pk=pk, status=Lesson.Status.DRAFT)
        if action == "approve":
            lesson.status = Lesson.Status.PUBLISHED
        elif action == "reject":
            lesson.status = Lesson.Status.REJECTED
        else:
            return Response(
                {"detail": "action must be approve|reject"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lesson.save(update_fields=["status", "updated_at"])
        _log(request.user, f"lesson_{action}", lesson.id, title=lesson.title)
        return Response({"ok": True, "status": lesson.status})


class ArticleReviewQueueView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def get(self, request):
        qs = NewsArticle.objects.filter(
            status=NewsArticle.Status.DRAFT
        ).select_related("category")
        for param, field in (
            ("category", "category__code"),
            ("country", "country"),
            ("level", "difficulty"),
        ):
            value = request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return Response(NewsArticleSerializer(qs, many=True).data)


class ArticleReviewActionView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def post(self, request, pk, action):
        article = get_object_or_404(NewsArticle, pk=pk)
        if action == "approve":
            article.status = NewsArticle.Status.PUBLISHED
            article.published_date = timezone.now()
            article.expiry_date = None  # recomputed on save from publish date
        elif action == "reject":
            article.status = NewsArticle.Status.REJECTED
        else:
            return Response(
                {"detail": "action must be approve|reject"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        article.save()
        _log(request.user, f"article_{action}", article.id,
             title=article.title_en)
        return Response({"ok": True, "status": article.status})


class ArticleEditView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def patch(self, request, pk):
        article = get_object_or_404(NewsArticle, pk=pk)
        editable = ("title_en", "title_ar", "content_short", "body",
                    "difficulty", "country", "is_global")
        for field in editable:
            if field in request.data:
                setattr(article, field, request.data[field])
        article.save()
        return Response(NewsArticleSerializer(article).data)


# =========================================================================== #
# Placement question bank CRUD (§4.1.2) — Content/Super
# =========================================================================== #
def _question_payload(q: PlacementQuestion) -> dict:
    return {
        "id": str(q.id),
        "level": q.level,
        "qtype": q.qtype,
        "passage": q.passage,
        "question": q.question,
        "options": q.options,
        "correct_index": q.correct_index,
        "is_active": q.is_active,
    }


class PlacementQuestionListView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def get(self, request):
        qs = PlacementQuestion.objects.all()
        level = request.query_params.get("level")
        if level:
            qs = qs.filter(level=level.upper())
        return Response([_question_payload(q) for q in qs])

    def post(self, request):
        data = request.data
        try:
            question = PlacementQuestion.objects.create(
                level=str(data["level"]).upper(),
                qtype=data["qtype"],
                passage=data.get("passage", ""),
                question=data["question"],
                options=list(data["options"]),
                correct_index=int(data["correct_index"]),
                is_active=bool(data.get("is_active", True)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return Response(
                {"detail": f"Invalid question payload: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(_question_payload(question),
                        status=status.HTTP_201_CREATED)


class PlacementQuestionDetailView(AdminAPIView):
    permission_classes = [IsContentAdmin]

    def patch(self, request, pk):
        question = get_object_or_404(PlacementQuestion, pk=pk)
        for field in ("level", "qtype", "passage", "question", "options",
                      "correct_index", "is_active"):
            if field in request.data:
                setattr(question, field, request.data[field])
        question.save()
        return Response(_question_payload(question))

    def delete(self, request, pk):
        get_object_or_404(PlacementQuestion, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================================================================== #
# Admin accounts + API keys (Super only)
# =========================================================================== #
class AdminUserListView(AdminAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(
            [_admin_payload(a) for a in AdminUser.objects.all()]
        )

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = str(request.data.get("password", ""))
        role = request.data.get("role")
        if not email or len(password) < 8 or role not in AdminUser.Role.values:
            return Response(
                {"detail": "email, password (>=8 chars) and a valid role "
                           "are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if AdminUser.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "An admin with this email already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        admin = AdminUser(
            email=email,
            full_name=request.data.get("full_name", ""),
            role=role,
            created_by=request.user,
        )
        admin.set_password(password)
        admin.save()
        _log(request.user, "admin_created", email, role=role)
        return Response(_admin_payload(admin), status=status.HTTP_201_CREATED)


class AdminUserDetailView(AdminAPIView):
    permission_classes = [IsSuperAdmin]

    def patch(self, request, pk):
        admin = get_object_or_404(AdminUser, pk=pk)
        if "role" in request.data and request.data["role"] in AdminUser.Role.values:
            admin.role = request.data["role"]
        if "is_active" in request.data:
            admin.is_active = bool(request.data["is_active"])
        if request.data.get("password"):
            admin.set_password(str(request.data["password"]))
        if "full_name" in request.data:
            admin.full_name = request.data["full_name"]
        admin.save()
        _log(request.user, "admin_updated", admin.email)
        return Response(_admin_payload(admin))


class APIKeyListView(AdminAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response([
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.prefix,
                "trust_level": k.trust_level,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at,
                "created_at": k.created_at,
            }
            for k in APIKey.objects.all()
        ])

    def post(self, request):
        name = str(request.data.get("name", "")).strip()
        trust = request.data.get("trust_level", APIKey.Trust.DRAFT_ONLY)
        if not name or trust not in APIKey.Trust.values:
            return Response(
                {"detail": "name and a valid trust_level are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw, prefix, key_hash = APIKey.generate()
        key = APIKey.objects.create(
            name=name, prefix=prefix, key_hash=key_hash,
            trust_level=trust, created_by=request.user,
        )
        _log(request.user, "api_key_created", name, trust_level=trust)
        # The raw key is returned exactly once.
        return Response(
            {"id": str(key.id), "name": name, "key": raw,
             "trust_level": trust},
            status=status.HTTP_201_CREATED,
        )


class APIKeyRevokeView(AdminAPIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        key = get_object_or_404(APIKey, pk=pk)
        key.is_active = False
        key.save(update_fields=["is_active", "updated_at"])
        _log(request.user, "api_key_revoked", key.name)
        return Response({"ok": True})


class ImportLogListView(AdminAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response([
            {
                "id": str(log.id),
                "api_key": log.api_key.name if log.api_key else None,
                "publish_mode": log.publish_mode,
                "content_id": log.content_id,
                "content_title": log.content_title,
                "success": log.success,
                "detail": log.detail,
                "created_at": log.created_at,
            }
            for log in ImportLog.objects.select_related("api_key")[:200]
        ])


# =========================================================================== #
# Content Import API (v2 §5.1) — API-key auth, trust-tiered publish modes
# =========================================================================== #
class LessonImportView(APIView):
    """POST /api/v1/content/lessons/import  (Bearer <api_key>)."""

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]

    def post(self, request):
        api_key: APIKey = request.auth
        data = request.data if isinstance(request.data, dict) else {}
        # Draft is the safer default when unspecified (§5.1).
        mode = data.pop("publish_mode", "draft")
        if mode not in ("draft", "direct"):
            return Response(
                {"detail": "publish_mode must be 'draft' or 'direct'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Direct publishing needs the higher trust tier (§5.1).
        if mode == "direct" and api_key.trust_level != APIKey.Trust.DIRECT_PUBLISH:
            return Response(
                {"detail": "This API key may only submit drafts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_status = (
            Lesson.Status.PUBLISHED if mode == "direct" else Lesson.Status.DRAFT
        )
        try:
            lesson = import_lesson(data, status=target_status)
        except ImportValidationError as exc:
            ImportLog.objects.create(
                api_key=api_key, publish_mode=mode, content_id="",
                success=False, detail="; ".join(exc.errors),
            )
            return Response(
                {"detail": "Validation failed.", "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Every import is logged; direct publishes are the critical trail (§5.1).
        ImportLog.objects.create(
            api_key=api_key,
            publish_mode=mode,
            content_id=str(lesson.id),
            content_title=lesson.title,
            success=True,
        )
        return Response(
            {
                "lesson_id": str(lesson.id),
                "status": lesson.status,
                "publish_mode": mode,
                "review_required": mode == "draft",
            },
            status=status.HTTP_201_CREATED,
        )
