/// App-wide configuration.
class AppConfig {
  /// Base URL of the backend API. Override with --dart-define=API_BASE_URL=...
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://84.8.223.62:8000/api/v1',
  );

  /// Where friends can download the app (used in share messages).
  static const String downloadUrl =
      'https://github.com/yasserox171/App-Learning-English-/releases/tag/latest-apk';

  /// Web OAuth client ID for Google Sign-In (v2 §6.1). Android needs the WEB
  /// client id as serverClientId to obtain an idToken the backend can verify.
  /// Override with --dart-define=GOOGLE_WEB_CLIENT_ID=...
  static const String googleWebClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
    defaultValue: '',
  );

  /// WhatsApp number for manual premium activation (v2 §7.2, ~24h delay).
  /// Override with --dart-define=WHATSAPP_NUMBER=2126XXXXXXXX
  static const String whatsappNumber = String.fromEnvironment(
    'WHATSAPP_NUMBER',
    defaultValue: '',
  );
}
