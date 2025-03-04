#!/usr/bin/env bash

set -e

for _ in $(seq "$1"); do
	git pull --rebase
	if git push; then
		exit 0
	fi
	sleep 1
done
exit 1