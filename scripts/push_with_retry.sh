#!/usr/bin/env bash

for i in $(seq $1); do
	git pull --rebase
	if git push; then
		exit 0
	fi
	sleep 1
done
exit 1