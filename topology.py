import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller
from comnetsemu.cli import CLI, spawnXtermDocker


def testTopo():
    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    server = net.addDockerHost(
        "server",
        dimage="ebpf-server",
        ip="11.0.1.1",
        docker_args={"hostname": "server"},
    )
    client1 = net.addDockerHost(
        "client1",
        dimage="ebpf-client",
        ip="10.0.0.1",
        docker_args={"hostname": "client1"},
    )
    client2 = net.addDockerHost(
        "client2",
        dimage="ebpf-client",
        ip="10.0.0.2",
        docker_args={"hostname": "client2"},
    )
    client3 = net.addDockerHost(
        "client3",
        dimage="ebpf-client",
        ip="10.0.0.3",
        docker_args={"hostname": "client3"},
    )
    client4 = net.addDockerHost(
        "client4",
        dimage="ebpf-client",
        ip="11.0.0.4",
        docker_args={"hostname": "client4"},
    )
    client5 = net.addDockerHost(
        "client5",
        dimage="ebpf-client",
        ip="11.0.0.5",
        docker_args={"hostname": "client5"},
    )
    attacker = net.addDockerHost(
        "attacker",
        dimage="ebpf-attacker",
        ip="10.0.0.6",
        docker_args={"hostname": "attacker"},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, server, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client4, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client5, bw=10, delay="10ms")

    net.addLinkNamedIfce(s2, server, bw=10, delay="10ms")
    net.addLinkNamedIfce(s2, client1, bw=10, delay="10ms")
    net.addLinkNamedIfce(s2, client2, bw=10, delay="10ms")
    net.addLinkNamedIfce(s2, client3, bw=10, delay="10ms")
    net.addLinkNamedIfce(s2, attacker, bw=10, delay="10ms")

    info("*** assigning ip to server's second interface\n")
    intf = server.intf('server-s2')
    intf.setIP('10.0.1.1/8')

    info("*** Starting network\n")
    net.start()

    # info("*** testing connections before xdpfw:\n")
    # test_connection(client1, "10.0.1.1", 3)
    # test_connection(client2, "10.0.1.1", 3)
    # test_connection(client3, "10.0.1.1", 3)
    # test_connection(attacker, "10.0.1.1", 3)
    # test_connection(client4, "11.0.1.1", 3)
    # test_connection(client5, "11.0.1.1", 3)
    
    info("*** initiating legit traffic\n")
    server.cmd("python3 /app_ddos_detection/echo_server/server.py --ip 10.0.1.1 --port 60000 &")
    client1.cmd("python3 /app/client.py --ip 10.0.1.1 --port 60000 -t client1_text &")
    client2.cmd("python3 /app/client.py --ip 10.0.1.1 --port 60000 -t client2 &")
    client3.cmd("python3 /app/client.py --ip 10.0.1.1 --port 60000 -t c3 &")
    server.cmd("python3 /app_ddos_detection/echo_server/server.py --ip 11.0.1.1 --port 60001 &")
    client4.cmd("python3 /app/client.py --ip 11.0.1.1 --port 60001 -t some_random_text_by_c4 &")

    info("*** running xdpfw on both interfaces\n")
    server.cmd("cd /app_xdp_fw/ && make && make install")
    server.cmd("xdpfw --config /etc/xdpfw/xdpfw.conf.s1 &")
    server.cmd("xdpfw --config /etc/xdpfw/xdpfw.conf.s2 &")

    # info("*** testing connections after xdpfw:\n")
    # test_connection(client1, "10.0.1.1", 3)
    # test_connection(client2, "10.0.1.1", 3)
    # test_connection(client3, "10.0.1.1", 3)
    # test_connection(attacker, "10.0.1.1", 3)
    # test_connection(client4, "11.0.1.1", 3)
    # test_connection(client5, "11.0.1.1", 3)

    info("*** running ddos detection on both interfaces\n")
    server.cmd("cd /app_ddos_detection")
    server.cmd(
        "printf -- '#!/bin/bash\n" +
        "python3 /app_ddos_detection/sniff.py -if server-s1 --conf-path /etc/xdpfw/xdpfw.conf.s1 --ml-model dt_model.pkl --operate\n' > ddd_s1.sh;" +
        "chmod +x ddd_s1.sh; ./ddd_s1.sh &")
    server.cmd(
        "printf -- '#!/bin/bash\n" +
        "python3 /app_ddos_detection/sniff.py -if server-s2 --conf-path /etc/xdpfw/xdpfw.conf.s2 --ml-model dt_model.pkl --operate\n' > ddd_s2.sh;" +
        "chmod +x ddd_s2.sh; ./ddd_s2.sh &")

    info("*** generating flood script for attacker\n")
    attacker.cmd(
        "printf -- '#!/bin/bash\n" +
        "python3 /traffic_generator/traffic_generator.py --interval 0.001 -if attacker-s2 -v \n' > flood_s2.sh;" +
        "chmod +x flood_s2.sh;")

    spawnXtermDocker("server")
    spawnXtermDocker("attacker")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

def test_connection(source_container, target_ip, ping_count=10):
    info(f"*** {source_container.docker_args['hostname']} --> {target_ip}\n")
    info("* Ping test count: %d" % ping_count)
    ret = source_container.cmd("ping -c " + str(ping_count) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    info("* Measured loss rate: {:.2f}%\n".format(measured))


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
