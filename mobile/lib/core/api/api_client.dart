import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../features/auth/auth_controller.dart';
import '../config.dart';
import 'token_storage.dart';

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => TokenStorage(const FlutterSecureStorage()),
);

/// Configured Dio instance with a JWT auth interceptor and refresh-on-401.
final dioProvider = Provider<Dio>((ref) {
  final storage = ref.read(tokenStorageProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storage.access;
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final req = error.requestOptions;
        final alreadyRetried = req.extra['retried'] == true;

        // Try a one-time refresh on 401 (guarded against infinite loops).
        if (error.response?.statusCode == 401 && !alreadyRetried) {
          final refresh = await storage.refresh;
          if (refresh != null) {
            try {
              final res = await Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl))
                  .post('/auth/refresh', data: {'refresh': refresh});
              final newAccess = res.data['access'] as String;
              await storage.save(access: newAccess, refresh: refresh);
              req.headers['Authorization'] = 'Bearer $newAccess';
              req.extra['retried'] = true; // prevents re-refresh loop
              final clone = await dio.fetch(req);
              return handler.resolve(clone);
            } catch (_) {
              // Refresh failed: session is dead -> sign out, back to login.
              await _signOut(ref);
            }
          } else {
            await _signOut(ref);
          }
        } else if (error.response?.statusCode == 401 && alreadyRetried) {
          await _signOut(ref);
        }
        handler.next(error);
      },
    ),
  );

  return dio;
});

/// Clears the session so the router redirects to the login screen.
Future<void> _signOut(Ref ref) async {
  try {
    await ref.read(authControllerProvider.notifier).logout();
  } catch (_) {
    await ref.read(tokenStorageProvider).clear();
  }
}
