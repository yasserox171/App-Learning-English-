import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Thin wrapper around device text-to-speech, used to pronounce vocabulary.
class TtsService {
  TtsService() {
    _tts
      ..setLanguage('en-US')
      ..setSpeechRate(0.45)
      ..setPitch(1.0);
  }

  final FlutterTts _tts = FlutterTts();

  Future<void> speak(String text) async {
    if (text.trim().isEmpty) return;
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
