# SOCA for Frappe / ERPNext

An installable Frappe app for OpenID Connect code sign-in with PKCE S256,
ES256 `private_key_jwt` and hosted or proxy Client ID Metadata Documents.
**Alpha 0.1.0a1: ordinary SSO defaults off.** Review the
[requirements assessment](docs/requirements-coverage.md) before a staging rollout.

The app adds native **SOCA Profile** and **SOCA Identity** DocTypes, existing-login
buttons, document/candidate-test actions and headless maintenance. Admission denies
by default. Existing accounts require independently approved issuer/subject links;
a verified email never establishes a link. Optional provisioning creates website
users only, with a configured role that has no desk access. Existing local roles,
credentials and edits remain intact. Local administrator recovery stays available.

Install into a supported Bench checkout:

```sh
bench get-app https://github.com/RESOAuth/frappe-soca-plugin.git --branch feat/soca-oidc-integration
bench --site your-site install-app frappe_soca
bench build --app frappe_soca
```

The tested host is **Frappe 16.52.0** in the official **ERPNext 16.51.1** image,
with MariaDB 11.4 and Redis 7. ERPNext application installation is optional for this
framework integration; the native tests install Frappe and this app. Other host
versions have not been validated. Python protocol fixtures run independently of Bench.

Generate deployment keys using `python demo/generate-secrets.py`. Copy the contents
of [demo/config.example.json](demo/config.example.json) into a `soca` object in the
site's `site_config.json`, replacing the origin/key references and adding explicit
admission rules. Create the corresponding `staff` SOCA Profile while disabled. Site
configuration overrides and locks database/UI values. Keep key files outside the
site's public files and database, owned by the Frappe process with mode 0600.

Use native Desk search to open SOCA Profile and SOCA Identity. Publish/check the
candidate documents, complete a real operator-bound test login, then enable the
profile. Candidate tests do not create users, link accounts or replace your session.
See [configuration and recovery](docs/operations.md) for every supported setting.
Headless checks/status/disable use native Bench execution:

```sh
bench --site your-site execute frappe_soca.commands.status --kwargs '{"profile":"staff"}'
bench --site your-site execute frappe_soca.commands.check --kwargs '{"profile":"staff"}'
bench --site your-site execute frappe_soca.commands.disable --kwargs '{"profile":"staff"}'
```

The public routes are `/api/method/frappe_soca.api.metadata?profile=staff` and
`/api/method/frappe_soca.api.jwks?profile=staff`; the exact callback route is
`/api/method/frappe_soca.api.callback?profile=staff`. Use the deployment origin as
canonical HTTPS. Proxy mode supports private/local HTTPS applications using inline
public keys; its encoded URL is public and may change the client ID during a key change.

Run the disposable real-host container test with `bash demo/test-host.sh` using
Podman, or set `CONTAINER_RUNTIME=docker`. The script builds the pinned official
host image, creates MariaDB/Redis/site, installs the app, performs native account
checks and removes its own containers. It does not contact an identity provider.
For a manual demo, use this Containerfile in the official
[Frappe Docker development/deployment stack](https://github.com/frappe/frappe_docker),
then install the app into a disposable site. Keep sign-in behind HTTPS and redact
callback queries from Gunicorn/reverse-proxy access logs.

```sh
python -m pip install --require-hashes -r requirements-test.txt
python -m pytest -q
ruff check frappe_soca tests
python -m build
python tests/check_package.py
bash demo/test-host.sh
```

[Dated results](docs/verification.md) distinguish synthetic security fixtures,
native host checks and unattempted real-provider logins. Automated rotation, HSM/KMS,
claim diagnostics, broad algorithm coverage, provider logout, existing-session
revocation and complete conformance/accessibility testing remain gaps. No live
RESOAuth login or production-readiness certification is claimed.

See [SECURITY.md](SECURITY.md), [threat model](docs/threat-model.md) and
[AGPL-3.0-only licence](LICENSE). The protocol transport is adapted from the
[RESOAuth Wagtail implementation](https://github.com/RESOAuth/wagtail-soca-plugin);
account selection follows the newer protected-association requirements.
