import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class NewsExercise {
  NewsExercise({
    required this.id,
    required this.template,
    required this.content,
    required this.order,
  });

  final String id;
  final String template;
  final Map<String, dynamic> content;
  final int order;

  factory NewsExercise.fromJson(Map<String, dynamic> j) => NewsExercise(
        id: j['id'],
        template: j['template'] ?? '',
        content: (j['content'] as Map?)?.cast<String, dynamic>() ?? {},
        order: j['order'] ?? 0,
      );
}

class NewsArticle {
  NewsArticle({
    required this.id,
    required this.titleEn,
    required this.titleAr,
    required this.contentShort,
    required this.source,
    required this.imageUrl,
    required this.difficulty,
    required this.exercises,
  });

  final String id;
  final String titleEn;
  final String titleAr;
  final String contentShort;
  final String source;
  final String imageUrl;
  final String difficulty;
  final List<NewsExercise> exercises;

  factory NewsArticle.fromJson(Map<String, dynamic> j) => NewsArticle(
        id: j['id'],
        titleEn: j['title_en'] ?? '',
        titleAr: j['title_ar'] ?? '',
        contentShort: j['content_short'] ?? '',
        source: j['source'] ?? '',
        imageUrl: j['image_url'] ?? '',
        difficulty: j['difficulty'] ?? '',
        exercises: [
          for (final e in (j['exercises'] as List? ?? const []))
            NewsExercise.fromJson(e as Map<String, dynamic>),
        ],
      );
}

class NewsSubmitResult {
  NewsSubmitResult({required this.isCorrect, required this.correctAnswer});

  final bool isCorrect;
  final String correctAnswer;
}

class NewsRepository {
  NewsRepository(this._dio);

  final Dio _dio;

  /// Today's story, or null when none is published (the Home card hides).
  Future<NewsArticle?> daily() async {
    try {
      final res = await _dio.get('/news/daily');
      return NewsArticle.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<NewsSubmitResult> submit(
    String articleId,
    String exerciseId,
    Map<String, dynamic> answer,
  ) async {
    final res = await _dio.post(
      '/news/$articleId/exercises/$exerciseId/submit',
      data: answer,
    );
    final data = res.data as Map<String, dynamic>;
    return NewsSubmitResult(
      isCorrect: data['is_correct'] == true,
      correctAnswer: (data['correct_answer'] ?? '').toString(),
    );
  }
}

final newsRepositoryProvider = Provider<NewsRepository>(
  (ref) => NewsRepository(ref.read(dioProvider)),
);

final dailyNewsProvider = FutureProvider<NewsArticle?>(
  (ref) => ref.read(newsRepositoryProvider).daily(),
);
