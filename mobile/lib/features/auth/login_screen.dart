import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import 'auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final state = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(t.t('login')),
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            onPressed: () => ref.read(localeProvider.notifier).toggle(),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(t.t('app_title'),
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 24),
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
            if (state.error != null)
              Text(state.error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: state.loading
                  ? null
                  : () => ref
                      .read(authControllerProvider.notifier)
                      .login(_email.text.trim(), _password.text),
              child: state.loading
                  ? const CircularProgressIndicator()
                  : Text(t.t('login')),
            ),
            TextButton(
              onPressed: () => context.go('/register'),
              child: Text(t.t('register')),
            ),
          ],
        ),
      ),
    );
  }
}
