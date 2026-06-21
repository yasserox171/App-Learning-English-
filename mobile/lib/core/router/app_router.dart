import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/auth_controller.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/content/lesson_detail_screen.dart';
import '../../features/content/lessons_screen.dart';
import '../../features/content/levels_screen.dart';
import '../../features/content/units_screen.dart';
import '../../features/placement/placement_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/progress/progress_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/levels',
    redirect: (context, state) {
      final authed = ref.read(authControllerProvider).isAuthenticated;
      final loggingIn =
          state.matchedLocation == '/login' || state.matchedLocation == '/register';
      if (!authed && !loggingIn) return '/login';
      if (authed && loggingIn) return '/levels';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      GoRoute(path: '/placement', builder: (_, __) => const PlacementScreen()),
      GoRoute(path: '/levels', builder: (_, __) => const LevelsScreen()),
      GoRoute(
        path: '/levels/:id/units',
        builder: (_, s) => UnitsScreen(levelId: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/units/:id/lessons',
        builder: (_, s) => LessonsScreen(unitId: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/lessons/:id',
        builder: (_, s) => LessonDetailScreen(lessonId: s.pathParameters['id']!),
      ),
      GoRoute(path: '/progress', builder: (_, __) => const ProgressScreen()),
      GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
    ],
  );
});
