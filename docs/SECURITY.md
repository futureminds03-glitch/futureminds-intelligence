# Security baseline

This document supplements, and does not replace or weaken, the FutureMinds Mandatory Engineering Security Standard.

## Initial threat model

Assume evaluation inputs, agent outputs, repository content, tool traces and external artifacts may be malicious or misleading. Threats include prompt injection, malicious fixtures, path traversal, secret exfiltration, poisoned evidence, grader manipulation, unauthorized tool use, cross-project data exposure and denial of service.

## Mandatory baseline

1. Treat all case inputs, model outputs, logs and retrieved repository content as untrusted data.
2. Never execute arbitrary code from an evaluation case in the initial runner.
3. Do not place credentials, tokens, private keys or production secrets in fixtures, logs or artifacts.
4. Use least-privilege, short-lived credentials for future adapters.
5. Separate read, write, deploy and production permissions.
6. Restrict network egress for any future untrusted-code sandbox.
7. Redact sensitive values before persistence or display.
8. Validate input size, structure, types and allowed identifiers.
9. Make grader rules versioned and auditable; subjects must not be able to modify their own grading policy.
10. Record provenance for evidence and preserve the distinction between observation and inference.
11. Keep security gates mandatory; no aggregate score can override them.
12. Define retention, deletion and access controls before collecting customer traces.

## Safe first slice

The first runner processes JSON documents and performs deterministic comparisons only. It must not evaluate JavaScript/Python supplied by a case, shell out to user-controlled commands, fetch arbitrary URLs or accept credentials in input.

## Future sandbox requirements

Before executing untrusted code or agents, design isolated ephemeral environments, resource/time limits, read-only mounts by default, scoped credentials, network policy, artifact scanning, cleanup verification and adversarial tests. Do not ship a partial sandbox and describe it as secure.

## Incident handling

If evidence storage or an adapter exposes sensitive data, stop the affected integration, preserve relevant audit information without copying secrets, rotate exposed credentials through authorized procedures, assess scope and document remediation.
