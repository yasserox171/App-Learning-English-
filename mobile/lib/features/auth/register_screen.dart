import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/widgets/app_logo.dart';
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
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final state = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('create_account'))),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Center(child: AppLogo(size: 72)),
              const SizedBox(height: 24),
              TextField(
                controller: _name,
                decoration: InputDecoration(
                  labelText: t.t('full_name'),
                  prefixIcon: const Icon(Icons.person_outline),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  labelText: t.t('email'),
                  prefixIcon: const Icon(Icons.mail_outline),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _password,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: t.t('password'),
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _goal,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.flag_outlined),
                ),
                items: const [
                  DropdownMenuItem(value: 'study', child: Text('Study')),
                  DropdownMenuItem(value: 'work', child: Text('Work')),
                  DropdownMenuItem(value: 'travel', child: Text('Travel')),
                  DropdownMenuItem(
                      value: 'communication', child: Text('Communication')),
                ],
                onChanged: (v) => setState(() => _goal = v ?? 'study'),
              ),
              const SizedBox(height: 16),
              if (state.error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(state.error!,
                      style: const TextStyle(color: Colors.red)),
                ),
              FilledButton(
                onPressed: state.loading
                    ? null
                    : () async {
                        await ref
                            .read(authControllerProvider.notifier)
                            .register(
                              email: _email.text.trim(),
                              password: _password.text,
                              fullName: _name.text,
                              learningGoal: _goal,
                            );
                        if (!context.mounted) return;
                        // A converting guest stays authenticated throughout,
                        // so navigate explicitly rather than relying on the
                        // auth-state redirect (v2 §2.1).
                        final next = ref.read(authControllerProvider);
                        if (next.error == null && next.isAuthenticated) {
                          context.go('/home');
                        }
                      },
                child: state.loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(t.t('register')),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(t.t('have_account')),
                  TextButton(
                    onPressed: () => context.go('/login'),
                    child: Text(t.t('login')),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
