# The playbook's alerting-rule policy for pint (cloudflare/pint), used offline.
# Every alert names its severity, has a summary and a runbook, and must persist for a minute before
# it fires; recording rules keep the job label so dashboards and routing still work.
# Checked rules: AP-OBS-* in schemas/antipatterns.v1.json.

rule {
  match {
    kind = "alerting"
  }
  annotation "summary" {
    required = true
  }
  annotation "runbook_url" {
    required = true
  }
  label "severity" {
    required = true
    value    = "(page|ticket)"
  }
  for {
    min = "1m"
  }
}

rule {
  match {
    kind = "recording"
  }
  aggregate ".+" {
    keep = ["job"]
  }
}
