import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/widgets/app_logo.dart';
import 'auth_controller.dart';
import 'google_signin_service.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _remember = true;
  bool _obscure = true;

  void _comingSoon(String label) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('$label — soon')));
  }

  Future<void> _googleSignIn() async {
    final t = AppLocalizations.of(context);
    try {
      final idToken =
          await ref.read(googleSignInServiceProvider).signIn();
      if (idToken == null) return; // cancelled
      await ref
          .read(authControllerProvider.notifier)
          .signInWithGoogleToken(idToken);
      if (!mounted) return;
      // Guests converting via Google stay authenticated the whole time, so
      // the auth redirect won't fire — navigate explicitly.
      final next = ref.read(authControllerProvider);
      if (next.error == null && next.isAuthenticated) context.go('/home');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(t.t('google_not_configured'))),
      );
    }
  }

  Future<void> _continueAsGuest() async {
    final ok =
        await ref.read(authControllerProvider.notifier).ensureSession();
    if (ok && mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final state = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            onPressed: () => ref.read(localeProvider.notifier).toggle(),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Center(child: AppLogo(size: 84)),
              const SizedBox(height: 20),
              Text('${t.t('welcome')} 👋',
                  textAlign: TextAlign.center,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 24),
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
              Row(
                children: [
                  Checkbox(
                    value: _remember,
                    onChanged: (v) => setState(() => _remember = v ?? true),
                  ),
                  Text(t.t('remember_me')),
                  const Spacer(),
                  TextButton(
                    onPressed: () => _comingSoon(t.t('forgot_password')),
                    child: Text(t.t('forgot_password')),
                  ),
                ],
              ),
              if (state.error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(state.error!,
                      style: const TextStyle(color: Colors.red)),
                ),
              FilledButton(
                onPressed: state.loading
                    ? null
                    : () => ref
                        .read(authControllerProvider.notifier)
                        .login(_email.text.trim(), _password.text),
                child: state.loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(t.t('login')),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Expanded(child: Divider()),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text(t.t('or_text')),
                  ),
                  const Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _googleSignIn,
                icon: const Icon(Icons.g_mobiledata, size: 28),
                label: Text(t.t('sign_in_google')),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => _comingSoon(t.t('sign_in_apple')),
                icon: const Icon(Icons.apple),
                label: Text(t.t('sign_in_apple')),
              ),
              const SizedBox(height: 10),
              // v2 §2.1: no forced signup — guests get full free access.
              TextButton.icon(
                onPressed: _continueAsGuest,
                icon: const Icon(Icons.person_outline),
                label: Text(t.t('continue_guest')),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(t.t('no_account')),
                  TextButton(
                    onPressed: () => context.go('/register'),
                    child: Text(t.t('create_account')),
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
