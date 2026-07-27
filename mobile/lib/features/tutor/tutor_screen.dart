import 'dart:convert';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../core/i18n/app_localizations.dart';
import 'data/tutor_repository.dart';

/// AI Tutor voice conversation (v2 §3): a capped, lesson-themed spoken
/// exchange. Speech is captured on-device, the tutor's reply text comes from
/// Claude and its voice from Google Cloud TTS (played from base64 MP3).
class TutorScreen extends ConsumerStatefulWidget {
  const TutorScreen({super.key, required this.lessonId});

  final String lessonId;

  @override
  ConsumerState<TutorScreen> createState() => _TutorScreenState();
}

class _TutorScreenState extends ConsumerState<TutorScreen> {
  final _speech = stt.SpeechToText();
  final _player = AudioPlayer();

  TutorSessionStart? _session;
  final List<TutorTurn> _turns = [];
  bool _listening = false;
  bool _thinking = false;
  bool _ended = false;
  String _partial = '';
  String? _error;
  TutorResult? _result;

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _speech.stop();
    _player.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    try {
      final session =
          await ref.read(tutorRepositoryProvider).start(widget.lessonId);
      setState(() {
        _session = session;
        _turns.add(TutorTurn(role: 'assistant', text: session.openingText));
      });
      _playB64(session.openingAudioB64);
    } catch (e) {
      if (!mounted) return;
      final code = (e is Exception && '$e'.contains('429')) ? 429 : 0;
      setState(() {
        _error = code == 429
            ? AppLocalizations.of(context).t('tutor_daily_limit')
            : '$e';
      });
    }
  }

  Future<void> _playB64(String? b64) async {
    if (b64 == null || b64.isEmpty) return;
    try {
      await _player.play(BytesSource(base64Decode(b64)));
    } catch (_) {/* audio is best-effort; the text is always shown */}
  }

  Future<void> _toggleListen() async {
    if (_listening) {
      await _speech.stop();
      setState(() => _listening = false);
      if (_partial.trim().isNotEmpty) await _sendTurn(_partial.trim());
      return;
    }
    final available = await _speech.initialize();
    if (!available) return;
    setState(() {
      _listening = true;
      _partial = '';
    });
    await _speech.listen(
      localeId: 'en_US',
      onResult: (result) {
        setState(() => _partial = result.recognizedWords);
        if (result.finalResult && _partial.trim().isNotEmpty) {
          _speech.stop();
          setState(() => _listening = false);
          _sendTurn(_partial.trim());
        }
      },
    );
  }

  Future<void> _sendTurn(String text) async {
    final session = _session;
    if (session == null || _thinking || _ended) return;
    setState(() {
      _turns.add(TutorTurn(role: 'user', text: text));
      _thinking = true;
      _partial = '';
    });
    try {
      final result = await ref
          .read(tutorRepositoryProvider)
          .turn(session.sessionId, text: text);
      if (!mounted) return;
      setState(() {
        _turns.add(TutorTurn(role: 'assistant', text: result.replyText));
        _thinking = false;
        _ended = result.ended;
      });
      _playB64(result.replyAudioB64);
      if (result.ended) _finish();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _thinking = false;
        _error = '$e';
      });
    }
  }

  Future<void> _finish() async {
    final session = _session;
    if (session == null) return;
    try {
      final result =
          await ref.read(tutorRepositoryProvider).end(session.sessionId);
      if (!mounted) return;
      setState(() {
        _ended = true;
        _result = result;
      });
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final session = _session;

    return Scaffold(
      appBar: AppBar(
        title: Text('🎙️ ${t.t('ai_tutor')}'),
        actions: [
          if (session != null && !_ended)
            TextButton(
              onPressed: _finish,
              child: Text(MaterialLocalizations.of(context).okButtonLabel),
            ),
        ],
      ),
      body: _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(_error!, textAlign: TextAlign.center),
              ),
            )
          : session == null
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    // Target vocabulary chips (§3.2)
                    if (session.targetVocabulary.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                        child: Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            for (final word in session.targetVocabulary)
                              Chip(
                                label: Text(word,
                                    style: const TextStyle(fontSize: 12)),
                                visualDensity: VisualDensity.compact,
                              ),
                          ],
                        ),
                      ),
                    Expanded(
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _turns.length + (_thinking ? 1 : 0),
                        itemBuilder: (context, i) {
                          if (i == _turns.length) {
                            return Align(
                              alignment: Alignment.centerLeft,
                              child: _bubble(
                                  t.t('tutor_thinking'), false, scheme),
                            );
                          }
                          final turn = _turns[i];
                          final isUser = turn.role == 'user';
                          return Align(
                            alignment: isUser
                                ? Alignment.centerRight
                                : Alignment.centerLeft,
                            child: _bubble(turn.text, isUser, scheme),
                          );
                        },
                      ),
                    ),
                    if (_result != null)
                      Container(
                        margin: const EdgeInsets.all(16),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: scheme.primaryContainer,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          children: [
                            Text('🎉 ${t.t('tutor_session_done')}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold)),
                            const SizedBox(height: 6),
                            Text(
                              '${t.t('tutor_terms_used')}: '
                              '${_result!.termsUsed} / ${_result!.termsTotal}',
                            ),
                          ],
                        ),
                      ),
                    if (!_ended)
                      Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          children: [
                            if (_listening)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Text(
                                  _partial.isEmpty
                                      ? t.t('tutor_listening')
                                      : _partial,
                                  style: TextStyle(
                                      color: scheme.onSurfaceVariant),
                                ),
                              ),
                            GestureDetector(
                              onTap: _thinking ? null : _toggleListen,
                              child: CircleAvatar(
                                radius: 36,
                                backgroundColor: _listening
                                    ? Colors.red
                                    : scheme.primary,
                                child: Icon(
                                  _listening ? Icons.stop : Icons.mic,
                                  color: Colors.white,
                                  size: 34,
                                ),
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(t.t('tutor_tap_to_speak'),
                                style: const TextStyle(fontSize: 12)),
                          ],
                        ),
                      ),
                  ],
                ),
    );
  }

  Widget _bubble(String text, bool isUser, ColorScheme scheme) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      constraints: const BoxConstraints(maxWidth: 300),
      decoration: BoxDecoration(
        color: isUser ? scheme.primary : scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        text,
        style: TextStyle(color: isUser ? Colors.white : null),
        textDirection: TextDirection.ltr,
      ),
    );
  }
}
