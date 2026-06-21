import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import 'auth_controller.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  String _goal = 'study';

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final state = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('register'))),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            TextField(
              controller: _name,
              decoration: InputDecoration(labelText: t.t('full_name')),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _email,
              decoration: InputDecoration(labelText: t.t('email')),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              decoration: InputDecoration(labelText: t.t('password')),
              obscureText: true,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _goal,
              items: const [
                DropdownMenuItem(value: 'study', child: Text('Study')),
                DropdownMenuItem(value: 'work', child: Text('Work')),
                DropdownMenuItem(value: 'travel', child: Text('Travel')),
                DropdownMenuItem(
                    value: 'communication', child: Text('Communication')),
              ],
              onChanged: (v) => setState(() => _goal = v ?? 'study'),
            ),
            const SizedBox(height: 12),
            if (state.error != null)
              Text(state.error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: state.loading
                  ? null
                  : () => ref.read(authControllerProvider.notifier).register(
                        email: _email.text.trim(),
                        password: _password.text,
                        fullName: _name.text,
                        learningGoal: _goal,
                      ),
              child: state.loading
                  ? const CircularProgressIndicator()
                  : Text(t.t('register')),
            ),
            TextButton(
              onPressed: () => context.go('/login'),
              child: Text(t.t('login')),
            ),
          ],
        ),
      ),
    );
  }
}
