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

std::string name;
float measureInterval = 0.02;
uint32_t packetSize = 1448.0;
std::ofstream throughput;
std::ofstream queueSize;
std::ofstream lost;
std::ofstream new_throughput;
std::ofstream output;
QueueDiscContainer qd;

uint32_t prev = 0;
Time prevTime = Seconds(0);
uint32_t currentCwnd = 0;
uint32_t ssThresh = 0;
// uint32_t g_firstBytesReceived = 0; //!< First received packet size.
double pacingRate = 0;
std::vector<uint64_t> delay;
uint32_t rto = 0;
uint32_t dropObserved = 0;
uint32_t markObserved = 0;
double queueLength = 0;
uint32_t bytesInFlight = 0;
SequenceNumber32 tx;
SequenceNumber32 unAck;

NS_LOG_COMPONENT_DEFINE("ScratchSimulator");

void
OutputStats()
{
    // double throughput = g_firstBytesReceived * 8 / measureInterval / 1e6;
    double avgDelay = accumulate(delay.begin(), delay.end(), 0.0) / delay.size();
    output << Simulator::Now().GetSeconds() << ", " << currentCwnd << ", " << ssThresh << ", " << pacingRate << ", " << avgDelay << ", " << rto << ", "
           << dropObserved << ", " << markObserved << ", " << queueLength << ", " << bytesInFlight
           << ", " << tx << ", " << unAck << std::endl;
    // g_firstBytesReceived = 0;
    delay.clear();
    dropObserved = 0;
    markObserved = 0;
    Simulator::Schedule(Seconds(measureInterval), &OutputStats);
}

/**
 * Trace receiver Rx bytes.
 *
 * \param packet The packet.
 * \param address The sender address.
 */
// void
// RecvTputTracer(Ptr<const Packet> packet, const Address& address)
// {
//     g_firstBytesReceived += packet->GetSize();
// }

// Trace congestion window
void
CwndTracer(uint32_t oldval, uint32_t newval)
{
    currentCwnd = newval / packetSize;
}

void
SsThreshTracer(uint32_t oldval, uint32_t newval)
{
    ssThresh = newval;
}

void
PacingRateTracer(DataRate oldValue, DataRate newValue)
{
    pacingRate = newValue.GetBitRate() / 1e6;
}

void
RttTracer(Time oldValue, Time newValue)
{
    delay.push_back(newValue.GetMilliSeconds());
}

void
RtoTracer(Time oldValue, Time newValue)
{
    rto = newValue.GetMilliSeconds();
}

void
DropTracer(std::ofstream* ofStream, Ptr<const QueueDiscItem> item)
{
    dropObserved++;
}

void
MarkTracer(std::ofstream* ofStream, Ptr<const QueueDiscItem> item, const char* reason)
{
    markObserved++;
}

void
QueueLengthTracer(uint32_t oldval, uint32_t newval)
{
    queueLength = newval;
}

void
InFlightTracer(uint32_t oldval, uint32_t newval)
{
    bytesInFlight = newval;
}

void
TxTracer(SequenceNumber32 old [[maybe_unused]], SequenceNumber32 nextTx)
{
    tx = nextTx;
}

void
UnAckTracer(SequenceNumber32 old [[maybe_unused]], SequenceNumber32 unAckSeq)
{
    unAck = unAckSeq;
}

void
ConnectTracer()
{
    Config::ConnectWithoutContextFailSafe(
        "/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/CongestionWindow",
        MakeBoundCallback(&CwndTracer));
    Config::ConnectWithoutContextFailSafe(
        "/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/SlowStartThreshold",
        MakeCallback(&SsThreshTracer));
    // Config::ConnectWithoutContextFailSafe("/NodeList/1/ApplicationList/*/$ns3::PacketSink/Rx",
    //                                       MakeCallback(&RecvTputTracer));
    Config::ConnectWithoutContextFailSafe("/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/PacingRate",
                                          MakeCallback(&PacingRateTracer));
    Config::ConnectWithoutContextFailSafe("/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/RTT",
                                          MakeCallback(&RttTracer));
    Config::ConnectWithoutContextFailSafe("/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/RTO",
                                          MakeCallback(&RtoTracer));
    Config::ConnectWithoutContextFailSafe(
        "/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/BytesInFlight",
        MakeCallback(&InFlightTracer));
    Config::ConnectWithoutContextFailSafe(
        "/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/NextTxSequence",
        MakeCallback(&TxTracer));
    Config::ConnectWithoutContextFailSafe(
        "/NodeList/0/$ns3::TcpL4Protocol/SocketList/0/TxBuffer/UnackSequence",
        MakeCallback(&UnAckTracer));
}

void
ChangeBottleneckBw(std::string bw, Ptr<QueueDisc> qd)
{
    NS_LOG_LOGIC("Changing bottleneck bandwidth to " << bw << " at "
                                                     << Simulator::Now().GetMilliSeconds() << "ms");
    Config::Set("/NodeList/2/DeviceList/1/$ns3::PointToPointNetDevice/DataRate", StringValue(bw));
    Config::Set("/NodeList/3/DeviceList/0/$ns3::PointToPointNetDevice/DataRate", StringValue(bw));
    int bandwidth = std::stoi(bw); // Convert string to integer
    int queueSize = static_cast<int>(std::floor((bandwidth * 20.0) / 1000.0 / 1448.0 / 8.0));
    qd->SetAttribute("MaxSize", QueueSizeValue(QueueSize(std::to_string(queueSize)+"p")));
    NS_LOG_LOGIC("Queue size set to " << queueSize);
}

int
main(int argc, char* argv[])
{
    LogComponentEnable("ScratchSimulator", LOG_LEVEL_LOGIC);
    // LogComponentEnable("BulkSendApplication", LOG_LEVEL_LOGIC);
    // LogComponentEnable("OnOffApplication", LOG_LEVEL_DEBUG);
    LogComponentEnable("TcpSocketBase", LOG_LEVEL_LOGIC);
    // LogComponentEnable("TcpL4Protocol", LOG_LEVEL_LOGIC);
    LogComponentEnable("FifoQueueDisc", LOG_LEVEL_LOGIC);
    // LogComponentEnable("TcpRxBuffer", LOG_LEVEL_LOGIC);
    // LogComponentEnable("PacketSink", LOG_LEVEL_LOGIC);
    // LogComponentEnable("Socket", LOG_LEVEL_LOGIC);
    // LogComponentEnable("Ipv4RawSocketImpl", LOG_LEVEL_LOGIC);
    LogComponentEnable("PointToPointNetDevice", LOG_LEVEL_LOGIC);
    LogComponentEnable("QueueDisc", LOG_LEVEL_LOGIC);
    LogComponentEnable("DataRate", LOG_LEVEL_LOGIC);
    // NS_LOG_UNCOND("Scratch Simulator for transformer-cc");
    // LogComponentEnable("ScratchSimulator", LOG_LEVEL_DEBUG);
    // LogComponentEnable("BulkSendApplication", LOG_LEVEL_LOGIC);
    // LogComponentEnable("OnOffApplication", LOG_LEVEL_DEBUG);
    // LogComponentEnable("TcpSocketBase", LOG_LEVEL_DEBUG);
    // LogComponentEnable("TcpCubic", LOG_LEVEL_FUNCTION);
    // LogComponentEnable("Ipv4FlowProbe", LOG_LEVEL_DEBUG);
    // LogComponentEnable("TcpDctcp", LOG_LEVEL_INFO);
    // LogComponentEnable("TcpCongestionOps", LOG_LEVEL_FUNCTION);

    // Naming the output directory using local system time
    time_t rawtime;
    struct tm* timeinfo;
    char buffer[80];
    time(&rawtime);
    timeinfo = localtime(&rawtime);
    strftime(buffer, sizeof(buffer), "%d-%m-%Y-%I-%M-%S", timeinfo);
    std::string currentTime(buffer);

    std::string tcpTypeId = "TcpNewReno";
    std::string queueType = "FifoQueueDisc";
    std::string onTimeMean = "15";
    std::string onTimeVar = "0.1";
    std::string offTimeMean = "0.2";
    std::string offTimeVar = "0.05";
    Time stopTime = Seconds(10);
    std::string oneWayDelay = "10ms";
    bool queueUseEcn = false;
    Time ceThreshold = MilliSeconds(1);
    std::string traceFile = "./test-trace";
    std::string outputDir = "./results/";
    int startLine = 0;
    uint32_t runNum = 0;
    uint32_t initialCwnd = 10;
    bool isSecondPolicy = false;

    // Cubic parameters
    double beta = 0.7;
    double cubicC = 0.4;

    // NewReno parameters
    double alpha = 1;
    uint32_t renoBeta = 2;

    CommandLine cmd(__FILE__);
    cmd.AddValue("tcpTypeId",
                 "Transport protocol to use: TcpLinuxReno, TcpVegas, TcpDctcp, TcpCubic, TcpBbr",
                 tcpTypeId);
    cmd.AddValue("queueType",
                 "bottleneck queue type to use: CoDelQueueDisc, FqCoDelQueueDisc",
                 queueType);
    cmd.AddValue("stopTime",
                 "Stop time for applications / simulation time will be stopTime + 1",
                 stopTime);
    cmd.AddValue("onTimeMean", "Mean on time for OnOff application in seconds", onTimeMean);
    cmd.AddValue("onTimeVar", "Variance of on time for OnOff application in seconds", onTimeVar);
    cmd.AddValue("offTimeMean", "Mean off time for OnOff application in seconds", offTimeMean);
    cmd.AddValue("offTimeVar", "Variance of off time for OnOff application in seconds", offTimeVar);
    cmd.AddValue("oneWayDelay",
                 "One way delay of the bottleneck link with units (e.g., 10ms)",
                 oneWayDelay);
    cmd.AddValue("ceThreshold", "CoDel CE threshold (for DCTCP)", ceThreshold);
    cmd.AddValue("packetSize", "Packet size in bytes (default 1448)", packetSize);
    cmd.AddValue("measureInterval",
                 "Measurement interval for output stats in seconds (default 0.02)",
                 measureInterval);
    cmd.AddValue("traceFile", "File path for the bottleneck bandwidth trace", traceFile);
    cmd.AddValue("outputDir", "output directory path", outputDir);
    cmd.AddValue("queueUseEcn", "use ECN on queue", queueUseEcn);
    cmd.AddValue("startLine", "start line of the trace file", startLine);
    cmd.AddValue("beta", "Cubic beta parameter for multiplicative decrease", beta);
    cmd.AddValue("cubicC", "Cubic scaling factor", cubicC);
    cmd.AddValue("alpha", "NewReno alpha parameter for additive increase", alpha);
    cmd.AddValue("renoBeta", "NewReno beta parameter for multiplicative decrease", renoBeta);
    cmd.AddValue("runNum", "Run number for randomness seed", runNum);
    cmd.AddValue("initialCwnd", "Initial congestion window size", initialCwnd);
    cmd.AddValue("isSecondPolicy", "Whether the current simulation is running the second policy in a policy switch", isSecondPolicy);
    cmd.Parse(argc, argv);
    NS_LOG_DEBUG("Using " << tcpTypeId << " as the transport protocol");

    ns3::RngSeedManager::SetRun(runNum);
    queueType = std::string("ns3::") + queueType;

    MakeDirectories(outputDir);
    std::string inputName = traceFile;
    inputName.erase(0, 1);
    for (int i = 0; i < 4; ++i)
    {
        inputName.erase(0, inputName.find("/") + 1);
    }
    NS_LOG_DEBUG("inputName: " << inputName);
    if (tcpTypeId == "TcpCubic")
    {
        name = tcpTypeId + '-' + std::to_string(beta) + '-' + std::to_string(cubicC) + '-' +
               onTimeMean + '-' + onTimeVar + '-' + offTimeMean + '-' + offTimeVar + '-' +
               currentTime + '-' + std::to_string(startLine) + '-' + inputName;
    } else if (tcpTypeId == "TcpNewReno") {
        name = tcpTypeId + '-' + std::to_string(alpha) + '-' + std::to_string(renoBeta) + '-' +
               onTimeMean + '-' + onTimeVar + '-' + offTimeMean + '-' + offTimeVar + '-' +
               currentTime + '-' + std::to_string(startLine) + '-' + inputName;
    }
    else
        name = tcpTypeId + '-' + onTimeMean + '-' + onTimeVar + '-' + offTimeMean + '-' +
               offTimeVar + '-' + currentTime + '-' + std::to_string(startLine) + '-' + inputName;

    Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::" + tcpTypeId));

    // The maximum send buffer size is set to 41943040 bytes (40MB) and the
    // maximum receive buffer size is set to 62914560 bytes (60MB) in the Linux
    // kernel. The same buffer sizes are used as default in this example.
    Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(41943040));
    Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(62914560));
    Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(initialCwnd));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(packetSize));
    Config::SetDefault("ns3::TcpCubic::Beta", DoubleValue(beta));
    Config::SetDefault("ns3::TcpCubic::C", DoubleValue(cubicC));
    Config::SetDefault("ns3::TcpNewReno::RenoAlpha", DoubleValue(alpha));
    Config::SetDefault("ns3::TcpNewReno::RenoBeta", UintegerValue(renoBeta));
    Config::SetDefault("ns3::TcpRxBuffer::TputOutputPath", StringValue(outputDir + name +"-tput"));

    // Enable TCP to use ECN regardless
    Config::SetDefault("ns3::TcpSocketBase::UseEcn", StringValue("Off"));

    Config::SetDefault("ns3::DropTailQueue<Packet>::MaxSize", QueueSizeValue(QueueSize("1p")));
    Config::SetDefault(queueType + "::MaxSize", QueueSizeValue(QueueSize("20p")));

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
    edgeLink.SetDeviceAttribute("DataRate", StringValue("500Mbps"));
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
    tch.SetRootQueueDisc(queueType);
    tch.SetQueueLimits("ns3::DynamicQueueLimits", "HoldTime", StringValue("1ms"));

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
    OnOffHelper source("ns3::TcpSocketFactory", InetSocketAddress(ir1.GetAddress(1), port));
    source.SetAttribute("OnTime",
                        StringValue("ns3::NormalRandomVariable[Mean=" + onTimeMean +
                                    "|Variance=" + onTimeVar + "]"));
    source.SetAttribute("OffTime",
                        StringValue("ns3::NormalRandomVariable[Mean=" + offTimeMean +
                                    "|Variance=" + offTimeVar + "]"));
    source.SetAttribute("MaxBytes", UintegerValue(0));
    source.SetAttribute("DataRate", DataRateValue(DataRate("250Mb/s")));
    source.SetAttribute("PacketSize", UintegerValue(1448));
    ApplicationContainer sourceApps = source.Install(sender.Get(0));
    sourceApps.Start(Seconds(0.1));
    // Hook trace source after application starts
    Simulator::Schedule(Seconds(0.1) + MilliSeconds(1), &ConnectTracer);
    sourceApps.Stop(stopTime);

    // Install application on the receiver
    PacketSinkHelper sink("ns3::TcpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
    ApplicationContainer sinkApps = sink.Install(receiver.Get(0));
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(stopTime);

    // Trace the queue occupancy on the second interface of R1
    tch.Uninstall(routers.Get(0)->GetDevice(1));

    qd = tch.Install(routers.Get(0)->GetDevice(1));
    std::ofstream queueDropOfStream;
    qd.Get(0)->TraceConnectWithoutContext("Drop",
                                          MakeBoundCallback(&DropTracer, &queueDropOfStream));
    qd.Get(0)->TraceConnectWithoutContext("Mark",
                                          MakeBoundCallback(&MarkTracer, &queueDropOfStream));
    qd.Get(0)->TraceConnectWithoutContext("PacketsInQueue", MakeCallback(&QueueLengthTracer));

    // Open files for writing outputs
    output.open(outputDir + name, std::ios::out);

    output << "Time, currentCwnd, ssThres, pacingRate, avgDelay, rto, dropObserved, "
              "markObserved, "
              "queueLength, bytesInFlight, tx, unAck"
           << std::endl;
    Simulator::Schedule(Seconds(measureInterval), &OutputStats);

    NS_LOG_DEBUG("traceFile: " << traceFile);
    std::ifstream trace(traceFile);
    int t, available_bw;
    trace.seekg(std::ios::beg);
    for (int i = 0; i < startLine - 1; ++i)
    {
        trace.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    }
    int start_t = -1;
    while (trace >> t >> available_bw)
    {
        if (start_t == -1)
        {
            start_t = t;
        }
        Simulator::Schedule(MilliSeconds(t - start_t - Simulator::Now().GetMilliSeconds()),
                            &ChangeBottleneckBw,
                            std::to_string(available_bw) + "bps", qd.Get(0));
    }

    Simulator::Stop(stopTime + TimeStep(1));
    Simulator::Run();
    Simulator::Destroy();

    output.close();

    return 0;
}
