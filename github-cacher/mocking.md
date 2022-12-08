# Mocking Network Requests
A writeup for an idea not yet implemented

## Introduction
During our work of caching Java artifacts, we find that network accesses are all
over the place. Even though we are able to solve a large part of them by 
the caching scripts (download dependencies through the build system) and
patching scripts (download files manually and change file location in the build
script), we cannot consider this a general solution for the problems of
reproducing artifacts that access the internet. Thus, a natural question come
into our mind is: is it possible to intercept all network traffic during a
build script and replay it when we are trying to reproduce the artifact?
Theoretically, this will make most images that are already reproducible to work
offline, which will help maintaining reproduciblity a lot.

## Technology Enablers

### Intercepting and Modifying Network Traffic
To be able to mock the Internet traffic, we need to be able to record the
network packets when running the build script and send it back to the artifact
when reproducing it.

* `tcpdump` can be used to intercept network packets, but AFAIK it cannot
  replace network packets.
* Docker supports the use of proxies. It works as adding environment variables
  like `HTTP_PROXY`. However, it is possible for the application to ignore this
  setting.
	* Proxy works for: curl, wget, apt-get, pip (probably: mvn, etc.)
	* Proxy does not work for: ping, nslookup
	* Ref: https://docs.docker.com/network/proxy/
	* Ref: https://docs.docker.com/config/daemon/systemd/#httphttps-proxy
	* Ref: https://docs.docker.com/config/containers/container-networking/
* It is possible to force all network requests to be proxied. This is done by
  transparent proxy servers (e.g. Squid) and firewall (iptables) forwarding.
  It also looks like that the proxy server need to run in another container.
	* Ref: https://github.com/silarsis/docker-proxy
	* Ref: https://gist.github.com/int128/aecad331dc66b2272bf0
* It is possible to write a Docker network plugin, but not sure whether it is
  useful:
  https://docs.docker.com/engine/extend/plugins_network/#write-a-network-plugin

### Encryption
Since a large number of network accesses are in HTTPS, we need to decrypt this
traffic. This is a trivial [Man-in-the-middle attack
](https://en.wikipedia.org/wiki/Man-in-the-middle_attack) model. However, the
difference is that we can control the HTTPS client and add a CA certificate to
it. So normally there will be no problem.

When performing a normal HTTP connection:
```
+-----------+                                                  +--------------+
| BugSwarm  |                        No                        |   GitHub     |
| Artifact  |                    Encryption                    |              |
|           | -----------------------------------------------> |              |
|           |                                                  |              |
|           |                                                  |              |
+-----------+                                                  +--------------+
```

When performing a normal HTTPS connection (ENC = Encryption, DEC = Decryption):
```
+-----------+--+                                            +--+--------------+
| BugSwarm  |  |                  GitHub's                  |  |   GitHub     |
| Artifact  | E|                 Encryption                 |D |              |
|           | N| -----------------------------------------> |E |              |
|           | C|                                            |C |              |
|GitHub's CA|  |                                            |  | GitHub's Key |
+-----------+--+                                            +--+--------------+
```

The system architecture will look like:
```
+-----------+--+            +--+-----------+--+             +--+--------------+
| BugSwarm  |  |  Proxy's   |  |   Proxy   |  |  GitHub's   |  |   GitHub     |
| Artifact  | E| Encryption |D |           | E| Encryption  |D |              |
|           | N| ---------> |E |           | N| ----------> |E |              |
|Proxy's CA | C|            |C |Proxy's Key| C|             |C |              |
|GitHub's CA|  |            |  |GitHub's CA|  |             |  | GitHub's Key |
+-----------+--+            +--+-----------+--+             +--+--------------+
```

Note that we need to install `Proxy's CA` in `BugSwarm Artifact`, or the
artifact will notice the man-in-the-middle attack. For example:
```
curl: (60) SSL certificate problem: self signed certificate
More details here: https://curl.haxx.se/docs/sslcerts.html

curl failed to verify the legitimacy of the server and therefore could not
establish a secure connection to it. To learn more about this situation and
how to fix it, please visit the web page mentioned above.
```

Since the proxy needs to be able to proxy all hosts, it should be able to sign
certificates automatically when it detects a new host name. See one of the
references below.

An alternative to installing the CA is probably to rewrite the libssl. However
it is too much of a project.

* Ref: https://stackoverflow.com/questions/50206936/how-can-i-disable-firefoxs-ssl-tls-certificate
* Ref: https://github.com/silarsis/docker-proxy#https-support

## Other Problems

### Understanding the Packets
Either automatically or manually, we need to be able to understand the packets
in order to cache them. The container is probably not going to send the exactly
same packages in the exactly same order, so we need to understand these
packages. For example:
* We need to keep track of the TCP connection states if working on packet level.
* For network accesses that download files, we should be able to extract the
  file and the corresponding URLs. If the URL contains something like a
  timestamp of the current time, we need to write a template that can match this
  URL. This is likely to be manual work.

### Artifacts not Covered
This method may not be able to cover some artifacts:
1. Artifacts that do not use the standard `libssl` for encrypted communication
   (should be uncommon).
2. Artifacts that access strange Internet addresses, which conflicts with the
   proxy server (maybe something like 172.17.0.2).
3. Artifacts that send random network packets that we cannot find a pattern
   (uncommon).
4. Artifacts that alter the firewall configurations during the build script
   (should be uncommon).

### Complexity of the Artifact
Another concern is that mocking the network may make the artifact too
complicated. BugSwarm is currently using containers, which already enclose a lot
of environments compared to other datasets. Virtual Machines may be able to make
it more reproducible (citation needed). If we use a machine emulator that
simulates all parts of the machine (e.g. network, time, random number
generation, context switches) deterministically, then all artifacts should be
100% reproducible. However, such an approach is too expensive.

For mocking the network, it looks like that the artifact will no longer be one
single Docker container. It may be a container and a set of files that will be
downloaded from the Proxy. It may be the a container (original artifact) and
another container of proxy (e.g. Squid). Any of those options will create an
overhead in time and storage when reproducing the artifact. The user also need
to perform Docker network configurations in the image.

## Why Should We Still Mock the Network
For tests that access the network, the only way to isolate them is to mock the
network. There are existing frameworks in the application level to implement
this (e.g. Python's [requests-mock](https://pypi.org/project/requests-mock/)).
However, if the project author did not use this framework, then we cannot mine
this project. This may further bias our dataset.

## Recommendations for Future Development
Personally, I recommend continue isolating the dependencies through downloading
files and modifying the build script. We should consider implementing mocking
the network requests for the testing phase. The amount of traffic mocked should
be small, and we can do some amount of manual work on
[Understanding the Packets](understanding-the-packets).

## See Also
* https://github.com/BugSwarm/bugswarm-dev/issues/252

