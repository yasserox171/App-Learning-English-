import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class AttemptResult {
  AttemptResult({required this.isCorrect, required this.score, required this.maxScore});

  final bool isCorrect;
  final int score;
  final int maxScore;

  factory AttemptResult.fromJson(Map<String, dynamic> j) => AttemptResult(
        isCorrect: j['is_correct'] as bool,
        score: j['score'] as int,
        maxScore: j['max_score'] as int,
      );
}

class ExerciseRepository {
  ExerciseRepository(this._dio);

  final Dio _dio;

  Future<AttemptResult> attempt(String exerciseId, Map<String, dynamic> answer) async {
    final res = await _dio.post(
      '/exercises/$exerciseId/attempt',
      data: {'answer': answer},
    );
    return AttemptResult.fromJson(res.data as Map<String, dynamic>);
  }
}

final exerciseRepositoryProvider = Provider<ExerciseRepository>(
  (ref) => ExerciseRepository(ref.read(dioProvider)),
);
