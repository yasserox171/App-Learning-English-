import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class StatsOverview {
  StatsOverview({
    required this.overallPercent,
    required this.lessonsCompleted,
    required this.totalLessons,
    required this.wordsLearned,
    required this.wordsMastered,
    required this.streak,
    required this.xp,
    required this.totalTimeSeconds,
  });

  final int overallPercent;
  final int lessonsCompleted;
  final int totalLessons;
  final int wordsLearned;
  final int wordsMastered;
  final int streak;
  final int xp;
  final int totalTimeSeconds;

  factory StatsOverview.fromJson(Map<String, dynamic> j) => StatsOverview(
        overallPercent: j['overall_percent'] ?? 0,
        lessonsCompleted: j['lessons_completed'] ?? 0,
        totalLessons: j['total_lessons'] ?? 0,
        wordsLearned: j['words_learned'] ?? 0,
        wordsMastered: j['words_mastered'] ?? 0,
        streak: j['streak'] ?? 0,
        xp: j['xp'] ?? 0,
        totalTimeSeconds: j['total_time_seconds'] ?? 0,
      );
}

class HeatmapUnit {
  HeatmapUnit({
    required this.unitId,
    required this.title,
    required this.levelCode,
    required this.totalWords,
    required this.learnedWords,
    required this.percent,
    required this.status,
  });

  final String unitId;
  final String title;
  final String levelCode;
  final int totalWords;
  final int learnedWords;
  final int percent;
  final String status; // strong | growing | weak

  factory HeatmapUnit.fromJson(Map<String, dynamic> j) => HeatmapUnit(
        unitId: j['unit_id'],
        title: j['title'] ?? '',
        levelCode: j['level_code'] ?? '',
        totalWords: j['total_words'] ?? 0,
        learnedWords: j['learned_words'] ?? 0,
        percent: j['percent'] ?? 0,
        status: j['status'] ?? 'weak',
      );
}

class SkillNode {
  SkillNode({
    required this.title,
    required this.levelCode,
    required this.attempts,
    required this.accuracy,
    required this.status,
  });

  final String title;
  final String levelCode;
  final int attempts;
  final int accuracy;
  final String status;

  factory SkillNode.fromJson(Map<String, dynamic> j) => SkillNode(
        title: j['title'] ?? '',
        levelCode: j['level_code'] ?? '',
        attempts: j['attempts'] ?? 0,
        accuracy: j['accuracy'] ?? 0,
        status: j['status'] ?? 'weak',
      );
}

class WeakArea {
  WeakArea({
    required this.title,
    required this.accuracy,
    required this.practiceLessonId,
  });

  final String title;
  final int accuracy;
  final String? practiceLessonId;

  factory WeakArea.fromJson(Map<String, dynamic> j) => WeakArea(
        title: j['title'] ?? '',
        accuracy: j['accuracy'] ?? 0,
        practiceLessonId: j['practice_lesson_id'],
      );
}

class DayTime {
  DayTime({required this.date, required this.seconds});

  final DateTime date;
  final int seconds;
}

class TimeInvestment {
  TimeInvestment({
    required this.days,
    required this.weekSeconds,
    required this.totalSeconds,
  });

  final List<DayTime> days;
  final List<int> weekSeconds;
  final int totalSeconds;

  factory TimeInvestment.fromJson(Map<String, dynamic> j) => TimeInvestment(
        days: [
          for (final d in (j['days'] as List? ?? const []))
            DayTime(
              date: DateTime.parse(d['date']),
              seconds: d['seconds'] ?? 0,
            ),
        ],
        weekSeconds: [
          for (final w in (j['weeks'] as List? ?? const []))
            (w['seconds'] ?? 0) as int,
        ],
        totalSeconds: j['total_seconds'] ?? 0,
      );
}

/// Everything the dashboard needs, fetched in parallel.
class StatsBundle {
  StatsBundle({
    required this.overview,
    required this.heatmap,
    required this.skills,
    required this.weakAreas,
    required this.time,
  });

  final StatsOverview overview;
  final List<HeatmapUnit> heatmap;
  final List<SkillNode> skills;
  final List<WeakArea> weakAreas;
  final TimeInvestment time;
}

class StatsRepository {
  StatsRepository(this._dio);

  final Dio _dio;

  Future<StatsBundle> load() async {
    final results = await Future.wait([
      _dio.get('/user/stats/overview'),
      _dio.get('/user/stats/vocabulary-heatmap'),
      _dio.get('/user/stats/grammar-skills'),
      _dio.get('/user/stats/weak-areas'),
      _dio.get('/user/stats/time-investment'),
    ]);
    return StatsBundle(
      overview: StatsOverview.fromJson(
          results[0].data as Map<String, dynamic>),
      heatmap: [
        for (final u in (results[1].data['units'] as List? ?? const []))
          HeatmapUnit.fromJson(u as Map<String, dynamic>),
      ],
      skills: [
        for (final s in (results[2].data['skills'] as List? ?? const []))
          SkillNode.fromJson(s as Map<String, dynamic>),
      ],
      weakAreas: [
        for (final a in (results[3].data['areas'] as List? ?? const []))
          WeakArea.fromJson(a as Map<String, dynamic>),
      ],
      time: TimeInvestment.fromJson(
          results[4].data as Map<String, dynamic>),
    );
  }
}

final statsRepositoryProvider = Provider<StatsRepository>(
  (ref) => StatsRepository(ref.read(dioProvider)),
);

final statsBundleProvider = FutureProvider<StatsBundle>(
  (ref) => ref.read(statsRepositoryProvider).load(),
);
