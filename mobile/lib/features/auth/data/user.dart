class AppUser {
  AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.appLanguage = 'ar',
    this.learningGoal,
  });

  final String id;
  final String email;
  final String fullName;
  final String role;
  final String appLanguage;
  final String? learningGoal;

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as String,
        email: json['email'] as String,
        fullName: (json['full_name'] ?? '') as String,
        role: json['role'] as String,
        appLanguage: (json['app_language'] ?? 'ar') as String,
        learningGoal: json['learning_goal'] as String?,
      );
}
