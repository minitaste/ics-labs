#!/bin/bash

COUNT=${1:-10}  # дефолт 10 ітерацій

for i in $(seq 1 $COUNT); do
  curl -v 127.0.0.1:5500/
  curl -v 127.0.0.1:5500/error
done