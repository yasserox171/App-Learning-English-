/// App-wide configuration.
class AppConfig {
  /// Base URL of the backend API. Override with --dart-define=API_BASE_URL=...
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  /// Where friends can download the app (used in share messages).
  static const String downloadUrl =
      'https://github.com/yasserox171/App-Learning-English-/releases/tag/latest-apk';
}
