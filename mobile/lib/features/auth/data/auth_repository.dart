import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import 'user.dart';

class AuthRepository {
  AuthRepository(this._dio, this._ref);

  final Dio _dio;
  final Ref _ref;

  Future<AppUser> _persistAndParse(Map<String, dynamic> data) async {
    await _ref.read(tokenStorageProvider).save(
          access: data['access'] as String,
          refresh: data['refresh'] as String,
        );
    return AppUser.fromJson(data['user'] as Map<String, dynamic>);
  }

  Future<AppUser> login(String email, String password) async {
    final res = await _dio.post('/auth/login',
        data: {'email': email, 'password': password});
    return _persistAndParse(res.data as Map<String, dynamic>);
  }

  Future<AppUser> register({
    required String email,
    required String password,
    required String fullName,
    String? nativeLanguage,
    String? learningGoal,
    String appLanguage = 'ar',
  }) async {
    final res = await _dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      'full_name': fullName,
      if (nativeLanguage != null) 'native_language': nativeLanguage,
      if (learningGoal != null) 'learning_goal': learningGoal,
      'app_language': appLanguage,
    });
    return _persistAndParse(res.data as Map<String, dynamic>);
  }

  /// v2 §2.1: automatic guest account — no user input, same JWT mechanism.
  Future<AppUser> guest({String? country}) async {
    final res = await _dio.post('/auth/guest', data: {
      if (country != null && country.isNotEmpty) 'country': country,
    });
    return _persistAndParse(res.data as Map<String, dynamic>);
  }

  /// v2 §6.1: Google ID token → server-side verification. When the caller is
  /// a guest (token already attached by the interceptor), the backend
  /// converts the same row in place.
  Future<AppUser> googleLogin(String idToken) async {
    final res =
        await _dio.post('/auth/social/google', data: {'id_token': idToken});
    return _persistAndParse(res.data as Map<String, dynamic>);
  }

  Future<AppUser> me() async {
    final res = await _dio.get('/auth/me');
    return AppUser.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> logout() => _ref.read(tokenStorageProvider).clear();
}

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.read(dioProvider), ref),
);
