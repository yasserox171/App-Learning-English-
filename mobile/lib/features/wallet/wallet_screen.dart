import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';
import '../../core/i18n/app_localizations.dart';
import 'data/wallet_repository.dart';

/// Coins wallet + premium screen (v2 §2.3 + §7.3 payment page UX).
///
/// One prominent "Subscribe now" action (Google Play on Android), with the
/// remaining methods tucked behind an unobtrusive accordion — no comparison
/// tables, no choice paralysis.
class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(walletProvider);

    return Scaffold(
      appBar: AppBar(title: Text('🪙 ${t.t('wallet')}')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (wallet) => _WalletBody(wallet: wallet),
      ),
    );
  }
}

class _WalletBody extends ConsumerStatefulWidget {
  const _WalletBody({required this.wallet});

  final Wallet wallet;

  @override
  ConsumerState<_WalletBody> createState() => _WalletBodyState();
}

class _WalletBodyState extends ConsumerState<_WalletBody> {
  late Wallet _wallet = widget.wallet;
  bool _busy = false;

  String _tierLabel(AppLocalizations t, RedemptionTier tier) {
    switch (tier.days) {
      case 3:
        return t.t('premium_days_3');
      case 7:
        return t.t('premium_days_7');
      case 30:
        return t.t('premium_days_30');
      default:
        return '${tier.days}d premium';
    }
  }

  Future<void> _redeem(RedemptionTier tier) async {
    setState(() => _busy = true);
    final t = AppLocalizations.of(context);
    try {
      final updated =
          await ref.read(walletRepositoryProvider).redeem(tier.key);
      setState(() => _wallet = updated);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(t.t('redeem_success'))),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('❌')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openWhatsApp() async {
    final number = AppConfig.whatsappNumber;
    if (number.isEmpty) return;
    final uri = Uri.parse(
        'https://wa.me/$number?text=${Uri.encodeComponent("أرغب في الاشتراك المميز")}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final wallet = _wallet;
    final progress =
        (wallet.earnedToday / wallet.dailyCap).clamp(0.0, 1.0).toDouble();

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // Balance card
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [scheme.primary, scheme.primary.withOpacity(0.75)],
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(t.t('coins_balance'),
                  style: const TextStyle(color: Colors.white70)),
              Text('🪙 ${wallet.balance}',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 36,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 8,
                  backgroundColor: Colors.white24,
                  valueColor:
                      const AlwaysStoppedAnimation<Color>(Colors.amber),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                wallet.capReached
                    ? t.t('daily_cap_reached')
                    : '${t.t('earned_today')}: ${wallet.earnedToday}/${wallet.dailyCap}',
                style: const TextStyle(color: Colors.white, fontSize: 13),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        if (wallet.premiumActive && wallet.premiumUntil != null)
          Card(
            color: Colors.green.withOpacity(0.12),
            child: ListTile(
              leading: const Icon(Icons.workspace_premium,
                  color: Colors.green, size: 32),
              title: Text(t.t('premium_active_until')),
              subtitle: Text(
                  '${wallet.premiumUntil!.toLocal()}'.split('.').first),
            ),
          ),
        const SizedBox(height: 8),

        // Redemption tiers (manual tap — §2.3)
        Text(t.t('redeem'),
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        for (final tier in wallet.tiers)
          Card(
            child: ListTile(
              leading: const Text('🎁', style: TextStyle(fontSize: 28)),
              title: Text(_tierLabel(t, tier)),
              subtitle: Text('${tier.coins} ${t.t('coins_short')}'),
              trailing: FilledButton(
                onPressed: (_busy || wallet.balance < tier.coins)
                    ? null
                    : () => _redeem(tier),
                child: Text(t.t('redeem')),
              ),
            ),
          ),

        const SizedBox(height: 24),

        // §7.3: one prominent subscribe button…
        Text(t.t('premium_title'),
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        FilledButton.icon(
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            textStyle:
                const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          icon: const Icon(Icons.play_arrow_rounded),
          onPressed: () {
            // Google Play Billing goes live once the Play Console products
            // exist; purchases are then verified server-side
            // (POST /billing/google/verify) before any premium activates.
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(t.t('play_billing_unavailable'))),
            );
          },
          label: Text(t.t('subscribe_now')),
        ),
        const SizedBox(height: 6),
        Center(
          child: Text('${t.t('monthly_plan')} · ${t.t('annual_plan')}',
              style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant)),
        ),

        // …and the rest behind a small accordion (§7.3).
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Text(t.t('other_payment_methods'),
              style: const TextStyle(fontSize: 14)),
          children: [
            ListTile(
              leading: const Icon(Icons.chat, color: Colors.green),
              title: Text(t.t('whatsapp_payment'),
                  style: const TextStyle(fontSize: 14)),
              onTap: _openWhatsApp,
            ),
          ],
        ),
      ],
    );
  }
}
