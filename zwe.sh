#!/bin/bash

sleep=60
username=""
password=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    -sleep)
        sleep="$2"
        shift
        ;;
    -u)
        username="$2"
        shift
        ;;
    -p)
        password="$2"
        shift
        ;;
    -n)
        notify="$2"
        shift
        ;;
    *)
        echo "Invalid option: $1" 1>&2
        exit 1
        ;;
    esac
    shift
done

GetJwt() {
    local TOKENURL="https://api-my.te.eg/api/user/generatetoken?channelId=WEB_APP"
    local LOGINURL="https://api-my.te.eg/api/user/login?channelId=WEB_APP"

    local token_response=$(curl -q -s -X GET \
        -H "Host: api-my.te.eg" \
        -H "Accept: application/json, text/plain, */*" \
        -H "Connection: close" \
        "$TOKENURL")

    local first_jwt=$(echo "$token_response" | jq -r '.body.jwt')

    local login_response=$(curl -s -X POST "$LOGINURL" \
        -H "Accept: application/json, text/plain, */*" \
        -H "Content-Type: application/json" \
        -H "Jwt: \"$first_jwt\"" \
        -H "Connection: close" \
        -d "{\"header\":{\"msisdn\":\"$username\",\"numberServiceType\":\"FBB\",\"timestamp\":\"$(date +%s)\",\"locale\":\"en\"},\"body\":{\"password\":\"$password\"}}")

    echo $(echo "$login_response" | jq -r '.body.jwt')
}

while true; do
    jwt=$(GetJwt)

    # response=$(curl -s http://worldtimeapi.org/api/timezone/Africa/Cairo)
    # timezone=$(echo "$response" | jq -r '.datetime' | cut -c 9-16)

    usage_info=$(curl -s -X POST \
        https://api-my.te.eg/api/line/freeunitusage \
        -H "Accept: application/json, text/plain, */*" \
        -H "Jwt: $jwt" \
        -H "Content-Type: application/json" \
        -H "Connection: close" \
        --data "{\"header\":{\"customerId\":\"1111111111111111\",\"msisdn\":\"$username\",\"numberServiceType\":\"FBB\",\"locale\":\"en\"}}")

    usage_percentage=$(echo "$usage_info" | jq -r '.body.detailedLineUsageList[0].usagePercentage')
    free_amount=$(echo "$usage_info" | jq -r '.body.detailedLineUsageList[0].freeAmount')

    message="**$timezone** => **$usage_percentage%** => **$free_amount GB** remaining."

    if [ -n "$notify" ]; then
        echo "$message" | notify -silent -id $notify
    else
        echo "$message"
    fi

    sleep "$sleep"
done
