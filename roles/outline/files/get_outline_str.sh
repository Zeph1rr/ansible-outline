#!/bin/bash

export SHADOWBOX_DIR="${SHADOWBOX_DIR:-/opt/outline}"

readonly ACCESS_CONFIG="${ACCESS_CONFIG:-${SHADOWBOX_DIR}/access.txt}"

function get_field_value {
    grep "$1" "${ACCESS_CONFIG}" | sed "s/$1://"
}


echo -e "\033[1;32m{\"apiUrl\":\"$(get_field_value apiUrl)\",\"certSha256\":\"$(get_field_value certSha256)\"}\033[0m"
