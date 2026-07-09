import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../tts/tts_service.dart';

/// Plays the generated feedback tones + haptics. Respects the app's sound
/// switch (soundEnabledProvider); haptics always fire (they're subtle).
class FeedbackService {
  FeedbackService(this._ref);

  final Ref _ref;
  final AudioPlayer _player = AudioPlayer();

  bool get _soundOn => _ref.read(soundEnabledProvider);

  Future<void> _play(String name) async {
    if (!_soundOn) return;
    try {
      await _player.stop();
      await _player.play(AssetSource('sounds/$name.wav'));
    } catch (_) {
      // Sound is decoration — never let it break the flow.
    }
  }

  Future<void> correct() async {
    HapticFeedback.lightImpact();
    await _play('correct');
  }

  /// Longer, richer celebration (~750ms) with a strong haptic — used by the
  /// bubble vocabulary quiz (UX prompt 1.1).
  Future<void> celebrate() async {
    HapticFeedback.heavyImpact();
    await _play('celebrate');
  }

  Future<void> wrong() async {
    HapticFeedback.mediumImpact();
    await _play('wrong');
  }

  Future<void> complete() async {
    HapticFeedback.lightImpact();
    await _play('complete');
  }

  Future<void> levelUp() async {
    HapticFeedback.heavyImpact();
    await _play('level_up');
  }

  void dispose() => _player.dispose();
}

final feedbackServiceProvider = Provider<FeedbackService>((ref) {
  final service = FeedbackService(ref);
  ref.onDispose(service.dispose);
  return service;
});
