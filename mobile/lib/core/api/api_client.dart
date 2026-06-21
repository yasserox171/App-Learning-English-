import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

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
        // Try a one-time refresh on 401.
        if (error.response?.statusCode == 401) {
          final refresh = await storage.refresh;
          if (refresh != null) {
            try {
              final res = await Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl))
                  .post('/auth/refresh', data: {'refresh': refresh});
              final newAccess = res.data['access'] as String;
              await storage.save(access: newAccess, refresh: refresh);
              final req = error.requestOptions;
              req.headers['Authorization'] = 'Bearer $newAccess';
              final clone = await dio.fetch(req);
              return handler.resolve(clone);
            } catch (_) {
              await storage.clear();
            }
          }
        }
        handler.next(error);
      },
    ),
  );

  return dio;
});
