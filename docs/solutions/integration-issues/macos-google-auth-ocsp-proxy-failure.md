---
title: "macOS Google sign-in blocked by an OCSP proxy route"
date: "2026-10-25"
category: "integration-issues"
module: "Clash Verge routing"
problem_type: "integration_issue"
component: "authentication"
symptoms:
  - "Internet Accounts reported Authentication Failed while adding Google."
  - "Google login worked in a browser, but the system authorization page did not open."
  - "trustd received an invalid response from ocsp.digicert.com."
root_cause: "config_error"
resolution_type: "config_change"
severity: "medium"
tags: ["macos", "mail", "google-oauth", "ocsp", "clash-verge", "tun"]
---

# macOS Google sign-in blocked by an OCSP proxy route

## Problem

Adding a Google account in macOS Internet Accounts failed before a usable authorization page opened. The route comparison and successful retry implicated a failing certificate-status query through the proxy. A single-domain direct route restored the query, after which Google authorization opened.

The verified endpoint of this investigation was the Google authorization page. Final consent, account creation in Internet Accounts, and Mail synchronization remained unverified when browser automation was stopped by an access restriction.

## Symptoms

- The system displayed `Authentication Failed` and `Failed to authenticate with Google, please try again later`.
- The same account could sign in to Gmail in a browser. A request to Google through macOS URLSession also returned HTTP 200.
- At the failure time, `trustd` reported an invalid OCSP response from `ocsp.digicert.com`; Internet Accounts subsequently logged `NSURLErrorDomain -999`. The cancellation code alone did not identify the cause.

## What didn't work

Temporarily changing the default browser from Chrome to Safari reproduced the failure. Chrome was restored after the comparison.

Successful Google HTTPS requests did not establish that the exact failing certificate-status request was reachable. Likewise, `curl --noproxy '*'` still used the active TUN route and fake-IP DNS; it was not a physical-network control.

## Solution

Compare the exact OCSP request from local diagnostics across routes, keeping its hostname and request path unchanged. This incident produced:

| Route | Result |
| --- | --- |
| Explicit local HTTP proxy | HTTP 502, empty body |
| No explicit proxy, TUN still active | Empty response through a fake IP |
| Physical interface with a freshly resolved address | HTTP 200, `application/ocsp-response`, parseable response reporting `good` |
| Original proxy entry after the domain rule | The same successful OCSP result |

With authorization, prepend this exact-domain rule to the active Mac rules override:

```yaml
prepend:
  - DOMAIN,ocsp.digicert.com,DIRECT
```

Keep the existing rules after it. Back up the current files, validate the complete candidate with Mihomo, reload, and read back the running rules. The trial verified that the prior rule sequence and selected proxy groups were unchanged. Retrying Internet Accounts then opened Google's actual macOS authorization page.

This was a live Mac fix. The rule had not yet been mirrored into this repository when the learning was captured, and no other device was verified. The [project workflow](../../../AGENTS.md) defines the export and device-specific follow-up. The existing apply path checks the current override prefix and validates a candidate (`sync-mac.py:230`), then reloads a configuration payload and reads back the rules (`sync-mac.py:262`).

## Why this works

OCSP checks a certificate's revocation status. Apple lists `ocsp.digicert.com` on TCP port 80 as a certificate-validation dependency, including for macOS. A working login host on HTTPS therefore does not establish that all authorization dependencies are reachable. [Apple's network requirements](https://support.apple.com/en-us/101555)

The controlled route comparison and successful retry support the failing OCSP route as the cause of this observed blocker. They do not establish why the upstream proxy path returned 502, or that every similar Google authorization error has this cause.

## Prevention

- Separate certificate reachability, authorization-page launch, consent, account persistence, and mailbox synchronization in acceptance results. Verify each stage that the task requires.
- When the browser works but system authorization fails, inspect the failing time window in `trustd` and Internet Accounts logs before changing credentials or broad proxy settings.
- Use the exact certificate-status request for comparisons. Resolve a fresh address and bind the physical interface when testing outside an active TUN; omitting a proxy flag is insufficient.
- Scope any exception to the demonstrated host. Preserve certificate validation and the original HTTP endpoint; do not disable TLS verification to make a diagnostic pass.
- Check saved configuration and effective runtime separately. Before restoring a backup, verify that files and runtime still belong to the trial; preserve unknown concurrent changes for reconciliation.

For a saved OCSP response, this command exposes its reported status:

```sh
openssl ocsp -respin response.der -noverify -text
```

Here `-noverify` skips response verification, including signature verification, in the diagnostic parser. A parseable `good` result is not independent cryptographic verification, and this command does not change macOS trust policy. The system authorization retry remains necessary.

## Related

- [Gmail transport rules](../../../clash/rules.yaml), `clash/rules.yaml:58`, address IMAP, SMTP, and POP connectivity. They cover a later stage than this certificate-status failure.
- [Mac rule export and device activation](../../../README.md#publishing-mac-changes-to-the-repository-primary).
