import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import 'data/auth_repository.dart';
import 'data/user.dart';

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
      state = AuthState(error: 'Login failed', loading: false);
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
      state = AuthState(error: 'Registration failed', loading: false);
    }
  }

  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) => AuthController(ref));
