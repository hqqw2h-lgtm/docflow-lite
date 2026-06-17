#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROPERTIES_FILE="$BASE_DIR/.mvn/wrapper/maven-wrapper.properties"
if [[ ! -f "$PROPERTIES_FILE" ]]; then
  echo "Missing $PROPERTIES_FILE" >&2
  exit 1
fi

DISTRIBUTION_URL="$(WRAPPER_PROPS="$PROPERTIES_FILE" python3 - <<'INNER_PY'
import os
from pathlib import Path
props = Path(os.environ['WRAPPER_PROPS']).read_text().splitlines()
for line in props:
    if line.startswith('distributionUrl='):
        print(line.split('=', 1)[1])
        break
INNER_PY
)"
ARCHIVE_NAME="${DISTRIBUTION_URL##*/}"
MAVEN_DIR_NAME="${ARCHIVE_NAME%-bin.tar.gz}"
WRAPPER_DIR="$BASE_DIR/.mvn/wrapper"
MAVEN_HOME="$WRAPPER_DIR/$MAVEN_DIR_NAME"
ARCHIVE_PATH="$WRAPPER_DIR/$ARCHIVE_NAME"

if [[ ! -x "$MAVEN_HOME/bin/mvn" ]]; then
  mkdir -p "$WRAPPER_DIR"
  if [[ ! -f "$ARCHIVE_PATH" ]]; then
    echo "Downloading Maven from $DISTRIBUTION_URL" >&2
    DOWNLOAD_URL="$DISTRIBUTION_URL" DOWNLOAD_PATH="$ARCHIVE_PATH" python3 - <<'INNER_PY'
import os
from urllib.request import urlretrieve
urlretrieve(os.environ['DOWNLOAD_URL'], os.environ['DOWNLOAD_PATH'])
INNER_PY
  fi
  tar -xzf "$ARCHIVE_PATH" -C "$WRAPPER_DIR"
fi

exec "$MAVEN_HOME/bin/mvn" "$@"
