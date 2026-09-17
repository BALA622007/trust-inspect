# Mobile app integration

For the SIH prototype, the backend already exposes the APIs needed by a Flutter
or React Native inspector app.

Recommended mobile screens:
1. Login / SSO
2. My Assignments
3. Project Details
4. Start Inspection
5. GPS Verification
6. Live Evidence Capture
7. Attendance Verification
8. Checklist
9. Submit Report
10. Offline Sync Queue
11. Evidence Trust Status

Important production rule:
Critical evidence should be captured through the app camera rather than accepting
arbitrary old gallery media. The backend POC accepts uploads for demonstration.
Use device attestation, secure storage, signed requests and server-side validation
in production.
