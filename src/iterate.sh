#!/bin/bash

for number in {1..239}
do
    python gen_page.py $number
    sleep 0.1
done
exit 0
