import 'package:flutter/material.dart';

import 'api_client.dart';

class DetectionScreen extends StatefulWidget {
  const DetectionScreen({super.key});

  @override
  State<DetectionScreen> createState() => _DetectionScreenState();
}

class _DetectionScreenState extends State<DetectionScreen> {

  String result = "Press Start Detection";
  bool isLoading = false;

  Future<void> detectRansomware() async {

    setState(() {
      isLoading = true;
      result = "Detecting...";
    });

    try {
      final data = await ApiClient.getJson('/scan');
      final detected = (data['ransomware_detected'] == true);
      final scannedFiles = data['scanned_files'];
      final durationMs = data['duration_ms'];
      final suspiciousList = data['suspicious_files'] as List? ?? [];
      final suspicious = suspiciousList.length;
      final scannedPaths = (data['scanned_paths'] as List?)?.join('\n') ?? 'N/A';

      String suspiciousDetails = '';
      if (suspicious > 0) {
        // Show file paths or names if there are any suspicious files
        suspiciousDetails = '\n\nSuspicious Files:\n' + 
            suspiciousList.map((f) => '- ${f['path']}').join('\n');
      }

      setState(() {
        result = detected
            ? "🚨 DANGER: RANSOMWARE ACTIVITY DETECTED!\n\nScanned: $scannedFiles files\nSuspicious: $suspicious$suspiciousDetails\n\nTime: ${durationMs}ms\n\nFolders Scanned:\n$scannedPaths"
            : "✅ System Safe\n\nScanned: $scannedFiles files\nTime: ${durationMs}ms\n\nFolders Scanned:\n$scannedPaths";
      });

    } catch (e) {

      setState(() {
        result = "Connection Failed\nTip: Settings > Backend URL";
      });

    }

    setState(() {
      isLoading = false;
    });

  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text("Ransomware Detection"),
        centerTitle: true,
      ),

      body: Center(

        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(20),
  
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
  
                const Icon(
                  Icons.radar_rounded,
                  size: 140,
                  color: Color(0xFF00796B),
                ),
  
                const SizedBox(height: 30),
  
                Text(
                  result,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
  
                const SizedBox(height: 40),
  
                isLoading
                    ? const CircularProgressIndicator()
                    : ElevatedButton(
                  onPressed: detectRansomware,
                  child: const Text("Start Detection"),
                ),
  
              ],
            ),
          ),
        ),

      ),
    );
  }
}