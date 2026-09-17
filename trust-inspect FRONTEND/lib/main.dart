import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';



const String apiBaseUrl = 'http://10.156.239.241:8000';
String? accessToken;

// Shared in-memory list of alert members.
// Starts empty on purpose (per project requirement).
final List<Map<String, String>> alertMembers = [];

void main() {
  runApp(const TrustInspectApp());
}

class TrustInspectApp extends StatelessWidget {
  const TrustInspectApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TRUST INSPECT',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        useMaterial3: true,
      ),
      home: const LoginPage(),
    );
  }
}

// ---------------------------------------------------------------------------
// LOGIN PAGE (local demo login only — NOT connected to backend)
// ---------------------------------------------------------------------------
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController usernameController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();

  @override
  void dispose() {
    usernameController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> login() async {
  final username = usernameController.text.trim();
  final password = passwordController.text;

  if (username.isEmpty || password.isEmpty) {
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(
      content: Text('Please enter username and password'),
    ),
  );
  return;
}

  try {
  final response = await http.post(
    Uri.parse('$apiBaseUrl/auth/login'),
    headers: {
      'Content-Type': 'application/json',
    },
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      accessToken = data['access_token'];

      if (accessToken == null || accessToken.toString().isEmpty) {
        throw Exception('Access token missing');
      }

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => const DashboardPage(),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Invalid username or password'),
        ),
      );
    }
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to connect to backend: $e'),
      ),
    );
  }
}

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.verified_user, size: 72, color: Colors.indigo),
                const SizedBox(height: 12),
                const Text(
                  'TRUST INSPECT',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 32),
                TextField(
                  controller: usernameController,
                  decoration: const InputDecoration(
                    labelText: 'Username',
                    prefixIcon: Icon(Icons.person),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: login,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: const Text('LOGIN'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// DASHBOARD PAGE
// NOTE: stats and inspection cards below are demo placeholder values,
// not live backend data.
// ---------------------------------------------------------------------------
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int currentTab = 0;

  List<Map<String, dynamic>> projects = [];
  int alertCount = 0;
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    loadDashboardData();
  }

  Future<void> loadDashboardData() async {
    if (accessToken == null || accessToken!.isEmpty) {
      setState(() {
        isLoading = false;
        errorMessage = 'Authentication token not available';
      });
      return;
    }

    try {
      final projectsResponse = await http.get(
        Uri.parse('$apiBaseUrl/projects'),
        headers: {
          'Authorization': 'Bearer $accessToken',
        },
      );

      final alertsResponse = await http.get(
        Uri.parse('$apiBaseUrl/alerts'),
        headers: {
          'Authorization': 'Bearer $accessToken',
        },
      );

      if (projectsResponse.statusCode != 200) {
        throw Exception(
          'Projects API failed: ${projectsResponse.statusCode}',
        );
      }

      if (alertsResponse.statusCode != 200) {
        throw Exception(
          'Alerts API failed: ${alertsResponse.statusCode}',
        );
      }

      final projectData =
          List<Map<String, dynamic>>.from(
        jsonDecode(projectsResponse.body),
      );

      final alertData =
          List<dynamic>.from(
        jsonDecode(alertsResponse.body),
      );

      setState(() {
        projects = projectData;
        alertCount = alertData.length;
        isLoading = false;
        errorMessage = null;
      });
    } catch (e) {
      setState(() {
        isLoading = false;
        errorMessage = 'Unable to load dashboard: $e';
      });
    }
  }

  Color levelColor(double riskScore) {
    if (riskScore >= 70) {
      return Colors.red;
    }

    if (riskScore >= 40) {
      return Colors.orange;
    }

    return Colors.green;
  }

  String riskLevel(double riskScore) {
    if (riskScore >= 70) {
      return 'HIGH';
    }

    if (riskScore >= 40) {
      return 'MEDIUM';
    }

    return 'LOW';
  }

  Widget buildStat(String label, String value) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }

  Widget buildHome() {
    if (isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 48,
                color: Colors.red,
              ),
              const SizedBox(height: 12),
              Text(
                errorMessage!,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: loadDashboardData,
                child: const Text('RETRY'),
              ),
            ],
          ),
        ),
      );
    }

    final highRiskCount = projects.where((project) {
      final score = (project['risk_score'] ?? 0).toDouble();
      return score >= 70;
    }).length;

    final averageRisk = projects.isEmpty
        ? 0.0
        : projects.fold<double>(
              0.0,
              (sum, project) =>
                  sum + (project['risk_score'] ?? 0).toDouble(),
            ) /
            projects.length;

    return RefreshIndicator(
      onRefresh: loadDashboardData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Hello, Inspector 👋',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const Text(
            'Here is your inspection overview',
            style: TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 16),

          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Row(
                children: [
                  buildStat(
                    'High Risk',
                    '$highRiskCount',
                  ),
                  buildStat(
                    'Projects',
                    '${projects.length}',
                  ),
                  buildStat(
                    'Alerts',
                    '$alertCount',
                  ),
                  buildStat(
                    'Avg Risk',
                    averageRisk.toStringAsFixed(1),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          const Text(
            'Projects',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          if (projects.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: Center(
                  child: Text('No projects available'),
                ),
              ),
            ),

          ...projects.map((project) {
            final name =
                project['name']?.toString() ?? 'Unnamed Project';

            final district =
                project['district']?.toString() ?? '';

            final riskScore =
                (project['risk_score'] ?? 0).toDouble();

            final level = riskLevel(riskScore);

            return Card(
              child: ListTile(
                title: Text(name),
                subtitle: Text(
                  district.isEmpty
                      ? '$level — ${riskScore.toStringAsFixed(0)}'
                      : '$district • $level — ${riskScore.toStringAsFixed(0)}',
                ),
                leading: CircleAvatar(
                  backgroundColor: levelColor(riskScore),
                  child: Text(
                    riskScore.toStringAsFixed(0),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                    ),
                  ),
                ),
                trailing: TextButton(
                  onPressed: () {
                    Navigator.push(
                    context,
                    MaterialPageRoute(
  builder: (context) => ProjectRiskPage(
    projectId: project['id'] as int,
  ),
),

                    );
                  },
                  child: const Text('VIEW'),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      buildHome(),
      const Center(child: Text('Inspections list — coming soon')),
      const AlertMembersPage(),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('TRUST INSPECT')),
      body: pages[currentTab],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: currentTab,
        onTap: (index) {
          setState(() {
            currentTab = index;
          });
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(
              icon: Icon(Icons.fact_check), label: 'Inspections'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// PROJECT RISK PAGE
// NOTE: project details, risk score, anomalies, and confidence below are
// demo placeholder values, not values computed live from the backend.
// ---------------------------------------------------------------------------
class ProjectRiskPage extends StatefulWidget {
  final int projectId;

  const ProjectRiskPage({
    super.key,
    required this.projectId,
  });

  @override
  State<ProjectRiskPage> createState() => _ProjectRiskPageState();
}

class _ProjectRiskPageState extends State<ProjectRiskPage> {
  final Set<String> selectedAlertMembers = {};
  Map<String, dynamic>? trustData;
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    loadProjectRisk();
  }

  Future<void> loadProjectRisk() async {
    if (accessToken == null || accessToken!.isEmpty) {
      if (!mounted) return;
      setState(() {
        isLoading = false;
        errorMessage = 'Authentication token not available';
      });
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('$apiBaseUrl/projects/${widget.projectId}/trust'),
        headers: {
          'Authorization': 'Bearer $accessToken',
        },
      );

      if (response.statusCode != 200) {
        throw Exception(
          'Trust API failed: ${response.statusCode}',
        );
      }

      final data = jsonDecode(response.body);

      if (!mounted) return;
      setState(() {
        trustData = Map<String, dynamic>.from(data);
        isLoading = false;
        errorMessage = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        isLoading = false;
        errorMessage = 'Unable to load project risk: $e';
      });
    }
  }

  Future<void> analyzeProject() async {
  if (accessToken == null || accessToken!.isEmpty) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Authentication token not available'),
      ),
    );
    return;
  }

  try {
    final response = await http.post(
      Uri.parse('$apiBaseUrl/ai/analyze/${widget.projectId}'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(
        'AI analysis failed: ${response.statusCode}\n${response.body}',
      );
    }

    final data = jsonDecode(response.body);

    if (!mounted) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('AI Risk Analysis'),
        content: SingleChildScrollView(
          child: Text(
            const JsonEncoder.withIndent('  ').convert(data),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to run AI analysis: $e'),
      ),
    );
  }
}

   Future<void> startInspection() async {
  if (accessToken == null || accessToken!.isEmpty) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Authentication token not available'),
      ),
    );
    return;
  }

  try {
    // 1. Check whether phone location is enabled.
    final serviceEnabled =
        await Geolocator.isLocationServiceEnabled();

    if (!serviceEnabled) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please turn on Location/GPS'),
        ),
      );
      return;
    }

    // 2. Check location permission.
    LocationPermission permission =
        await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Location permission is required for inspection',
          ),
        ),
      );
      return;
    }

    // 3. Get the current phone GPS position.
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
      ),
    );

    // 4. Get project data from the backend.
    final projectsResponse = await http.get(
      Uri.parse('$apiBaseUrl/projects'),
      headers: {
        'Authorization': 'Bearer $accessToken',
      },
    );

    if (projectsResponse.statusCode != 200) {
      throw Exception(
        'Unable to load project location: '
        '${projectsResponse.statusCode}',
      );
    }

    final projectList =
        List<Map<String, dynamic>>.from(
      jsonDecode(projectsResponse.body),
    );

    final project = projectList.firstWhere(
      (item) => item['id'] == widget.projectId,
      orElse: () => <String, dynamic>{},
    );

    if (project.isEmpty) {
      throw Exception('Selected project not found');
    }

    final projectLatitude =
        (project['latitude'] as num).toDouble();

    final projectLongitude =
        (project['longitude'] as num).toDouble();

    // 5. Calculate distance between phone and project.
    final distanceMeters = Geolocator.distanceBetween(
      position.latitude,
      position.longitude,
      projectLatitude,
      projectLongitude,
    );

    // 6. Allow inspection only within this radius.
    const allowedRadiusMeters = 200.0;

    if (distanceMeters > allowedRadiusMeters) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Inspection blocked. You are '
            '${distanceMeters.toStringAsFixed(0)} m away from '
            'the registered project location.',
          ),
          duration: const Duration(seconds: 5),
        ),
      );
      return;
    }

    // 7. Location verified — assign inspection.
    final response = await http.post(
      Uri.parse('$apiBaseUrl/inspections/assign'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Inspection assignment failed: '
        '${response.statusCode}',
      );
    }

    final data = jsonDecode(response.body);

if (!mounted) return;

await loadProjectRisk();
    final inspectionId = data['inspection_id'];
    final inspectorId = data['inspector_id'];

   Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => InspectionPage(
      inspectionId: inspectionId,
      projectId: widget.projectId,
      inspectorId: inspectorId.toString(),
    ),
  ),
);
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to start inspection: $e'),
      ),
    );
  }
}

  void showSendAlertDialog() {
    if (alertMembers.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No alert members configured')),
      );
      return;
    }

    selectedAlertMembers.clear();

    showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              title: const Text('Send Alert'),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Select alert recipients:'),
                    const SizedBox(height: 8),
                    ...alertMembers.map((member) {
                      final phone = member['phone'] ?? '';
                      return CheckboxListTile(
                        title: Text(member['name'] ?? ''),
                        subtitle: Text(
                            '${member['role'] ?? ''} • $phone'),
                        value: selectedAlertMembers.contains(phone),
                        onChanged: (value) {
                          setDialogState(() {
                            if (value == true) {
                              selectedAlertMembers.add(phone);
                            } else {
                              selectedAlertMembers.remove(phone);
                            }
                          });
                        },
                      );
                    }),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pop(dialogContext);
                    if (selectedAlertMembers.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                            content: Text('No recipients selected')),
                      );
                      return;
                    }
                    // NOTE: this only updates the UI. No real SMS/email
                    // provider is connected yet, so no message is actually
                    // delivered outside this app.
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          'Alert queued for ${selectedAlertMembers.length} recipient(s) (demo only — no real provider connected)',
                        ),
                      ),
                    );
                  },
                  child: const Text('Send Alert'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Project Risk')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (isLoading)
  const Center(
    child: CircularProgressIndicator(),
  )
else if (errorMessage != null)
  Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.error_outline,
            size: 48,
            color: Colors.red,
          ),
          const SizedBox(height: 12),
          Text(
            errorMessage!,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: loadProjectRisk,
            child: const Text('RETRY'),
          ),
        ],
      ),
    ),
  )
else if (trustData != null)
  Builder(
    builder: (context) {
      final projectName =
          trustData!['project']?.toString() ?? 'Unknown Project';

      final trustScore =
          (trustData!['trust_score'] ?? 0).toDouble();

      final riskScore =
          (trustData!['risk_score'] ?? 0).toDouble();

      final aiDecision =
          trustData!['latest_ai_decision']
              as Map<String, dynamic>?;

      final riskLevel =
          aiDecision?['risk_level']?.toString() ?? 'UNKNOWN';

      final confidence =
          (aiDecision?['confidence'] ?? 0).toDouble();

      final recommendation =
          aiDecision?['recommendation']?.toString() ??
          'No recommendation available';

      final signals =
          aiDecision?['signals'] as Map<String, dynamic>? ?? {};

      Color riskColor;

      switch (riskLevel) {
        case 'HIGH':
          riskColor = Colors.red;
          break;
        case 'MEDIUM':
          riskColor = Colors.orange;
          break;
        case 'LOW':
          riskColor = Colors.green;
          break;
        default:
          riskColor = Colors.grey;
      }

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            projectName,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 16),

          Card(
            color: riskColor.withValues(alpha: 0.08),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Text(
                    '${trustScore.toStringAsFixed(0)} / 100',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: riskColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'TRUST SCORE',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Risk Score: ${riskScore.toStringAsFixed(0)}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    riskLevel,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: riskColor,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          const Text(
            'AI Risk Analysis',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          ListTile(
            leading: const Icon(Icons.people),
            title: const Text('Attendance Anomaly'),
            subtitle: Text(
              '${signals['attendance_anomaly'] ?? 0}',
            ),
          ),

          ListTile(
            leading: const Icon(Icons.description),
            title: const Text('Evidence Anomaly'),
            subtitle: Text(
              '${signals['evidence_anomaly'] ?? 0}',
            ),
          ),

          ListTile(
            leading: const Icon(Icons.videocam),
            title: const Text('CCTV Anomaly'),
            subtitle: Text(
              '${signals['cctv_anomaly'] ?? 0}',
            ),
          ),

          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('Inspection Gap'),
            subtitle: Text(
              '${signals['inspection_gap'] ?? 0}',
            ),
          ),

          const SizedBox(height: 16),

          const Text(
            'AI Recommendation',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          Text(recommendation),

          const SizedBox(height: 8),

          Text(
            'Risk Level: $riskLevel',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: riskColor,
            ),
          ),

          const SizedBox(height: 4),

          Text(
            'AI Confidence: ${(confidence * 100).toStringAsFixed(0)}%',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 24),
        ],
      );
    },
  ),const SizedBox(height: 16),

SizedBox(
  width: double.infinity,
  child: ElevatedButton.icon(
    onPressed: analyzeProject,
    icon: const Icon(Icons.analytics),
    label: const Text('RUN AI ANALYSIS'),
  ),
),

const SizedBox(height: 16),

Row(
  children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: startInspection,
                    child: const Text('START INSPECTION'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: showSendAlertDialog,
                    child: const Text('SEND ALERT'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}







class InspectionPage extends StatefulWidget {
  final int inspectionId;
  final int projectId;
  final String inspectorId;

  const InspectionPage({
    super.key,
    required this.inspectionId,
    required this.projectId,
    required this.inspectorId,
  });

  @override
  State<InspectionPage> createState() => _InspectionPageState();
}

class _InspectionPageState extends State<InspectionPage> {
  final TextEditingController findingsController =
      TextEditingController();
  bool cctvConnected = false;

  bool attendanceVerified = false;
  bool documentsVerified = false;
  bool cctvVerified = false;
  bool beneficiariesVerified = false;
  bool submitting = false;
  XFile? capturedEvidence;
  final TextEditingController cctvUrlController =
    TextEditingController();

  Future<void> captureEvidence() async {
  final picker = ImagePicker();

  final image = await picker.pickImage(
    source: ImageSource.camera,
    imageQuality: 85,
  );

  if (image == null) return;

  setState(() {
    capturedEvidence = image;
  });
}

  @override
void dispose() {
  findingsController.dispose();
  cctvUrlController.dispose();
  super.dispose();
}


Future<void> uploadEvidence() async {
  if (capturedEvidence == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Capture evidence first')),
    );
    return;
  }

  if (accessToken == null || accessToken!.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Authentication token not available')),
    );
    return;
  }

  try {
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
      ),
    );

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$apiBaseUrl/evidence'),
    );

    request.headers['Authorization'] = 'Bearer $accessToken';

    request.fields['project_id'] = widget.projectId.toString();
    request.fields['inspection_id'] = widget.inspectionId.toString();
    request.fields['evidence_type'] = 'PHOTO';
    request.fields['latitude'] = position.latitude.toString();
    request.fields['longitude'] = position.longitude.toString();

    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        capturedEvidence!.path,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(
        'Evidence upload failed: ${response.statusCode}\n${response.body}',
      );
    }

    final data = jsonDecode(response.body);

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Evidence uploaded successfully. ID: ${data['id']}',
        ),
      ),
    );
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to upload evidence: $e'),
      ),
    );
  }
}


Future<void> startRandomVC() async {
  if (accessToken == null || accessToken!.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Authentication token not available'),
      ),
    );
    return;
  }

  try {
    final response = await http.post(
      Uri.parse('$apiBaseUrl/vc/random'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'project_id': widget.projectId,
        'participant_role': 'PROJECT_INCHARGE',
      }),
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(
        'Random VC request failed: ${response.statusCode}\n${response.body}',
      );
    }

    final data = jsonDecode(response.body);

    if (!mounted) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Random VC'),
        content: Text(
          'VC ID: ${data['vc_id']}\n'
          'Status: ${data['status']}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to start Random VC: $e'),
      ),
    );
  }
}





  Future<void> submitInspection() async {
    if (accessToken == null || accessToken!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Authentication token not available'),
        ),
      );
      return;
    }

    if (findingsController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter inspection findings'),
        ),
      );
      return;
    }

    setState(() {
      submitting = true;
    });

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
        ),
      );

      final response = await http.post(
        Uri.parse(
          '$apiBaseUrl/inspections/${widget.inspectionId}/submit',
        ),
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
  'findings': findingsController.text.trim(),
  'latitude': position.latitude,
  'longitude': position.longitude,
  'attendance_verified': attendanceVerified,
  'documents_verified': documentsVerified,
  'cctv_verified': cctvVerified,
  'beneficiaries_verified': beneficiariesVerified,
}),
      );

      if (response.statusCode != 200) {
        throw Exception(
          'Inspection submission failed: ${response.statusCode}',
        );
      }

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Inspection submitted successfully'),
        ),
      );

      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Unable to submit inspection: $e'),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inspection'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Inspection ID: ${widget.inspectionId}',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Inspector: ${widget.inspectorId}',
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 20),

            const Text(
              'Inspection Checklist',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),

            CheckboxListTile(
              title: const Text('Attendance verified'),
              value: attendanceVerified,
              onChanged: (value) {
                setState(() {
                  attendanceVerified = value ?? false;
                });
              },
            ),

            CheckboxListTile(
              title: const Text('Documents verified'),
              value: documentsVerified,
              onChanged: (value) {
                setState(() {
                  documentsVerified = value ?? false;
                });
              },
            ),

            CheckboxListTile(
              title: const Text('CCTV activity verified'),
              value: cctvVerified,
              onChanged: (value) {
                setState(() {
                  cctvVerified = value ?? false;
                });
              },
            ),

           CheckboxListTile(
  title: const Text('Beneficiary presence verified'),
  value: beneficiariesVerified,
  onChanged: (value) {
    setState(() {
      beneficiariesVerified = value ?? false;
    });
  },
),

const SizedBox(height: 16),

const Text(
  'CCTV Surveillance',
  style: TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.bold,
  ),
),

const SizedBox(height: 8),

Card(
  child: Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: cctvUrlController,
          decoration: const InputDecoration(
            labelText: 'CCTV Stream URL',
            hintText: 'Enter CCTV stream endpoint',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
           onPressed: () {
  final url = cctvUrlController.text.trim();

  if (url.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Enter a CCTV stream URL'),
      ),
    );
    return;
  }

  setState(() {
    cctvConnected = true;
  });

  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(
      content: Text('CCTV endpoint connected'),
    ),
  );
},
            icon: const Icon(Icons.videocam),
            label: const Text('CONNECT CCTV'),
          ),
        ),
      ],
    ),
  ),
),

if (cctvConnected) ...[
  const SizedBox(height: 8),
  const Row(
    children: [
      Icon(Icons.check_circle, color: Colors.green),
      SizedBox(width: 8),
      Text('CCTV CONNECTED'),
    ],
  ),
],

const SizedBox(height: 16),

SizedBox(
  width: double.infinity,
  child: ElevatedButton.icon(
    onPressed: startRandomVC,
    icon: const Icon(Icons.video_call),
    label: const Text('START RANDOM VC'),
  ),
),

const SizedBox(height: 16),

SizedBox(
  width: double.infinity,
  child: OutlinedButton.icon(
    onPressed: captureEvidence,
    icon: const Icon(Icons.camera_alt),
    label: const Text('CAPTURE EVIDENCE'),
  ),
),

if (capturedEvidence != null)
  Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const SizedBox(height: 12),
      Text(
        'Evidence captured: ${capturedEvidence!.name}',
        style: const TextStyle(
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 12),
      SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: uploadEvidence,
          icon: const Icon(Icons.cloud_upload),
          label: const Text('UPLOAD EVIDENCE'),
        ),
      ),
    ],
  ),

const SizedBox(height: 16),

const Text(
  'Findings',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            TextField(
              controller: findingsController,
              maxLines: 5,
              decoration: const InputDecoration(
                hintText: 'Enter inspection findings',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 20),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: submitting ? null : submitInspection,
                icon: submitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                        ),
                      )
                    : const Icon(Icons.send),
                label: Text(
                  submitting ? 'SUBMITTING...' : 'SUBMIT INSPECTION',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}








// ---------------------------------------------------------------------------
// ALERT MEMBERS PAGE
// ---------------------------------------------------------------------------
class AlertMembersPage extends StatefulWidget {
  const AlertMembersPage({super.key});

  @override
  State<AlertMembersPage> createState() => _AlertMembersPageState();
}

class _AlertMembersPageState extends State<AlertMembersPage> {
  Future<void> addMember() async {
  final newMember = await Navigator.push(
    context,
    MaterialPageRoute(
      builder: (context) => const AddAlertMemberPage(),
    ),
  );

  if (newMember == null || newMember is! Map<String, String>) {
    return;
  }

  if (accessToken == null || accessToken!.isEmpty) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Authentication token not available'),
      ),
    );
    return;
  }

  try {
    final response = await http.post(
      Uri.parse('$apiBaseUrl/alert-members'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'name': newMember['name'],
        'role': newMember['role'],
        'email': newMember['email'],
        'phone': newMember['phone'],
        'active': true,
      }),
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(
        'Create alert member failed: ${response.statusCode}\n${response.body}',
      );
    }

    final data = Map<String, dynamic>.from(
      jsonDecode(response.body),
    );

    if (!mounted) return;

    setState(() {
      alertMembers.add({
        'id': data['id'].toString(),
        'name': data['name'].toString(),
        'role': data['role'].toString(),
        'email': data['email'].toString(),
        'phone': data['phone'].toString(),
      });
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Alert member added successfully'),
      ),
    );
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Unable to add alert member: $e'),
      ),
    );
  }
}

  Future<void> confirmDelete(Map<String, String> member) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Delete Alert Member'),
          content: Text(
            'Remove ${member['name']} from alert members? '
            'Other configured alert members will be notified before deletion.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    // Other configured members must be notified BEFORE deletion,
    // even if the member being deleted is itself an alert member.
    final otherMembers =
        alertMembers.where((m) => m['phone'] != member['phone']).toList();

    if (otherMembers.isNotEmpty) {
      // NOTE: demo only — no real notification provider connected yet.
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Notified ${otherMembers.length} other member(s) before deletion (demo only)',
          ),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No other alert members to notify'),
        ),
      );
    }

    setState(() {
      alertMembers.removeWhere((m) => m['phone'] == member['phone']);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Alert Members')),
      floatingActionButton: FloatingActionButton(
        onPressed: addMember,
        child: const Icon(Icons.add),
      ),
      body: alertMembers.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.people_outline, size: 64, color: Colors.grey),
                  const SizedBox(height: 12),
                  const Text('No Alert Members',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const Text('Add officers who should receive alerts.',
                      style: TextStyle(color: Colors.grey)),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: addMember,
                    child: const Text('ADD ALERT MEMBER'),
                  ),
                ],
              ),
            )
          : ListView.builder(
              itemCount: alertMembers.length,
              itemBuilder: (context, index) {
                final member = alertMembers[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: ListTile(
                    title: Text(member['name'] ?? ''),
                    subtitle: Text(
                      '${member['role'] ?? ''}\n${member['email'] ?? ''} • ${member['phone'] ?? ''}',
                    ),
                    isThreeLine: true,
                    trailing: IconButton(
                      icon: const Icon(Icons.delete, color: Colors.red),
                      onPressed: () => confirmDelete(member),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

// ---------------------------------------------------------------------------
// ADD ALERT MEMBER PAGE
// ---------------------------------------------------------------------------
class AddAlertMemberPage extends StatefulWidget {
  const AddAlertMemberPage({super.key});

  @override
  State<AddAlertMemberPage> createState() => _AddAlertMemberPageState();
}

class _AddAlertMemberPageState extends State<AddAlertMemberPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController nameController = TextEditingController();
  final TextEditingController roleController = TextEditingController();
  final TextEditingController emailController = TextEditingController();
  final TextEditingController phoneController = TextEditingController();

  @override
  void dispose() {
    nameController.dispose();
    roleController.dispose();
    emailController.dispose();
    phoneController.dispose();
    super.dispose();
  }

  String? validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Email is required';
    }
    final emailRegex = RegExp(r'^[\w\.\-]+@[\w\-]+\.[a-zA-Z]{2,}$');
    if (!emailRegex.hasMatch(value.trim())) {
      return 'Enter a valid email';
    }
    return null;
  }

  String? validatePhone(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Phone number is required';
    }
    if (value.trim().length != 10) {
      return 'Enter a valid 10-digit phone number';
    }
    return null;
  }

  void addMember() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    Navigator.pop(
      context,
      {
        'name': nameController.text.trim(),
        'role': roleController.text.trim(),
        'email': emailController.text.trim(),
        'phone': phoneController.text.trim(),
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Alert Member')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  prefixIcon: Icon(Icons.person),
                  border: OutlineInputBorder(),
                ),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Name is required'
                    : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: roleController,
                decoration: const InputDecoration(
                  labelText: 'Role',
                  prefixIcon: Icon(Icons.badge),
                  border: OutlineInputBorder(),
                ),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Role is required'
                    : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  prefixIcon: Icon(Icons.email),
                  border: OutlineInputBorder(),
                ),
                validator: validateEmail,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: phoneController,
                keyboardType: TextInputType.phone,
                maxLength: 10,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                ],
                decoration: const InputDecoration(
                  labelText: 'Phone',
                  prefixIcon: Icon(Icons.phone),
                  border: OutlineInputBorder(),
                  counterText: '',
                ),
                validator: validatePhone,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: addMember,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('ADD MEMBER'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
