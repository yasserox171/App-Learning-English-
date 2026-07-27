import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../core/config.dart';

/// Google Sign-In (v2 §6.1). The ID token is verified server-side — the app
/// never asserts an identity itself. `serverClientId` must be the WEB OAuth
/// client ID (Google's requirement for getting an idToken on Android).
class GoogleSignInService {
  GoogleSignIn? _google;

  bool get configured => AppConfig.googleWebClientId.isNotEmpty;

  /// Returns the Google ID token, or null if the user cancelled.
  Future<String?> signIn() async {
    if (!configured) {
      throw StateError('google-not-configured');
    }
    _google ??= GoogleSignIn(
      serverClientId: AppConfig.googleWebClientId,
      scopes: const ['email'],
    );
    final account = await _google!.signIn();
    if (account == null) return null; // user cancelled
    final auth = await account.authentication;
    return auth.idToken;
  }

  Future<void> signOut() async => _google?.signOut();
}

final googleSignInServiceProvider =
    Provider<GoogleSignInService>((ref) => GoogleSignInService());
