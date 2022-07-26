from numpy import NAN
from scapy.all import *
from scapy.layers.inet import *
import pandas as pd
import time
from stage1 import FlowDfGenerator


def sniff_packet_df(sniff_if, sniff_filter='ip', sniff_timeout=1):
    # capture = sniff(iface='wlp3s0', filter='ip', count=1000)
    capture = sniff(iface=sniff_if, filter=sniff_filter, timeout=sniff_timeout)
    # print(capture.summary())

    packet_list = []
    for packet in capture:
        p = dict()
        p['type'] = 'TCP' if TCP in packet else \
            'UDP' if UDP in packet else \
            'IP' if IP in packet else \
            'None'
        if p['type'] == 'None':
            continue
        elif p['type'] == 'TCP':
            p['Source_Port'] = packet['TCP'].sport
            p['Destination_Port'] = packet['TCP'].dport
        elif p['type'] == 'UDP':
            p['Source_Port'] = packet['UDP'].sport
            p['Destination_Port'] = packet['UDP'].dport
        else:
            p['Source_Port'] = NAN
            p['Destination_Port'] = NAN

        p['Time'] = packet.time - CURR_EPOCH_TIME
        p['Source_ip'] = packet['IP'].src
        p['Destination_IP'] = packet['IP'].dst
        p['Frame_length'] = len(packet['IP'])

        packet_list.append(p)

    return pd.DataFrame(packet_list)[["Time", "Source_ip", 'Source_Port', 'Destination_IP',
                                      'Destination_Port', 'Frame_length']]


CURR_EPOCH_TIME = int(time.time())
flow_df_generator = FlowDfGenerator()
flow_df = pd.DataFrame()
while True:
    packet_df = sniff_packet_df('lo')
    # print(packet_df)
    flow_df = pd.concat([flow_df, flow_df_generator.generate_flow_dataframe(
        packet_df, chunk_size=20, is_labeled=False)])
    print(flow_df)
    if len(flow_df) > 3000:
        break

# saving
flow_df.to_csv('output1.csv', index=False)
plt.plot(flow_df['Mean_Time'], flow_df['SSIP'], color="green")
plt.plot(flow_df['Mean_Time'], flow_df['SSP'], color="red")
plt.show()
plt.plot(flow_df['Mean_Time'], flow_df['SDFB'], color="blue")
plt.show()
plt.plot(flow_df['Mean_Time'], flow_df['SFE'], color="yellow")
plt.show()
plt.plot(flow_df['Mean_Time'], flow_df['RPF'], color="purple")
plt.show()
# plt.plot(flow_df['Mean_Time'], flow_df['Traffic_Type'], color="orange")
# plt.show()
# print(df)

# print('got 2000 packets')
# for packet in capture:
#     print(packet.summary())
#     # print(packet['IP'].src)
#     # print(packet.time)
#     # print(len(packet['IP']))
#     # print('******************************')

# # wrpcap("packets.pcap", capture)
