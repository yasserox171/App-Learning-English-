"""News Learning endpoints (UX prompt 2.1):

GET  /news/daily                          today's story + 3 free exercises
GET  /news/archive                        unexpired stories (7-day window)
POST /news/<id>/exercises/<ex_id>/submit  server-side correction
"""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.exercises.correctors import answer_text, get_corrector

from .models import NewsArticle, NewsExercise
from .serializers import NewsArticleListSerializer, NewsArticleSerializer


def _live_articles():
    return NewsArticle.objects.filter(expiry_date__gt=timezone.now())


class DailyNewsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _live_articles()


class NewsArticleDetailView(generics.RetrieveAPIView):
    serializer_class = NewsArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = NewsArticle.objects.all()


class NewsExerciseSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, article_id, exercise_id):
        exercise = get_object_or_404(
            NewsExercise, pk=exercise_id, article_id=article_id
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
        payload = {"is_correct": is_correct, "score": score}
        if not is_correct:
            payload["correct_answer"] = answer_text(
                exercise.template, exercise.content
            )
        return Response(payload)
