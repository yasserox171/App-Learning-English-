import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import 'data/auth_repository.dart';
import 'data/user.dart';

String _describeError(Object e, String fallback) {
  if (e is DioException) {
    if (e.response != null) {
      final data = e.response!.data;
      if (data is Map && data['error'] != null) {
        return '$fallback: ${data['error']['detail']}';
      }
      return '$fallback (HTTP ${e.response!.statusCode})';
    }
    // No response = could not reach the server.
    return 'Cannot reach server. Check the backend URL and your connection.';
  }
  return fallback;
}

class AuthState {
  const AuthState({this.user, this.loading = false, this.error});

  final AppUser? user;
  final bool loading;
  final String? error;

  bool get isAuthenticated => user != null;

  AuthState copyWith({AppUser? user, bool? loading, String? error}) => AuthState(
        user: user ?? this.user,
        loading: loading ?? this.loading,
        error: error,
      );
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref) : super(const AuthState());

  final Ref _ref;

  AuthRepository get _repo => _ref.read(authRepositoryProvider);

  /// Called at startup: if a token exists, load the profile.
  Future<void> bootstrap() async {
    final token = await _ref.read(tokenStorageProvider).access;
    if (token == null) return;
    try {
      final user = await _repo.me();
      state = state.copyWith(user: user);
    } catch (_) {
      await _repo.logout();
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final user = await _repo.login(email, password);
      state = AuthState(user: user);
    } catch (e) {
      state = AuthState(error: _describeError(e, 'Login failed'), loading: false);
    }
  }

  Future<void> register({
    required String email,
    required String password,
    required String fullName,
    String? learningGoal,
  }) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final user = await _repo.register(
        email: email,
        password: password,
        fullName: fullName,
        learningGoal: learningGoal,
      );
      state = AuthState(user: user);
    } catch (e) {
      state = AuthState(error: _describeError(e, 'Registration failed'), loading: false);
    }
  }

  /// v2 §2.1: silent guest bootstrap on first open — no user input required.
  /// Returns true when a session (existing or fresh guest) is available.
  Future<bool> ensureSession({String? country}) async {
    if (state.isAuthenticated) return true;
    final token = await _ref.read(tokenStorageProvider).access;
    if (token != null) {
      try {
        final user = await _repo.me();
        state = state.copyWith(user: user);
        return true;
      } catch (_) {
        await _repo.logout();
      }
    }
    try {
      final user = await _repo.guest(country: country);
      state = AuthState(user: user);
      return true;
    } catch (_) {
      return false; // offline / server unreachable → fall back to login
    }
  }

  Future<void> signInWithGoogleToken(String idToken) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final user = await _repo.googleLogin(idToken);
      state = AuthState(user: user);
    } catch (e) {
      state = AuthState(
        user: state.user,
        error: _describeError(e, 'Google sign-in failed'),
      );
    }
  }

  /// Refresh the profile (e.g. after premium activation or conversion).
  Future<void> refreshProfile() async {
    try {
      final user = await _repo.me();
      state = state.copyWith(user: user);
    } catch (_) {}
  }

  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) => AuthController(ref));
