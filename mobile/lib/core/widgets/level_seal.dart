import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// A certificate-style guilloche seal: a lace of thin rotated ellipses around
/// the level code, framed by a light diamond outline (ABA-inspired). Drawn
/// procedurally — no image assets needed.
class LevelSeal extends StatelessWidget {
  const LevelSeal({
    super.key,
    required this.code,
    this.size = 96,
    this.color,
  });

  final String code;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size.square(size),
            painter: _SealPainter(
              lace: color ?? AppTheme.success,
              frame: scheme.onSurfaceVariant.withOpacity(0.35),
              center: scheme.surface,
            ),
          ),
          Text(
            code,
            style: TextStyle(
              fontSize: size * 0.2,
              fontWeight: FontWeight.w800,
              color: scheme.onSurface,
            ),
          ),
        ],
      ),
    );
  }
}

class _SealPainter extends CustomPainter {
  _SealPainter({required this.lace, required this.frame, required this.center});

  final Color lace;
  final Color frame;
  final Color center;

  @override
  void paint(Canvas canvas, Size size) {
    final mid = size.center(Offset.zero);
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = lace.withOpacity(0.75);

    const petals = 12;
    final rx = size.width * 0.46;
    final ry = size.width * 0.18;
    for (var i = 0; i < petals; i++) {
      canvas.save();
      canvas.translate(mid.dx, mid.dy);
      canvas.rotate(i * math.pi / petals);
      canvas.drawOval(
        Rect.fromCenter(center: Offset.zero, width: rx * 2, height: ry * 2),
        stroke,
      );
      canvas.restore();
    }

    // Light diamond frame whose corners poke out past the lace.
    final d = size.width * 0.5 - 0.5;
    final diamond = Path()
      ..moveTo(mid.dx, mid.dy - d)
      ..lineTo(mid.dx + d, mid.dy)
      ..lineTo(mid.dx, mid.dy + d)
      ..lineTo(mid.dx - d, mid.dy)
      ..close();
    canvas.drawPath(
      diamond,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = frame,
    );

    // Clear circle behind the code so it stays readable over the lace.
    canvas.drawCircle(mid, size.width * 0.17, Paint()..color = center);
  }

  @override
  bool shouldRepaint(_SealPainter old) =>
      old.lace != lace || old.frame != frame || old.center != center;
}
