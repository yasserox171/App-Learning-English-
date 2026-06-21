import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import 'models.dart';

class ContentRepository {
  ContentRepository(this._dio);

  final Dio _dio;

  List<T> _results<T>(Response res, T Function(Map<String, dynamic>) fromJson) {
    final data = res.data;
    final list = (data is Map && data.containsKey('results'))
        ? data['results'] as List
        : data as List;
    return list.map((e) => fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Level>> levels() async =>
      _results(await _dio.get('/levels'), Level.fromJson);

  Future<List<Unit>> units(String levelId) async =>
      _results(await _dio.get('/levels/$levelId/units'), Unit.fromJson);

  Future<List<LessonSummary>> lessons(String unitId) async =>
      _results(await _dio.get('/units/$unitId/lessons'), LessonSummary.fromJson);

  Future<LessonDetail> lesson(String lessonId) async {
    final res = await _dio.get('/lessons/$lessonId');
    return LessonDetail.fromJson(res.data as Map<String, dynamic>);
  }
}

final contentRepositoryProvider = Provider<ContentRepository>(
  (ref) => ContentRepository(ref.read(dioProvider)),
);

final levelsProvider =
    FutureProvider<List<Level>>((ref) => ref.read(contentRepositoryProvider).levels());

final unitsProvider = FutureProvider.family<List<Unit>, String>(
  (ref, levelId) => ref.read(contentRepositoryProvider).units(levelId),
);

final lessonsProvider = FutureProvider.family<List<LessonSummary>, String>(
  (ref, unitId) => ref.read(contentRepositoryProvider).lessons(unitId),
);

final lessonProvider = FutureProvider.family<LessonDetail, String>(
  (ref, lessonId) => ref.read(contentRepositoryProvider).lesson(lessonId),
);
