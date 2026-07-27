class AppUser {
  AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.appLanguage = 'ar',
    this.learningGoal,
    this.isGuest = false,
    this.country = '',
  });

  final String id;
  final String email;
  final String fullName;
  final String role;
  final String appLanguage;
  final String? learningGoal;
  // v2 §2.1: guest accounts are real users; registration converts in place.
  final bool isGuest;
  final String country;

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as String,
        email: json['email'] as String,
        fullName: (json['full_name'] ?? '') as String,
        role: json['role'] as String,
        appLanguage: (json['app_language'] ?? 'ar') as String,
        learningGoal: json['learning_goal'] as String?,
        isGuest: json['is_guest'] == true,
        country: (json['country'] ?? '') as String,
      );
}
