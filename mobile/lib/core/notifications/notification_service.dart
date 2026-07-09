import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Local notifications (UX prompt 2.3): a daily streak reminder scheduled at
/// the learner's preferred time, plus instant notifications for unlocked
/// achievements. Everything is opt-in via the backend-synced preferences.
class NotificationService {
  static const _streakId = 1001;
  static const _channel = AndroidNotificationDetails(
    'reminders',
    'Reminders',
    channelDescription: 'Daily streak reminders and achievement unlocks',
    importance: Importance.defaultImportance,
    priority: Priority.defaultPriority,
  );

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _ready = false;

  Future<bool> _init() async {
    if (_ready) return true;
    try {
      tzdata.initializeTimeZones();
      const settings = InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      );
      await _plugin.initialize(settings);
      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
      _ready = true;
    } catch (_) {
      // Notifications are optional; never break the app over them.
    }
    return _ready;
  }

  /// (Re)schedules the daily streak reminder, or cancels it when disabled.
  ///
  /// The recurrence is anchored to the current UTC offset (no extra timezone
  /// plugin); after a DST-style clock change it drifts by the offset delta
  /// until the app is next opened, which reschedules it.
  Future<void> scheduleStreakReminder({
    required bool enabled,
    required TimeOfDay time,
  }) async {
    if (!await _init()) return;
    try {
      await _plugin.cancel(_streakId);
      if (!enabled) return;

      final now = DateTime.now();
      var next = DateTime(now.year, now.month, now.day, time.hour, time.minute);
      if (!next.isAfter(now)) next = next.add(const Duration(days: 1));

      await _plugin.zonedSchedule(
        _streakId,
        '🔥 English Master',
        'احفظ streak اليوم! درس واحد يكفي للحفاظ على سلسلتك.',
        tz.TZDateTime.from(next.toUtc(), tz.UTC),
        const NotificationDetails(
          android: _channel,
          iOS: DarwinNotificationDetails(),
        ),
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        matchDateTimeComponents: DateTimeComponents.time,
      );
    } catch (_) {/* optional feature */}
  }

  /// Instant "achievement unlocked" notification (respects the preference —
  /// callers check it before invoking).
  Future<void> showAchievement(String title, String body) async {
    if (!await _init()) return;
    try {
      await _plugin.show(
        DateTime.now().millisecondsSinceEpoch ~/ 1000,
        title,
        body,
        const NotificationDetails(
          android: _channel,
          iOS: DarwinNotificationDetails(),
        ),
      );
    } catch (_) {/* optional feature */}
  }
}

final notificationServiceProvider =
    Provider<NotificationService>((_) => NotificationService());
