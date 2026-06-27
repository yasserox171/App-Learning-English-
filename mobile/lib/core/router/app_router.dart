import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/auth_controller.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/content/lesson_player_screen.dart';
import '../../features/content/lessons_screen.dart';
import '../../features/content/levels_screen.dart';
import '../../features/content/units_screen.dart';
import '../../features/placement/placement_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/progress/progress_screen.dart';
import '../widgets/home_shell.dart';

final _rootKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  // Re-evaluate redirects when auth state changes (e.g. after login).
  final authChanged = ValueNotifier<bool>(
    ref.read(authControllerProvider).isAuthenticated,
  );
  ref.listen(authControllerProvider, (prev, next) {
    authChanged.value = next.isAuthenticated;
  });
  ref.onDispose(authChanged.dispose);

  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/home',
    refreshListenable: authChanged,
    redirect: (context, state) {
      final authed = ref.read(authControllerProvider).isAuthenticated;
      final loc = state.matchedLocation;
      final loggingIn = loc == '/login' || loc == '/register';
      if (!authed && !loggingIn) return '/login';
      if (authed && loggingIn) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      GoRoute(path: '/placement', builder: (_, __) => const PlacementScreen()),

      // Bottom-nav tabs (each branch keeps its own navigation state).
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomeShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/home', builder: (_, __) => const LevelsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/progress', builder: (_, __) => const ProgressScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          ]),
        ],
      ),

      // Drill-down routes: pushed onto the root navigator -> back arrow +
      // phone back works (full-screen, above the bottom bar).
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/levels/:id/units',
        builder: (_, s) => UnitsScreen(levelId: s.pathParameters['id']!),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/units/:id/lessons',
        builder: (_, s) => LessonsScreen(unitId: s.pathParameters['id']!),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/lessons/:id',
        builder: (_, s) => LessonPlayerScreen(lessonId: s.pathParameters['id']!),
      ),
    ],
  );
});
