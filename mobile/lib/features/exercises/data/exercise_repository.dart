import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class AttemptResult {
  AttemptResult({
    required this.isCorrect,
    required this.score,
    required this.maxScore,
    this.correctAnswer,
  });

  final bool isCorrect;
  final int score;
  final int maxScore;

  /// Present when the answer was wrong — used for the correction tooltip.
  final String? correctAnswer;

  factory AttemptResult.fromJson(Map<String, dynamic> j) => AttemptResult(
        isCorrect: j['is_correct'] as bool,
        score: j['score'] as int,
        maxScore: j['max_score'] as int,
        correctAnswer: j['correct_answer'] as String?,
      );
}

class HintResult {
  HintResult({required this.level, this.hint, this.eliminate = const []});

  final int level;
  final String? hint;

  /// Option indexes to strike out (multiple choice / listening, level 1).
  final List<int> eliminate;

  factory HintResult.fromJson(Map<String, dynamic> j) => HintResult(
        level: j['level'] ?? 1,
        hint: j['hint'] as String?,
        eliminate: ((j['eliminate'] as List?) ?? const []).cast<int>(),
      );
}

class ExerciseRepository {
  ExerciseRepository(this._dio);

  final Dio _dio;

  Future<AttemptResult> attempt(
    String exerciseId,
    Map<String, dynamic> answer, {
    bool usedHint = false,
  }) async {
    final res = await _dio.post(
      '/exercises/$exerciseId/attempt',
      data: {'answer': answer, if (usedHint) 'used_hint': true},
    );
    return AttemptResult.fromJson(res.data as Map<String, dynamic>);
  }

  Future<HintResult> hint(String exerciseId, int level) async {
    final res = await _dio.post(
      '/exercises/$exerciseId/hint',
      data: {'level': level},
    );
    return HintResult.fromJson(res.data as Map<String, dynamic>);
  }
}

final exerciseRepositoryProvider = Provider<ExerciseRepository>(
  (ref) => ExerciseRepository(ref.read(dioProvider)),
);
