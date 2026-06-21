class Level {
  Level({
    required this.id,
    required this.code,
    required this.name,
    required this.nameFr,
    required this.isFree,
  });

  final String id;
  final String code;
  final String name;
  final String nameFr;
  final bool isFree;

  factory Level.fromJson(Map<String, dynamic> j) => Level(
        id: j['id'],
        code: j['code'],
        name: j['name'],
        nameFr: j['name_fr'] ?? '',
        isFree: j['is_free'] ?? false,
      );
}

class Unit {
  Unit({required this.id, required this.title, required this.description});

  final String id;
  final String title;
  final String description;

  factory Unit.fromJson(Map<String, dynamic> j) =>
      Unit(id: j['id'], title: j['title'], description: j['description'] ?? '');
}

class LessonSummary {
  LessonSummary({required this.id, required this.title, required this.description});

  final String id;
  final String title;
  final String description;

  factory LessonSummary.fromJson(Map<String, dynamic> j) => LessonSummary(
        id: j['id'],
        title: j['title'],
        description: j['description'] ?? '',
      );
}

class LessonComponent {
  LessonComponent({
    required this.id,
    required this.type,
    required this.order,
    required this.payload,
  });

  final String id;
  final String type; // video | vocabulary | text | exercise
  final int order;
  final dynamic payload;

  factory LessonComponent.fromJson(Map<String, dynamic> j) => LessonComponent(
        id: j['id'],
        type: j['type'],
        order: j['order'],
        payload: j['payload'],
      );
}

class LessonDetail {
  LessonDetail({required this.id, required this.title, required this.components});

  final String id;
  final String title;
  final List<LessonComponent> components;

  factory LessonDetail.fromJson(Map<String, dynamic> j) => LessonDetail(
        id: j['id'],
        title: j['title'],
        components: (j['components'] as List)
            .map((c) => LessonComponent.fromJson(c as Map<String, dynamic>))
            .toList(),
      );
}

class ExerciseItem {
  ExerciseItem({
    required this.id,
    required this.templateCode,
    required this.content,
    required this.points,
  });

  final String id;
  final String templateCode;
  final Map<String, dynamic> content;
  final int points;

  factory ExerciseItem.fromJson(Map<String, dynamic> j) => ExerciseItem(
        id: j['id'],
        templateCode: j['template_code'],
        content: Map<String, dynamic>.from(j['content'] as Map),
        points: j['points'] ?? 1,
      );
}
