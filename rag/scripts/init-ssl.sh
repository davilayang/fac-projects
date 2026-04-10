#!/bin/bash
# Run once on a fresh server to obtain the initial Let's Encrypt certificate.
# After this, the certbot service in docker-compose handles renewals automatically
# via webroot (nginx serves the ACME challenge on port 80).
#
# Requires: TAG env var set (same one used for docker compose)
set -e

DOMAIN="arxiv-rag.45weeks.com"
EMAIL="${CERTBOT_EMAIL:-admin@45weeks.com}"
TAG="${TAG:-latest}"

# nginx needs a cert to start, but Let's Encrypt needs nginx to serve the ACME
# challenge — chicken-and-egg. Break it by seeding a self-signed cert first.
echo "==> Creating temporary self-signed certificate..."
TAG=$TAG docker compose run --rm --entrypoint /bin/sh certbot -c "
    mkdir -p /etc/letsencrypt/live/$DOMAIN &&
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
        -out  /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
        -days 1 -subj '/CN=localhost' 2>/dev/null
"

echo "==> Starting nginx with self-signed certificate..."
TAG=$TAG docker compose up -d --no-deps nginx
sleep 2

echo "==> Removing self-signed certificate so certbot can issue the real one..."
TAG=$TAG docker compose run --rm --entrypoint /bin/sh certbot -c "
    rm -rf /etc/letsencrypt/live/$DOMAIN \
           /etc/letsencrypt/archive/$DOMAIN \
           /etc/letsencrypt/renewal/$DOMAIN.conf 2>/dev/null || true
"

echo "==> Obtaining Let's Encrypt certificate for $DOMAIN..."
TAG=$TAG docker compose run --rm --entrypoint certbot certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "==> Reloading nginx with real certificate..."
TAG=$TAG docker compose exec nginx nginx -s reload

echo "==> Done. Certificate obtained for $DOMAIN."
echo "    Certbot will auto-renew every 12 hours via the certbot service."
