FROM docker.io/frappe/erpnext:v16.51.1@sha256:5de2e2fb769258489a3e2432c024a74e031dca20712474f81267d2e81719022d
USER frappe
COPY --chown=1000:1000 . /home/frappe/frappe-bench/apps/frappe_soca
RUN /home/frappe/frappe-bench/env/bin/pip install --require-hashes -r /home/frappe/frappe-bench/apps/frappe_soca/requirements.txt
RUN /home/frappe/frappe-bench/env/bin/pip install --no-deps -e /home/frappe/frappe-bench/apps/frappe_soca
RUN /home/frappe/frappe-bench/env/bin/python -c "from pathlib import Path; p=Path('sites/apps.txt'); s=p.read_text(); p.write_text(s if 'frappe_soca' in s.splitlines() else s.rstrip()+'\\nfrappe_soca\\n')"
