# FprimeYamcsReference F´ project

This is a basic project that shows F Prime/YAMCS integration. It has two key features:

1. It uses `Drv.Udp` as the communication driver
2. It has YAMCS and F Prime/YAMCS packages in `requirements.txt`

## Building

Building is done in the standard F Prime way:

1. `fprime-util generate`
2. `fprime-util build`

## Running

To run, run `fprime-yamcs` and open `http://localhost:8090` in your browser!