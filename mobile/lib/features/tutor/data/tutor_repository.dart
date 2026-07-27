import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class TutorTurn {
  TutorTurn({required this.role, required this.text});

  final String role; // assistant | user
  final String text;
}

class TutorSessionStart {
  TutorSessionStart({
    required this.sessionId,
    required this.openingText,
    this.openingAudioB64,
    required this.targetVocabulary,
    required this.maxExchanges,
  });

  final String sessionId;
  final String openingText;
  final String? openingAudioB64;
  final List<String> targetVocabulary;
  final int maxExchanges;

  factory TutorSessionStart.fromJson(Map<String, dynamic> j) =>
      TutorSessionStart(
        sessionId: j['session_id'],
        openingText: j['opening_text'] ?? '',
        openingAudioB64: j['opening_audio_b64'],
        targetVocabulary: [
          for (final w in (j['target_vocabulary'] as List? ?? const [])) '$w'
        ],
        maxExchanges: j['max_exchanges'] ?? 6,
      );
}

class TutorTurnResult {
  TutorTurnResult({
    required this.transcript,
    required this.replyText,
    this.replyAudioB64,
    required this.exchange,
    required this.maxExchanges,
    required this.ended,
  });

  final String transcript;
  final String replyText;
  final String? replyAudioB64;
  final int exchange;
  final int maxExchanges;
  final bool ended;

  factory TutorTurnResult.fromJson(Map<String, dynamic> j) => TutorTurnResult(
        transcript: j['transcript'] ?? '',
        replyText: j['reply_text'] ?? '',
        replyAudioB64: j['reply_audio_b64'],
        exchange: j['exchange'] ?? 0,
        maxExchanges: j['max_exchanges'] ?? 6,
        ended: j['ended'] == true,
      );
}

class TutorResult {
  TutorResult({required this.termsUsed, required this.termsTotal});

  final int termsUsed;
  final int termsTotal;
}

class TutorRepository {
  TutorRepository(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> usage() async {
    final res = await _dio.get('/tutor/usage');
    return res.data as Map<String, dynamic>;
  }

  Future<TutorSessionStart> start(String lessonId) async {
    final res =
        await _dio.post('/tutor/sessions', data: {'lesson_id': lessonId});
    return TutorSessionStart.fromJson(res.data as Map<String, dynamic>);
  }

  /// One exchange. The app sends the on-device transcript as text; the
  /// backend also accepts multipart audio for server-side Whisper STT.
  Future<TutorTurnResult> turn(String sessionId, {required String text}) async {
    final res = await _dio.post(
      '/tutor/sessions/$sessionId/turn',
      data: {'text': text},
    );
    return TutorTurnResult.fromJson(res.data as Map<String, dynamic>);
  }

  Future<TutorResult> end(String sessionId) async {
    final res = await _dio.post('/tutor/sessions/$sessionId/end');
    final data = res.data as Map<String, dynamic>;
    return TutorResult(
      termsUsed: data['terms_used'] ?? 0,
      termsTotal: data['terms_total'] ?? 0,
    );
  }
}

final tutorRepositoryProvider = Provider<TutorRepository>(
  (ref) => TutorRepository(ref.read(dioProvider)),
);
