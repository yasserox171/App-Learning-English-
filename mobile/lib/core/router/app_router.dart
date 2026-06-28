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
import '../../features/home/home_dashboard_screen.dart';
import '../../features/onboarding/language_screen.dart';
import '../../features/onboarding/splash_screen.dart';
import '../../features/placement/placement_intro_screen.dart';
import '../../features/placement/placement_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/profile/settings_screen.dart';
import '../../features/progress/certificates_screen.dart';
import '../../features/progress/progress_screen.dart';
import '../widgets/home_shell.dart';

final _rootKey = GlobalKey<NavigatorState>();

// Routes reachable without being signed in.
const _publicRoutes = {'/', '/language', '/login', '/register'};

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
    initialLocation: '/',
    refreshListenable: authChanged,
    redirect: (context, state) {
      final authed = ref.read(authControllerProvider).isAuthenticated;
      final loc = state.matchedLocation;
      final isPublic = _publicRoutes.contains(loc);
      // Let the splash/language flow decide on its own.
      if (loc == '/' || loc == '/language') return null;
      if (!authed && !isPublic) return '/login';
      if (authed && (loc == '/login' || loc == '/register')) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/language', builder: (_, __) => const LanguageScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),

      // Bottom-nav tabs (each branch keeps its own navigation state).
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomeShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/home', builder: (_, __) => const HomeDashboardScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/learn', builder: (_, __) => const LevelsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          ]),
        ],
      ),

      // Drill-down + secondary routes pushed onto the root navigator (full
      // screen, above the bottom bar; phone back works).
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
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/placement-intro',
        builder: (_, __) => const PlacementIntroScreen(),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/placement',
        builder: (_, __) => const PlacementScreen(),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/progress',
        builder: (_, __) => const ProgressScreen(),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/certificates',
        builder: (_, __) => const CertificatesScreen(),
      ),
      GoRoute(
        parentNavigatorKey: _rootKey,
        path: '/settings',
        builder: (_, __) => const SettingsScreen(),
      ),
    ],
  );
});
