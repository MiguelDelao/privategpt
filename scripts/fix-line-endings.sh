#!/bin/bash

# Fix line endings for cross-platform compatibility
echo "Converting script line endings for cross-platform compatibility..."

# Convert init-keycloak-realm.sh to Unix line endings
if command -v dos2unix &> /dev/null; then
    dos2unix scripts/init-keycloak-realm.sh
    echo "✅ Converted using dos2unix"
elif command -v sed &> /dev/null; then
    sed -i 's/\r$//' scripts/init-keycloak-realm.sh
    echo "✅ Converted using sed"
else
    echo "⚠️  No line ending conversion tool available"
    echo "💡 On Windows, use: git config core.autocrlf true"
fi

echo "✅ Line ending fix complete"