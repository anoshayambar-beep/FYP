import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:io';

// Screens
import 'splash_screen.dart';
import 'login_screen.dart';
import 'dashboard_screen.dart';
import 'detection_screen.dart';
import 'alerts_screen.dart';
import 'reports_screen.dart';
import 'blockchain_screen.dart';
import 'settings_screen.dart';
import 'register_screen.dart';

import 'services/notification_service.dart';
import 'services/auth_service.dart';
import 'api_client.dart';

import 'package:workmanager/workmanager.dart';

final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    try {
      // Initialize notification service in background process
      await NotificationService.init();
      
      final token = await AuthService.getToken();
      if (token == null) return true;

      // Fetch alerts from API
      final data = await ApiClient.getJson('/alerts');
      final List alerts = data['alerts'] ?? [];
      
      if (alerts.isNotEmpty) {
        final lastAlert = alerts.first;
        final alertTime = DateTime.parse(lastAlert['time_utc']);
        final now = DateTime.now().toUtc();
        
        // If alert happened in last 15 mins (matching check interval), show it
        if (now.difference(alertTime).inMinutes < 16) {
           await NotificationService.showNotification(
            "SECURITY BREACH!",
            lastAlert['message'] ?? "Suspicious activity detected!",
          );
        }
      }
    } catch (e) {
      // In background, we can't print easily, but we catch to avoid crash
    }
    return Future.value(true);
  });
}


void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.init();
  
  // Request permissions for Android 13+
  await NotificationService.requestPermission();
  
  if (Platform.isAndroid) {
    try {
      await Workmanager().initialize(callbackDispatcher, isInDebugMode: false);
      Workmanager().registerPeriodicTask(
        "1", 
        "fetchAlertsTask",
        frequency: const Duration(minutes: 15),
        constraints: Constraints(networkType: NetworkType.connected),
      );
    } catch (e) {
      debugPrint("Workmanager not supported on this platform");
    }
  }

  _startPersistentMonitoring();
  runApp(const RansomwareApp());
}

int _lastAlertCount = -1;

void _startPersistentMonitoring() {
  // Frequent check (Every 5 seconds) when app is in FOREGROUND
  Timer.periodic(const Duration(seconds: 5), (timer) async {
    _performCheck();
  });
}

Future<void> _performCheck() async {
  try {
    final token = await AuthService.getToken();
    if (token == null) return;

    final data = await ApiClient.getJson('/alerts');
    final List alerts = data['alerts'] ?? [];
    
    if (_lastAlertCount == -1) {
      _lastAlertCount = alerts.length;
      return;
    }

    if (alerts.length > _lastAlertCount) {
      final newAlert = alerts.first;
      
      // System notification (Heads-up)
      await NotificationService.showNotification(
        "🚨 SECURITY BREACH!",
        newAlert['message'] ?? "Suspicious activity detected!",
      );
      
      _showSecurityAlert(newAlert['message'] ?? "Suspicious activity detected!");
      _lastAlertCount = alerts.length;
    }
  } catch (e) { }
}

void _showSecurityAlert(String message) {
  scaffoldMessengerKey.currentState?.showSnackBar(
    SnackBar(
      content: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 28),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "SECURITY BREACH!",
                  style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF09FBD3)),
                ),
                Text(message, style: const TextStyle(color: Colors.white70)),
              ],
            ),
          ),
        ],
      ),
      backgroundColor: const Color(0xFF1D1E33),
      duration: const Duration(seconds: 10),
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.all(20),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(15),
        side: const BorderSide(color: Color(0xFF09FBD3), width: 1),
      ),
    ),
  );
}

class RansomwareApp extends StatelessWidget {
  const RansomwareApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      scaffoldMessengerKey: scaffoldMessengerKey,
      debugShowCheckedModeBanner: false,
      title: 'Ransomware Detection System',

      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF5F5F5),
        primaryColor: const Color(0xFF00796B),
        
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00796B),
          primary: const Color(0xFF00796B),
          secondary: const Color(0xFF004D40),
          surface: Colors.white,
        ),

        appBarTheme: const AppBarTheme(
          centerTitle: true,
          backgroundColor: Color(0xFF00796B),
          elevation: 4,
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
          iconTheme: IconThemeData(color: Colors.white),
        ),

        cardTheme: CardThemeData(
          color: Colors.white,
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),

        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFF00796B), width: 2),
          ),
        ),

        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF00796B),
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
        ),
      ),

      // 🔹 App start yahan se hoga
      home: const SplashScreen(),

      // 🔹 Proper named routes (COMSATS FYP style)
      routes: {
        '/login': (context) => const LoginScreen(),
        '/dashboard': (context) => const DashboardScreen(),
        '/detection': (context) => const DetectionScreen(),
        '/alerts': (context) => const AlertsScreen(),
        '/reports': (context) => const ReportsScreen(),
        '/blockchain': (context) => const BlockchainScreen(),
        '/settings': (context) => const SettingsScreen(),
        '/register': (context) => const RegisterScreen(),
      },
    );
  }
}
