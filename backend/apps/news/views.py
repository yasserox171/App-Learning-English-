"""News & Stories endpoints (v2 §2.2/§2.3).

GET  /news/feed        personalized: interests + level + country/global
GET  /news/categories  interest categories (for pickers)
GET  /news/daily       latest published story (legacy, kept for old clients)
GET  /news/archive     unexpired published stories
GET  /news/<id>        article detail (includes body + questions)
POST /news/<id>/exercises/<ex_id>/submit   server-side correction + coins

Reading is open — no registered account required (guests hold real JWTs, and
even unauthenticated reads are allowed per §2.2). Earning coins requires a
user (guest or registered).
"""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.exercises.correctors import answer_text, get_corrector

from . import services
from .models import Category, NewsArticle, NewsExercise
from .serializers import (
    CategorySerializer,
    NewsArticleListSerializer,
    NewsArticleSerializer,
)


def _live_articles():
    return NewsArticle.objects.filter(
        status=NewsArticle.Status.PUBLISHED, expiry_date__gt=timezone.now()
    )


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class NewsFeedView(generics.ListAPIView):
    """Personalized feed (v2 §2.2)."""

    serializer_class = NewsArticleListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return services.personalized_feed(self.request.user)


class DailyNewsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        article = _live_articles().first()
        if article is None:
            return Response(
                {"detail": "No news available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(NewsArticleSerializer(article).data)


class NewsArchiveView(generics.ListAPIView):
    serializer_class = NewsArticleListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return _live_articles()


class NewsArticleDetailView(generics.RetrieveAPIView):
    serializer_class = NewsArticleSerializer
    permission_classes = [permissions.AllowAny]
    queryset = NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED)


class NewsExerciseSubmitView(APIView):
    """Server-side correction (never trust a client 'correct' flag — §2.3)
    + coin awarding with daily cap and anti-farming."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, article_id, exercise_id):
        exercise = get_object_or_404(
            NewsExercise,
            pk=exercise_id,
            article_id=article_id,
            article__status=NewsArticle.Status.PUBLISHED,
        )
        answer = request.data if isinstance(request.data, dict) else {}
        try:
            corrector = get_corrector(exercise.template)
        except ValueError:
            return Response(
                {"detail": "Unsupported exercise template."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_correct, score = corrector.check(exercise.content, answer)

        economy = services.submit_answer(request.user, exercise, is_correct)

        payload = {"is_correct": is_correct, "score": score, **economy}
        if not is_correct:
            payload["correct_answer"] = answer_text(
                exercise.template, exercise.content
            )
        return Response(payload)
