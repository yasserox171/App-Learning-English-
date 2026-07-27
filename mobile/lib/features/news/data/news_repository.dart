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

/// Archive row — enough for the Home list, without the exercises payload.
class NewsSummary {
  NewsSummary({
    required this.id,
    required this.titleEn,
    required this.titleAr,
    required this.source,
    required this.imageUrl,
    required this.difficulty,
  });

  final String id;
  final String titleEn;
  final String titleAr;
  final String source;
  final String imageUrl;
  final String difficulty;

  factory NewsSummary.fromJson(Map<String, dynamic> j) => NewsSummary(
        id: j['id'],
        titleEn: j['title_en'] ?? '',
        titleAr: j['title_ar'] ?? '',
        source: j['source'] ?? '',
        imageUrl: j['image_url'] ?? '',
        difficulty: j['difficulty'] ?? '',
      );
}

class NewsSubmitResult {
  NewsSubmitResult({
    required this.isCorrect,
    required this.correctAnswer,
    this.coinsAwarded = 0,
    this.bonusAwarded = 0,
    this.capReached = false,
    this.balance = 0,
  });

  final bool isCorrect;
  final String correctAnswer;
  // v2 §2.3 coins economy
  final int coinsAwarded;
  final int bonusAwarded;
  final bool capReached;
  final int balance;
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

  /// Recent unexpired stories (newest first) for the Home list.
  Future<List<NewsSummary>> archive() async {
    final res = await _dio.get('/news/archive');
    final data = res.data;
    final list = (data is Map && data.containsKey('results'))
        ? data['results'] as List
        : data as List;
    return [
      for (final e in list) NewsSummary.fromJson(e as Map<String, dynamic>),
    ];
  }

  /// One story with its exercises (opened from the Home list).
  Future<NewsArticle> byId(String id) async {
    final res = await _dio.get('/news/$id');
    return NewsArticle.fromJson(res.data as Map<String, dynamic>);
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
      coinsAwarded: (data['coins_awarded'] ?? 0) as int,
      bonusAwarded: (data['bonus_awarded'] ?? 0) as int,
      capReached: data['cap_reached'] == true,
      balance: (data['balance'] ?? 0) as int,
    );
  }

  /// Personalized feed (v2 §2.2): interests + level + country/global.
  Future<List<NewsSummary>> feed() async {
    final res = await _dio.get('/news/feed');
    final data = res.data;
    final list = (data is Map && data.containsKey('results'))
        ? data['results'] as List
        : data as List;
    return [
      for (final e in list) NewsSummary.fromJson(e as Map<String, dynamic>),
    ];
  }
}

final newsRepositoryProvider = Provider<NewsRepository>(
  (ref) => NewsRepository(ref.read(dioProvider)),
);

final dailyNewsProvider = FutureProvider<NewsArticle?>(
  (ref) => ref.read(newsRepositoryProvider).daily(),
);

/// Home list now reads the personalized feed (v2 §2.2); the server falls
/// back to the general archive when the filters would return nothing.
final newsArchiveProvider = FutureProvider<List<NewsSummary>>(
  (ref) => ref.read(newsRepositoryProvider).feed(),
);

final newsArticleProvider = FutureProvider.family<NewsArticle, String>(
  (ref, id) => ref.read(newsRepositoryProvider).byId(id),
);
