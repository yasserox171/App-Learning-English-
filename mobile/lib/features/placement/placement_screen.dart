import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/app_localizations.dart';

/// Adaptive placement test (v2 §1.2): rounds of 5 questions starting at A2,
/// moving up/down by thresholds until the level settles. Always optional —
/// reached from "Test your level", never forced.
final _placementRepoProvider = Provider<_PlacementRepository>(
    (ref) => _PlacementRepository(ref.read(dioProvider)));

class _PlacementRepository {
  _PlacementRepository(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> start() async {
    final res = await _dio.post('/placement/start');
    return res.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> answer(
      String sessionId, Map<String, int> answers) async {
    final res = await _dio.post('/placement/answer',
        data: {'session_id': sessionId, 'answers': answers});
    return res.data as Map<String, dynamic>;
  }
}

class PlacementScreen extends ConsumerStatefulWidget {
  const PlacementScreen({super.key});

  @override
  ConsumerState<PlacementScreen> createState() => _PlacementScreenState();
}

class _PlacementScreenState extends ConsumerState<PlacementScreen> {
  String? _sessionId;
  String _level = 'A2';
  int _round = 1;
  List<Map<String, dynamic>> _questions = [];
  final Map<String, int> _answers = {};
  Map<String, dynamic>? _result; // set when completed
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    try {
      final data = await ref.read(_placementRepoProvider).start();
      setState(() {
        _sessionId = data['session_id'] as String;
        _level = data['level'] as String;
        _round = data['round'] as int;
        _questions = (data['questions'] as List).cast<Map<String, dynamic>>();
        _answers.clear();
      });
    } catch (e) {
      setState(() => _error = '$e');
    }
  }

  Future<void> _submitRound() async {
    if (_busy || _sessionId == null) return;
    setState(() => _busy = true);
    try {
      final data =
          await ref.read(_placementRepoProvider).answer(_sessionId!, _answers);
      if (data['completed'] == true) {
        setState(() => _result = data);
      } else {
        setState(() {
          _level = data['level'] as String;
          _round = data['round'] as int;
          _questions =
              (data['questions'] as List).cast<Map<String, dynamic>>();
          _answers.clear();
        });
      }
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: Text(t.t('placement_test'))),
        body: Center(child: Text(_error!)),
      );
    }
    if (_result != null) return _ResultView(result: _result!);
    if (_questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text(t.t('placement_test'))),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final allAnswered =
        _questions.every((q) => _answers.containsKey(q['id']));

    return Scaffold(
      appBar: AppBar(
        title: Text('${t.t('placement_test')} · $_level'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(value: _round / 4),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final q in _questions)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if ((q['passage'] ?? '') != '')
                      Container(
                        padding: const EdgeInsets.all(10),
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          color: Theme.of(context)
                              .colorScheme
                              .surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(q['passage'] as String,
                            textDirection: TextDirection.ltr),
                      ),
                    Text(q['question'] as String,
                        textDirection: TextDirection.ltr),
                    for (int i = 0; i < (q['options'] as List).length; i++)
                      RadioListTile<int>(
                        value: i,
                        groupValue: _answers[q['id']],
                        title: Text(q['options'][i] as String,
                            textDirection: TextDirection.ltr),
                        onChanged: (v) =>
                            setState(() => _answers[q['id'] as String] = v!),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: allAnswered && !_busy ? _submitRound : null,
            child: _busy
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : Text(t.t('submit')),
          ),
        ],
      ),
    );
  }
}

/// Result screen (§1.2): suggested level as the prominent default action,
/// with "start from A1" and "choose manually" always available.
class _ResultView extends StatelessWidget {
  const _ResultView({required this.result});

  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final suggested = result['suggested_level'] as String;
    final options = (result['options'] as Map?)?.cast<String, dynamic>() ?? {};
    final manual =
        (options['manual_choice'] as List? ?? const []).cast<String>();

    return Scaffold(
      appBar: AppBar(title: Text(t.t('placement_result_title'))),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 24),
            Text('🎯', style: Theme.of(context).textTheme.displayLarge),
            const SizedBox(height: 8),
            Text(suggested,
                style: Theme.of(context)
                    .textTheme
                    .displayMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            Text('${result['correct']}/${result['total']}'),
            const SizedBox(height: 32),
            FilledButton(
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
                textStyle:
                    const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
              onPressed: () => context.go('/learn'),
              child: Text('${t.t('start_at')} $suggested'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48)),
              onPressed: () => context.go('/learn'),
              child: Text(t.t('start_from_a1')),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () async {
                await showModalBottomSheet(
                  context: context,
                  builder: (sheetContext) => SafeArea(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        for (final code in manual)
                          ListTile(
                            title: Text(code),
                            onTap: () {
                              Navigator.pop(sheetContext);
                              context.go('/learn');
                            },
                          ),
                      ],
                    ),
                  ),
                );
              },
              child: Text(t.t('choose_level_manually')),
            ),
          ],
        ),
      ),
    );
  }
}
