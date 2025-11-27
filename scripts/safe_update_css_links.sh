#!/bin/bash
set -u
ROOT="/volume1/JENSEN/agents/my-agent"
BASE="$ROOT/app/templates/_base.html"
LOGIN="$ROOT/app/static/login.html"
TS="$(date +%Y%m%d-%H%M%S)"
BACK="$ROOT/_archive/pre_step2_safe_$TS"
mkdir -p "$BACK"

echo "[info] Backing up edited files to: $BACK"
cp -v "$BASE"  "$BACK/_base.html"
cp -v "$LOGIN" "$BACK/login.html"

fix_file () {
  infile="$1"
  tmp1="${infile}.tmp1"
  tmp2="${infile}.tmp2"

  echo "[info] Processing: $infile"

  # 1) Remove any existing /static/*.css <link rel="stylesheet"> lines (case-insensitive)
  #    Write to tmp1 to avoid in-place sed quirks on Synology.
  awk 'BEGIN{IGNORECASE=1}
       !($0 ~ /<link/ && $0 ~ /rel=["'"'"']stylesheet["'"'"']/ && $0 ~ /href=["'"'"']\/static\/[^"'"'"']*\.css/)
       { print }' "$infile" > "$tmp1"

  # 2) Insert two links (theme then final) right after the first <head ...> occurrence
  inserted=0
  awk 'BEGIN{IGNORECASE=1}
       {
         print
         if (inserted==0 && $0 ~ /<head/){
           print "    <link rel=\"stylesheet\" href=\"/static/theme.css?v=phase8_final\">"
           print "    <link rel=\"stylesheet\" href=\"/static/final.css?v=phase8_final\">"
           inserted=1
         }
       }' "$tmp1" > "$tmp2"

  mv -f "$tmp2" "$infile"
  rm -f "$tmp1"

  # 3) Show the two lines we just ensured exist
  echo "[ok] Links in $infile:"
  grep -n '/static/.*\.css?v=phase8_final' "$infile" || true
}

fix_file "$BASE"
fix_file "$LOGIN"

echo "[info] Restarting container so templates are reloaded..."
docker compose -f "$ROOT/docker-compose.yml" restart || true

echo "[verify] Expect 2 links on each page (theme + final)"
echo -n "login count: ";  curl -sk https://agent.meetjensen.com/static/login.html | grep -i '/static/.*\.css?v=phase8_final' | wc -l
echo -n "ui count:    ";  curl -sk https://agent.meetjensen.com/ui/ | grep -i '/static/.*\.css?v=phase8_final' | wc -l

echo "[done] Backups at: $BACK"
