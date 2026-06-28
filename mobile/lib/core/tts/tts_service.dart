import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../settings/settings_storage.dart';

/// Thin wrapper around device text-to-speech, used to pronounce vocabulary.
class TtsService {
  TtsService() {
    _tts
      ..setLanguage('en-US')
      ..setSpeechRate(0.45)
      ..setPitch(1.0);
  }

  final FlutterTts _tts = FlutterTts();

  /// When false, [speak] becomes a no-op (controlled by the sound setting).
  bool enabled = true;

  Future<void> speak(String text) async {
    if (!enabled || text.trim().isEmpty) return;
    await _tts.stop();
    await _tts.speak(text);
  }

  Future<void> stop() => _tts.stop();
}

final ttsServiceProvider = Provider<TtsService>((ref) {
  final service = TtsService();
  ref.onDispose(service.stop);
  return service;
});

/// Persisted on/off switch for spoken audio; keeps [TtsService.enabled] in sync.
class SoundNotifier extends StateNotifier<bool> {
  SoundNotifier(this._tts, this._storage) : super(true) {
    _load();
  }

  final TtsService _tts;
  final SettingsStorage _storage;

  Future<void> _load() async {
    final v = await _storage.soundEnabled;
    state = v;
    _tts.enabled = v;
  }

  void set(bool value) {
    state = value;
    _tts.enabled = value;
    _storage.setSoundEnabled(value);
  }
}

final soundEnabledProvider = StateNotifierProvider<SoundNotifier, bool>(
  (ref) => SoundNotifier(
    ref.read(ttsServiceProvider),
    ref.read(settingsStorageProvider),
  ),
);
