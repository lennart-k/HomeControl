#!/usr/bin/env bash

NAME="HomeControl"
DESC="Home Automation"
PID_FILE="/tmp/homecontrol.pid"
START_PARAMS="-clearport -daemon -pid-file $PID_FILE"

# Fill in your path
HOMECONTROL_PATH="./"

#Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' #No Color

start() {
    case $(cd $HOMECONTROL_PATH && exec python3.7 homecontrol $START_PARAMS) in
        0)
            echo -e "HomeControl was ${GREEN}successfully${NC} started"
            ;;
        1)
            echo -e "${RED}Failed${NC} to start HomeControl"
            ;;
    esac
}

stop() {
    case $(/bin/cat $PID_FILE &> /dev/null) in
        0)
            case $(kill -s SIGINT $(cat $PID_FILE) > /dev/null 2>&1) in 
                0)        
                    if [ $(timeout 10 tail --pid=$(cat $PID_FILE) -f /dev/null > /dev/null 2>&1) -eq 0 ]
                        then
                            echo -e "Service was ${GREEN}successfully${NC} stopped"
                        else
                            echo -e "${RED}Failed${NC} to stop HomeControl"
                        fi
                        ;;
                *)
                    echo -e "HomeControl is ${YELLOW}already${NC} stopped"
                    ;;
            esac
            ;;
        *)
            echo -e "HomeControl is ${YELLOW}already${NC} stopped"
            ;;
    esac
    
}

status() {
    case $(/bin/cat $PID_FILE &> /dev/null) in
        0)
            case $(kill -n 0 $(cat $PID_FILE) > /dev/null 2>&1) in
                0)
                    echo -e "Service is ${GREEN}running${NC}"
                    ;;
                *)
                    echo -e "HomeControl is ${RED}stopped${NC}"
                    ;;
            esac
            ;;
        *)
            echo -e "HomeControl is ${RED}stopped${NC}"
            ;;
    esac
            
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
        echo " Usage: $0 ${BLUE}{ start | stop | status | restart | reload }${NC}"
        exit 1
        ;;
esac

exit 0