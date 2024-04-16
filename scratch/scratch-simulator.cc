/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <filesystem>

using namespace ns3;
using namespace ns3::SystemPath;

std::string dir;
float tputMeasureInterval = 0.02;
std::ofstream throughput;
std::ofstream queueSize;
std::ofstream lost;

uint32_t prev = 0;
Time prevTime = Seconds(0);

NS_LOG_COMPONENT_DEFINE("ScratchSimulator");

// Calculate throughput
static void
TraceThroughput(Ptr<FlowMonitor> monitor)
{
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
    if (!stats.empty())
    {
        auto itr = stats.begin();
        Time curTime = Now();
        throughput << Simulator::Now().GetSeconds() << " "
                   << 8 * (itr->second.txBytes - prev) / ((curTime - prevTime).ToDouble(Time::US))
                   << std::endl;
        lost << Simulator::Now().GetSeconds() << " " << itr->second.lostPackets << std::endl;
        prevTime = curTime;
        prev = itr->second.txBytes;
    }
    Simulator::Schedule(Seconds(tputMeasureInterval), &TraceThroughput, monitor);
}

// Check the queue size
void
CheckQueueSize(Ptr<QueueDisc> qd)
{
    uint32_t qsize = qd->GetCurrentSize().GetValue();
    Simulator::Schedule(Seconds(0.2), &CheckQueueSize, qd);
    queueSize << Simulator::Now().GetSeconds() << " " << qsize << std::endl;
}

// Trace congestion window
static void
CwndTracer(Ptr<OutputStreamWrapper> stream, uint32_t oldval, uint32_t newval)
{
    *stream->GetStream() << Simulator::Now().GetSeconds() << " " << newval / 1448.0 << std::endl;
}

void
TraceCwnd(uint32_t nodeId, uint32_t socketId)
{
    AsciiTraceHelper ascii;
    Ptr<OutputStreamWrapper> stream = ascii.CreateFileStream(dir + "/cwnd.dat");
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                      "/$ns3::TcpL4Protocol/SocketList/" +
                                      std::to_string(socketId) + "/CongestionWindow",
                                  MakeBoundCallback(&CwndTracer, stream));
}

/**
 * Trace queue drop.
 *
 * \param ofStream Output filestream.
 * \param item The dropped QueueDiscItem.
 */
void
TraceQueueDrop(std::ofstream* ofStream, Ptr<const QueueDiscItem> item)
{
    *ofStream << Simulator::Now().GetSeconds() << " " << std::hex << item->Hash() << std::endl;
}

void
ChangeBottleneckBw(std::string bw)
{
    NS_LOG_LOGIC("Changing bottleneck bandwidth to " << bw << " at "
                                                     << Simulator::Now().GetMilliSeconds() << "ms");
    Config::Set("/NodeList/2/DeviceList/1/$ns3::PointToPointNetDevice/DataRate", StringValue(bw));
    Config::Set("/NodeList/3/DeviceList/0/$ns3::PointToPointNetDevice/DataRate", StringValue(bw));
    // uint32_t sndBufSize = stoi(bw)*0.01/8;
    // NS_LOG_DEBUG("Setting sndBufSize to " << sndBufSize);
    // Config::Set("/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/SndBufSize",
    // UintegerValue(sndBufSize));
}

int
main(int argc, char* argv[])
{
    NS_LOG_UNCOND("Scratch Simulator for transformer-cc");
    LogComponentEnable("ScratchSimulator", LOG_LEVEL_DEBUG);
//    LogComponentEnable("BulkSendApplication", LOG_LEVEL_LOGIC);
    // LogComponentEnable("OnOffApplication", LOG_LEVEL_LOGIC);
    // LogComponentEnable("TcpSocketBase", LOG_LEVEL_DEBUG);
    // LogComponentEnable("TcpCubic", LOG_LEVEL_DEBUG);
    // LogComponentEnable("Ipv4FlowProbe", LOG_LEVEL_DEBUG);

    // Naming the output directory using local system time
    time_t rawtime;
    struct tm* timeinfo;
    char buffer[80];
    time(&rawtime);
    timeinfo = localtime(&rawtime);
    strftime(buffer, sizeof(buffer), "%d-%m-%Y-%I-%M-%S", timeinfo);
    std::string currentTime(buffer);

    std::string tcpTypeId = "TcpBbr";
    std::string queueDisc = "FifoQueueDisc";
    Time stopTime = Seconds(100);
    std::string oneWayDelay = "10ms";
    std::string traceFile = "/mydata/ns3-traces/test-1.log";

    CommandLine cmd(__FILE__);
    cmd.AddValue("tcpTypeId",
                 "Transport protocol to use: TcpNewReno, TcpLinuxReno, "
                 "TcpHybla, TcpHighSpeed, TcpHtcp, TcpVegas, TcpScalable, TcpVeno, "
                 "TcpBic, TcpYeah, TcpIllinois, TcpWestwoodPlus, TcpLedbat, "
                 "TcpLp, TcpDctcp, TcpCubic, TcpBbr",
                 tcpTypeId);
    cmd.AddValue("stopTime",
                 "Stop time for applications / simulation time will be stopTime + 1",
                 stopTime);
    cmd.AddValue("oneWayDelay",
                 "One way delay of the bottleneck link with units (e.g., 10ms)",
                 oneWayDelay);
    cmd.AddValue("tputMeasureInterval",
                 "Measurement interval for throughput measurement",
                 tputMeasureInterval);
    cmd.AddValue("traceFile", "File path for the bottleneck bandwidth trace", traceFile);
    cmd.Parse(argc, argv);
    NS_LOG_DEBUG("Using " << tcpTypeId << " as the transport protocol");

    queueDisc = std::string("ns3::") + queueDisc;

    Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::" + tcpTypeId));

    // The maximum send buffer size is set to 4194304 bytes (4MB) and the
    // maximum receive buffer size is set to 6291456 bytes (6MB) in the Linux
    // kernel. The same buffer sizes are used as default in this example.
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(41943040));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(62914560));
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1448));
    Config::SetDefault("ns3::DropTailQueue<Packet>::MaxSize", QueueSizeValue(QueueSize("1p")));
    Config::SetDefault(queueDisc + "::MaxSize", QueueSizeValue(QueueSize("800p")));
    Config::SetDefault("ns3::TcpSocketBase::UseEcn", StringValue("On"));
    // Config::SetDefault(queueDisc + "::UseEcn", BooleanValue(true));

    NodeContainer sender;
    NodeContainer receiver;
    NodeContainer routers;
    sender.Create(1);
    receiver.Create(1);
    routers.Create(2);
    NS_LOG_DEBUG("router 0 id: " << routers.Get(0)->GetId());
    NS_LOG_DEBUG("router 1 id: " << routers.Get(1)->GetId());

    // Create the point-to-point link helpers
    PointToPointHelper bottleneckLink;
    bottleneckLink.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
    bottleneckLink.SetChannelAttribute("Delay", StringValue(oneWayDelay));

    PointToPointHelper edgeLink;
    edgeLink.SetDeviceAttribute("DataRate", StringValue("1000Mbps"));
    edgeLink.SetChannelAttribute("Delay", StringValue("0ms"));

    // Create NetDevice containers
    NetDeviceContainer senderEdge = edgeLink.Install(sender.Get(0), routers.Get(0));
    NetDeviceContainer r1r2 = bottleneckLink.Install(routers.Get(0), routers.Get(1));
    NetDeviceContainer receiverEdge = edgeLink.Install(routers.Get(1), receiver.Get(0));

    // Install Stack
    InternetStackHelper internet;
    internet.Install(sender);
    internet.Install(receiver);
    internet.Install(routers);

    // Configure the root queue discipline
    TrafficControlHelper tch;
    tch.SetRootQueueDisc(queueDisc);

    // tch.Install(senderEdge);
    // tch.Install(receiverEdge);

    // Assign IP addresses
    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.0.0.0", "255.255.255.0");

    Ipv4InterfaceContainer i1i2 = ipv4.Assign(r1r2);

    ipv4.NewNetwork();
    Ipv4InterfaceContainer is1 = ipv4.Assign(senderEdge);

    ipv4.NewNetwork();
    Ipv4InterfaceContainer ir1 = ipv4.Assign(receiverEdge);

    // Populate routing tables
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // Select sender side port
    uint16_t port = 50001;

    // Install the OnOff application on the sender
    // BulkSendHelper source("ns3::TcpSocketFactory", InetSocketAddress(ir1.GetAddress(1), port));
    OnOffHelper source("ns3::TcpSocketFactory", InetSocketAddress(ir1.GetAddress(1), port));
    source.SetAttribute("OnTime", StringValue("ns3::NormalRandomVariable[Mean=1|Variance=0.1]"));
    // source.SetAttribute("OffTime",
    // StringValue("ns3::NormalRandomVariable[Mean=0.2|Variance=0.05]"));
    source.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"));
    // source.SetAttribute("SendSize", UintegerValue(25));
    source.SetAttribute("MaxBytes", UintegerValue(0));
    source.SetAttribute("DataRate", DataRateValue(DataRate("150Mbps")));
    source.SetAttribute("PacketSize", UintegerValue(1448));
    ApplicationContainer sourceApps = source.Install(sender.Get(0));
    sourceApps.Start(Seconds(0.1));
    // Hook trace source after application starts
    Simulator::Schedule(Seconds(0.1) + MilliSeconds(1), &TraceCwnd, 0, 0);
    sourceApps.Stop(stopTime);

    // Install application on the receiver
    PacketSinkHelper sink("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
    ApplicationContainer sinkApps = sink.Install(receiver.Get(0));
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(stopTime);

    // Create a new directory to store the output of the program
    dir = tcpTypeId + "-results/" + currentTime + "/";
    MakeDirectories(dir);
    NS_LOG_DEBUG("Using " << dir << " as the output directory");

    std::filesystem::copy("BBR-Validation/ns-3 scripts/PlotScripts/gnuplotScriptCwnd", dir);
    std::filesystem::copy("BBR-Validation/ns-3 scripts/PlotScripts/gnuplotScriptThroughput", dir);
    std::filesystem::copy("BBR-Validation/ns-3 scripts/PlotScripts/gnuplotScriptQueueSize", dir);
    std::filesystem::copy("BBR-Validation/ns-3 scripts/PlotScripts/gnuplotScriptLost", dir);

    // Trace the queue occupancy on the second interface of R1
    tch.Uninstall(routers.Get(0)->GetDevice(1));
    QueueDiscContainer qd;
    qd = tch.Install(routers.Get(0)->GetDevice(1));
    std::ofstream queueDropOfStream;
    queueDropOfStream.open(dir + "/queueDrop.dat", std::ofstream::out);
    qd.Get(0)->TraceConnectWithoutContext("Drop",
                                          MakeBoundCallback(&TraceQueueDrop, &queueDropOfStream));
    Simulator::ScheduleNow(&CheckQueueSize, qd.Get(0));

    // Open files for writing throughput traces and queue size
    throughput.open(dir + "/throughput.dat", std::ios::out);
    queueSize.open(dir + "/queueSize.dat", std::ios::out);
    lost.open(dir + "/lost.dat", std::ios::out);

    NS_ASSERT_MSG(throughput.is_open(), "Throughput file was not opened correctly");
    NS_ASSERT_MSG(queueSize.is_open(), "Queue size file was not opened correctly");
    NS_ASSERT_MSG(lost.is_open(), "Lost packets file was not opened correctly");

    /*Config::MatchContainer match = Config::LookupMatches("/NodeList/3/DeviceList/");
    if (match.GetN() != 0)
    {
        for (uint32_t i = 0; i < match.GetN(); i++)
        {
            Ptr<Object> n = match.Get(i);
            NS_LOG_DEBUG("Device " << i << " id: " <<
    n->GetObject<PointToPointNetDevice>()->GetNode()->GetId()); NS_LOG_DEBUG("Device " << i << "
    data rate: " << n->GetObject<PointToPointNetDevice>()->m_bps);
        }
    }
    else
    {
        NS_FATAL_ERROR("Lookup got no matches");
    }*/

    // Check for dropped packets using Flow Monitor
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll();
    // Ptr<FlowMonitor> monitor = flowmon.Install(routers);
    Simulator::Schedule(Seconds(0 + 0.000001), &TraceThroughput, monitor);

    flowmon.SerializeToXmlFile(dir + "/flowmon.xml", true, true);
    // Simulator::Schedule(Seconds(0 + 0.000001), &TraceDrop, monitor);

    std::ifstream trace(traceFile);
    int t, available_bw;
    while (trace >> t >> available_bw)
    {
        Simulator::Schedule(MilliSeconds(t - Simulator::Now().GetMilliSeconds()),
                            &ChangeBottleneckBw,
                            std::to_string(available_bw) + "bps");
    }

    Simulator::Stop(stopTime + TimeStep(1));
    Simulator::Run();
    Simulator::Destroy();

    throughput.close();
    queueSize.close();
    lost.close();

    return 0;
}
