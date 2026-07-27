import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class RedemptionTier {
  RedemptionTier({required this.key, required this.coins, required this.days});

  final String key;
  final int coins;
  final int days;

  factory RedemptionTier.fromJson(Map<String, dynamic> j) => RedemptionTier(
        key: j['key'] ?? '',
        coins: j['coins'] ?? 0,
        days: j['days'] ?? 0,
      );
}

class Wallet {
  Wallet({
    required this.balance,
    required this.earnedToday,
    required this.dailyCap,
    required this.capReached,
    required this.tiers,
    required this.premiumActive,
    this.premiumUntil,
  });

  final int balance;
  final int earnedToday;
  final int dailyCap;
  final bool capReached;
  final List<RedemptionTier> tiers;
  final bool premiumActive;
  final DateTime? premiumUntil;

  factory Wallet.fromJson(Map<String, dynamic> j) => Wallet(
        balance: j['balance'] ?? 0,
        earnedToday: j['earned_today'] ?? 0,
        dailyCap: j['daily_cap'] ?? 60,
        capReached: j['cap_reached'] == true,
        tiers: [
          for (final t in (j['redemption_tiers'] as List? ?? const []))
            RedemptionTier.fromJson(t as Map<String, dynamic>),
        ],
        premiumActive: j['premium_active'] == true,
        premiumUntil: j['premium_until'] != null
            ? DateTime.tryParse(j['premium_until'] as String)
            : null,
      );
}

class WalletRepository {
  WalletRepository(this._dio);

  final Dio _dio;

  Future<Wallet> wallet() async {
    final res = await _dio.get('/billing/wallet');
    return Wallet.fromJson(res.data as Map<String, dynamic>);
  }

  /// Manual redemption (v2 §2.3) — the user taps, it never auto-triggers.
  Future<Wallet> redeem(String tierKey) async {
    final res = await _dio.post('/billing/redeem', data: {'tier': tierKey});
    return Wallet.fromJson(
        (res.data as Map<String, dynamic>)['wallet'] as Map<String, dynamic>);
  }
}

final walletRepositoryProvider = Provider<WalletRepository>(
  (ref) => WalletRepository(ref.read(dioProvider)),
);

final walletProvider = FutureProvider<Wallet>(
  (ref) => ref.read(walletRepositoryProvider).wallet(),
);
