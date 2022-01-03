#!/usr/bin/env bash

set -eE 
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'echo "\"${last_command}\" command filed with exit code $?."' ERR

python gen-bookmarks.py test/userData.json -o test/output/json-bookmarks.html
python gen-bookmarks.py test/userData.json -w "Test Workspace" -o test/output/json-bookmarks-filtered.html
python gen-bookmarks.py test/userData.txt -o test/output/yaml-bookmarks.html
python gen-bookmarks.py test/userData.txt -w "Test Workspace" -o test/output/yaml-bookmarks-filtered.html

cmp --silent test/output/json-bookmarks.html test/output/yaml-bookmarks.html
cmp --silent test/output/json-bookmarks-filtered.html test/output/yaml-bookmarks-filtered.html

