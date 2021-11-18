#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
"$DIR/build.sh"

docker run -it --rm --cpuset-cpus 0 --net=host -v $1:/root -v $DIR/..:/botsrc redditmodbot /startup.sh
