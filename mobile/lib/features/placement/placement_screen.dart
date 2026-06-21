import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/app_localizations.dart';

final _placementRepoProvider =
    Provider<_PlacementRepository>((ref) => _PlacementRepository(ref.read(dioProvider)));

class _PlacementRepository {
  _PlacementRepository(this._dio);
  final Dio _dio;

  Future<List<Map<String, dynamic>>> questions() async {
    final res = await _dio.get('/placement/test');
    return (res.data['questions'] as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> submit(Map<String, int> answers) async {
    final res = await _dio.post('/placement/submit', data: {'answers': answers});
    return res.data as Map<String, dynamic>;
  }
}

final _questionsProvider = FutureProvider<List<Map<String, dynamic>>>(
  (ref) => ref.read(_placementRepoProvider).questions(),
);

class PlacementScreen extends ConsumerStatefulWidget {
  const PlacementScreen({super.key});

  @override
  ConsumerState<PlacementScreen> createState() => _PlacementScreenState();
}

class _PlacementScreenState extends ConsumerState<PlacementScreen> {
  final Map<String, int> _answers = {};

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final questions = ref.watch(_questionsProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('placement_test'))),
      body: questions.when(
        data: (qs) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final q in qs)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(q['question'] as String),
                      for (int i = 0; i < (q['options'] as List).length; i++)
                        RadioListTile<int>(
                          value: i,
                          groupValue: _answers[q['id']],
                          title: Text(q['options'][i] as String),
                          onChanged: (v) =>
                              setState(() => _answers[q['id'] as String] = v!),
                        ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () async {
                final result =
                    await ref.read(_placementRepoProvider).submit(_answers);
                if (!context.mounted) return;
                final level = result['assigned_level']['name'];
                await showDialog(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: Text(t.t('placement_test')),
                    content: Text('$level\n${result['score']}/${result['total']}'),
                    actions: [
                      TextButton(
                        onPressed: () => context.go('/levels'),
                        child: Text(t.t('continue_')),
                      ),
                    ],
                  ),
                );
              },
              child: Text(t.t('submit')),
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}
