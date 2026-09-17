# Architecture

## Trust loop

DATA -> AI FUSION -> EXPLANATION -> DECISION -> ACTION -> HUMAN REVIEW -> VERIFIED OUTCOME -> MODEL FEEDBACK

## Three logical ledgers

1. Evidence Ledger
   - evidence ID
   - SHA-256 hash
   - timestamp
   - GPS
   - inspection/project ID
   - provenance

2. AI Decision Ledger
   - model/version
   - risk score
   - confidence
   - explanation
   - recommendation

3. Governance Ledger
   - actor
   - action
   - time
   - subject
   - workflow state

The POC uses one hash-chained table with a ledger_type field. Production can split
storage physically and place immutable records into WORM/object-lock storage.

## AI

The demo attendance detector uses IsolationForest. The risk score is a transparent
weighted model so judges can inspect the calculation. A production system should
benchmark several models, calibrate probabilities, conduct bias/error analysis,
and use a model registry.

## CCTV

The POC accepts CCTV events rather than decoding RTSP streams. A production
video gateway can normalize RTSP/ONVIF feeds, enforce access control and generate
events for the AI layer. Avoid continuous face recognition unless there is a
specific lawful, necessary and approved requirement.

## Privacy

Collect the minimum necessary data. Separate beneficiary identity from analytics
where possible. Encrypt data in transit and at rest, use role-based access,
retention policies, consent/notice where required, and immutable access logging.
