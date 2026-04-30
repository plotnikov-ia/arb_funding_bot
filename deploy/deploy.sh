#!/bin/bash

sudo ln -sf $(pwd)/deploy/arb_funding_bot.service /etc/systemd/system/arb_funding_bot.service
sudo systemctl daemon-reload
sudo systemctl restart arb_funding_bot