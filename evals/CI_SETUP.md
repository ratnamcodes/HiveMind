# CI evals gate — setup checklist (T18-B)

`.github/workflows/evals.yml` runs the **live** orchestrator, so it needs (1) Vertex auth and
(2) the partner secrets. GitHub-hosted runners can't use your local `gcloud` login, so this is
a one-time setup. Order matters.

## 1 — Vertex service account (Gemini in CI)
```bash
PROJECT=hivemind-hackathon
gcloud iam service-accounts create hivemind-ci --project "$PROJECT" \
  --display-name "HiveMind CI (Vertex)"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:hivemind-ci@$PROJECT.iam.gserviceaccount.com" \
  --role roles/aiplatform.user
gcloud iam service-accounts keys create /tmp/hivemind-ci.json \
  --iam-account "hivemind-ci@$PROJECT.iam.gserviceaccount.com"
```

## 2 — GitHub repo secrets
Load your local `.env` then push each as a secret (`gh auth login` first):
```bash
set -a; . ./.env; set +a          # export the .env vars into the shell

gh secret set GCP_SA_KEY < /tmp/hivemind-ci.json     # the SA key from step 1
gh secret set GOOGLE_CLOUD_PROJECT  -b "hivemind-hackathon"
gh secret set GOOGLE_CLOUD_LOCATION -b "global"
gh secret set GITLAB_URL            -b "$GITLAB_URL"
gh secret set GITLAB_BOT_TOKEN      -b "$GITLAB_BOT_TOKEN"
gh secret set GITLAB_TOKEN          -b "$GITLAB_TOKEN"
gh secret set GITLAB_TARGET_PROJECT -b "$GITLAB_TARGET_PROJECT"
gh secret set DT_ENVIRONMENT        -b "$DT_ENVIRONMENT"
gh secret set DT_PLATFORM_TOKEN     -b "$DT_PLATFORM_TOKEN"
gh secret set DT_API_TOKEN          -b "$DT_API_TOKEN"
gh secret set ELASTIC_CLOUD_ID      -b "$ELASTIC_CLOUD_ID"
gh secret set ELASTIC_API_KEY       -b "$ELASTIC_API_KEY"
gh secret set MDB_URI               -b "$MDB_URI"
gh secret set HMAC_SECRET           -b "$HMAC_SECRET"
gh secret set FIVETRAN_API_KEY      -b "$FIVETRAN_API_KEY"
gh secret set FIVETRAN_API_SECRET   -b "$FIVETRAN_API_SECRET"
gh secret set FIVETRAN_GROUP_ID     -b "$FIVETRAN_GROUP_ID"
```

## 3 — delete the local key
```bash
rm /tmp/hivemind-ci.json
```

## 4 — verify
Open a PR that regresses a scenario. The **HiveMind evals** check runs, posts a score comment,
and blocks merge if `pass_rate` drops > 2 pts below the `main` baseline (`evals/baseline.json`,
which the workflow updates on `main`).

## Caveats — read before enabling on every PR
- Each scenario is a **full live orchestrator run**: it opens a real MR in `hivemind-target`
  (auto-cleaned), hits live Dynatrace / Elastic / Fivetran / Atlas, and **spends Vertex credits**.
  20 scenarios ≈ 1 hr, so the workflow runs a **smoke subset (`--limit 3`)** by default; bump it
  via the `workflow_dispatch` input or run the full suite on a **self-hosted runner**.
- Vertex **per-minute rate limits** can FAIL a scenario transiently in CI (the agents don't retry
  mid-run on 429). A self-hosted runner or added retries gives stability for the full suite.
- The gate **logic** is already verified locally (it blocks a regression with a clear comment);
  this checklist is only the GitHub-Actions plumbing to make it run against real PRs.
```

