#!/bin/bash
set -e
cd /opt/agentic-framework

if [ ! -d .git ]; then
  git init
  git add -A
  git commit -m "Initial commit v3.0"
fi

git config user.email "deploy@agentic-framework.local"
git config user.name "Agentic Deploy"

if ! git remote | grep -q "openclaw"; then
  git remote add openclaw-upstream https://github.com/opencodelabs/openclaw.git 2>/dev/null || true
fi

cat > sync-openclaw.sh << 'SYNCEND'
#!/bin/bash
cd /opt/agentic-framework
git fetch openclaw-upstream main 2>/dev/null || exit 0
COMMITS=$(git log HEAD..openclaw-upstream/main --oneline 2>/dev/null | wc -l)
if [ "$COMMITS" -gt 0 ]; then
  git branch openclaw-backup 2>/dev/null
  git merge openclaw-upstream/main --no-edit && sudo docker compose build && sudo docker compose up -d || git merge --abort
fi
SYNCEND

chmod +x sync-openclaw.sh
(crontab -l 2>/dev/null | grep -v sync-openclaw; echo "0 */6 * * * /opt/agentic-framework/sync-openclaw.sh") | crontab - 2>/dev/null || true
echo "Git configured"
