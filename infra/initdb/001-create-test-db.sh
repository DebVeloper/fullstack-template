#!/bin/sh
set -eu

TEST_DB="${POSTGRES_TEST_DB:-app_test}"
PRIMARY_DB="${POSTGRES_DB:-app}"
DB_USER="${POSTGRES_USER:-postgres}"

if [ -z "${TEST_DB}" ]; then
  echo "POSTGRES_TEST_DB is empty; skipping test database creation."
  exit 0
fi

case "${TEST_DB}" in
  *[!a-zA-Z0-9_]*)
    echo "POSTGRES_TEST_DB contains invalid characters: ${TEST_DB}" >&2
    exit 1
    ;;
esac

if [ "${TEST_DB}" = "${PRIMARY_DB}" ]; then
  echo "POSTGRES_TEST_DB matches POSTGRES_DB (${PRIMARY_DB}); skipping."
  exit 0
fi

DB_EXISTS="$(psql -v ON_ERROR_STOP=1 --username "${DB_USER}" --dbname "${PRIMARY_DB}" -tAc "SELECT 1 FROM pg_database WHERE datname = '${TEST_DB}'")"

if [ "${DB_EXISTS}" = "1" ]; then
  echo "Database ${TEST_DB} already exists; skipping."
  exit 0
fi

psql -v ON_ERROR_STOP=1 --username "${DB_USER}" --dbname "${PRIMARY_DB}" -c "CREATE DATABASE \"${TEST_DB}\""
echo "Created test database: ${TEST_DB}"
