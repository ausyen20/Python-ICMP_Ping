ICMP Ping and Traceroute
-> I used python to create ICMP ping and Traceroute function

ICMP ping:
Methods used: ping, sendOnePing, doOneping, receiveOnePing
-> Uses the ping method to get the host
-> SendOne ping creates the socket, use the socket to doOne ping , and receiveOne ping returns the total delay from Host to Host

Traceroute:
Similar to traceroute on any Operating System, where it creates packet and path from source to destination. (Via routers between source and destination)
It displays round-trip latency from the source to each of the routers.
TTL (Time to Live) increments after each hops, up to 30. If packet does not reach, request type (timeout) will be thrown, and also computer latency.
For each TTL, the program will also send three pings (or packets), to check average latency from source to that specific address.