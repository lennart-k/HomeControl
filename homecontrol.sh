#!/usr/bin/env sh

NAME="HomeControl"
DESC="Home Automation"
PID_FILE="$HOME/.homecontrol/homecontrol.pid"
START_PARAMS="-clearport -daemon -pid-file=$PID_FILE -kp"

#Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' #No Color

start() {
    cd $HOMECONTROL_PATH && homecontrol $START_PARAMS
    if [ $? -eq 0 ]
    then
        echo "HomeControl was ${GREEN}successfully${NC} started"
    else
        echo "${RED}Failed${NC} to start HomeControl"
    fi
}

stop() {
    if [ -e $PID_FILE ]
    then
        /bin/kill -s SIGINT $(cat $PID_FILE) > /dev/null 2>&1
        if [ $? -eq 0 ]
        then
            timeout 10 tail --pid=$(cat $PID_FILE) -f /dev/null > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                echo "HomeControl was ${GREEN}successfully${NC} stopped"
            else
                echo "${RED}Failed${NC} to stop HomeControl"
            fi
        else
            echo "HomeControl is ${YELLOW}already${NC} stopped"
        fi
    else
        echo "HomeControl is ${YELLOW}already${NC} stopped"
    fi
}

status() {
    if [ -e $PID_FILE ]
    then
        /bin/kill -0 $(cat $PID_FILE) > /dev/null 2>&1
        if [ $? -eq 0 ]
        then
            echo "Service is ${GREEN}running${NC}"
        else
            echo "HomeControl is ${RED}stopped${NC}"
        fi
    else
        echo "HomeControl is ${RED}stopped${NC}"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart|reload)
        stop
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 ${BLUE}{ start | stop | status | restart | reload }${NC}"
        exit 1
        ;;
esac

exit 0