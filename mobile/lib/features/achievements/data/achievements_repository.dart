import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class AchievementBadge {
  AchievementBadge({
    required this.type,
    required this.icon,
    required this.titleEn,
    required this.titleAr,
    required this.descriptionEn,
    required this.descriptionAr,
    required this.unlocked,
    this.unlockedAt,
  });

  final String type;
  final String icon;
  final String titleEn;
  final String titleAr;
  final String descriptionEn;
  final String descriptionAr;
  final bool unlocked;
  final String? unlockedAt;

  String title(String lang) => lang == 'ar' ? titleAr : titleEn;
  String description(String lang) =>
      lang == 'ar' ? descriptionAr : descriptionEn;

  factory AchievementBadge.fromJson(Map<String, dynamic> j) =>
      AchievementBadge(
        type: j['type'] ?? '',
        icon: j['icon'] ?? '🏆',
        titleEn: j['title_en'] ?? '',
        titleAr: j['title_ar'] ?? '',
        descriptionEn: j['description_en'] ?? '',
        descriptionAr: j['description_ar'] ?? '',
        unlocked: j['unlocked'] == true,
        unlockedAt: j['unlocked_at'],
      );
}

class AchievementsPayload {
  AchievementsPayload({required this.badges, required this.newlyUnlocked});

  final List<AchievementBadge> badges;

  /// Types unlocked by this very request — the app pops a dialog for them.
  final List<String> newlyUnlocked;

  factory AchievementsPayload.fromJson(Map<String, dynamic> j) =>
      AchievementsPayload(
        badges: [
          for (final b in (j['badges'] as List? ?? const []))
            AchievementBadge.fromJson(b as Map<String, dynamic>),
        ],
        newlyUnlocked: [
          for (final t in (j['newly_unlocked'] as List? ?? const [])) '$t',
        ],
      );
}

class NotificationPrefs {
  const NotificationPrefs({
    this.streakReminder = true,
    this.contentAlert = true,
    this.weakAreaAlert = true,
    this.achievementAlert = true,
    this.preferredTime = '08:00',
  });

  final bool streakReminder;
  final bool contentAlert;
  final bool weakAreaAlert;
  final bool achievementAlert;
  final String preferredTime; // HH:MM

  int get hour => int.tryParse(preferredTime.split(':').first) ?? 8;
  int get minute => int.tryParse(preferredTime.split(':').last) ?? 0;

  NotificationPrefs copyWith({
    bool? streakReminder,
    bool? contentAlert,
    bool? weakAreaAlert,
    bool? achievementAlert,
    String? preferredTime,
  }) =>
      NotificationPrefs(
        streakReminder: streakReminder ?? this.streakReminder,
        contentAlert: contentAlert ?? this.contentAlert,
        weakAreaAlert: weakAreaAlert ?? this.weakAreaAlert,
        achievementAlert: achievementAlert ?? this.achievementAlert,
        preferredTime: preferredTime ?? this.preferredTime,
      );

  Map<String, dynamic> toJson() => {
        'streak_reminder': streakReminder,
        'content_alert': contentAlert,
        'weak_area_alert': weakAreaAlert,
        'achievement_alert': achievementAlert,
        'preferred_time': preferredTime,
      };

  factory NotificationPrefs.fromJson(Map<String, dynamic> j) =>
      NotificationPrefs(
        streakReminder: j['streak_reminder'] ?? true,
        contentAlert: j['content_alert'] ?? true,
        weakAreaAlert: j['weak_area_alert'] ?? true,
        achievementAlert: j['achievement_alert'] ?? true,
        preferredTime: j['preferred_time'] ?? '08:00',
      );
}

class AchievementsRepository {
  AchievementsRepository(this._dio);

  final Dio _dio;

  Future<AchievementsPayload> all() async {
    final res = await _dio.get('/user/achievements/all');
    return AchievementsPayload.fromJson(res.data as Map<String, dynamic>);
  }

  Future<NotificationPrefs> notificationPrefs() async {
    final res = await _dio.get('/notifications/preferences');
    return NotificationPrefs.fromJson(res.data as Map<String, dynamic>);
  }

  Future<NotificationPrefs> saveNotificationPrefs(
      NotificationPrefs prefs) async {
    final res =
        await _dio.post('/notifications/preferences', data: prefs.toJson());
    return NotificationPrefs.fromJson(res.data as Map<String, dynamic>);
  }
}

final achievementsRepositoryProvider = Provider<AchievementsRepository>(
  (ref) => AchievementsRepository(ref.read(dioProvider)),
);

final achievementsProvider = FutureProvider<AchievementsPayload>(
  (ref) => ref.read(achievementsRepositoryProvider).all(),
);

final notificationPrefsProvider = FutureProvider<NotificationPrefs>(
  (ref) => ref.read(achievementsRepositoryProvider).notificationPrefs(),
);
