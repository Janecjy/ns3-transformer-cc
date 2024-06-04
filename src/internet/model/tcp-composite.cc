#include "tcp-composite.h"

#include "ns3/log.h"
#include "ns3/string.h"
#include "ns3/simulator.h"

NS_LOG_COMPONENT_DEFINE("TcpComposite");

namespace ns3
{

NS_OBJECT_ENSURE_REGISTERED(TcpComposite);

TypeId
TcpComposite::GetTypeId()
{
    static TypeId tid = TypeId("ns3::TcpComposite")
                            .SetParent<TcpCongestionOps>()
                            .SetGroupName("Internet")
                            .AddConstructor<TcpComposite>()
                            .AddAttribute("SwitchTime",
                                          "Time to switch to the new policy in seconds",
                                          UintegerValue(5),
                                          MakeUintegerAccessor(&TcpComposite::m_switchTime),
                                          MakeUintegerChecker<uint32_t>())
                            .AddAttribute("FirstPolicyName",
                                          "First policy to use for congestion control",
                                          StringValue("TcpNewReno"),
                                          MakeStringAccessor(&TcpComposite::m_policyFirst),
                                          MakeStringChecker())
                            .AddAttribute("FirstPolicyFirstParameter",
                                          "First parameter for the first policy",
                                          DoubleValue(1),
                                          MakeDoubleAccessor(&TcpComposite::m_firstParFirst),
                                          MakeDoubleChecker<double>())
                            .AddAttribute("FirstPolicySecondParameter",
                                          "Second parameter for the first policy",
                                          DoubleValue(2),
                                          MakeDoubleAccessor(&TcpComposite::m_secondParFirst),
                                          MakeDoubleChecker<double>())
                            .AddAttribute("SecondPolicyName",
                                          "Second policy to use for congestion control",
                                          StringValue("TcpNewReno"),
                                          MakeStringAccessor(&TcpComposite::m_policySecond),
                                          MakeStringChecker())
                            .AddAttribute("SecondPolicyFirstParameter",
                                          "First parameter for the second policy",
                                          DoubleValue(10),
                                          MakeDoubleAccessor(&TcpComposite::m_firstParSecond),
                                          MakeDoubleChecker<double>())
                            .AddAttribute("SecondPolicySecondParameter",
                                          "Second parameter for the second policy",
                                          DoubleValue(20),
                                          MakeDoubleAccessor(&TcpComposite::m_secondParSecond),
                                          MakeDoubleChecker<double>());
    return tid;
}

TcpComposite::TcpComposite()
    : TcpCongestionOps()
{
    NS_LOG_FUNCTION(this);
}

TcpComposite::TcpComposite(const TcpComposite& sock)
    : TcpCongestionOps(sock)
{
    NS_LOG_FUNCTION(this);
}

TcpComposite::~TcpComposite()
{
}

uint32_t
TcpComposite::SlowStart(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    NS_LOG_FUNCTION(this << tcb << segmentsAcked);
    if (segmentsAcked >= 1)
    {
        tcb->m_cWnd += m_firstPar * tcb->m_segmentSize;
        NS_LOG_INFO("In SlowStart, updated to cwnd " << tcb->m_cWnd << " ssthresh "
                                                     << tcb->m_ssThresh);
        return segmentsAcked - 1;
    }

    return 0;
}

void
TcpComposite::CongestionAvoidance(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    NS_LOG_FUNCTION(this << tcb << segmentsAcked);

    if (segmentsAcked > 0)
    {
        double adder =
            static_cast<double>(tcb->m_segmentSize * tcb->m_segmentSize) / tcb->m_cWnd.Get();
        adder = std::max(1.0, adder);
        tcb->m_cWnd += m_firstPar * static_cast<uint32_t>(adder);
        NS_LOG_INFO("In CongAvoid, updated to cwnd " << tcb->m_cWnd << " ssthresh "
                                                     << tcb->m_ssThresh);
    }
}

void
TcpComposite::IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    NS_LOG_FUNCTION(this << tcb << segmentsAcked);
    if (tcb->m_cWnd < tcb->m_ssThresh)
    {
        segmentsAcked = SlowStart(tcb, segmentsAcked);
    }

    if (tcb->m_cWnd >= tcb->m_ssThresh)
    {
        CongestionAvoidance(tcb, segmentsAcked);
    }
}

void TcpComposite::Init(Ptr<TcpSocketState> tcb)
{
    NS_LOG_FUNCTION(this << tcb);
    SetPolicy(m_policyFirst);
    SetFirstPar(m_firstParFirst);
    SetSecondPar(m_secondParFirst);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::SetPolicy, this, m_policySecond);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::SetFirstPar, this, m_firstParSecond);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::SetSecondPar, this, m_secondParSecond);
}

std::string
TcpComposite::GetName() const
{
    NS_LOG_DEBUG("Policy name: " << m_policy << ", first parameter: " << m_firstPar
                                 << ", second parameter: " << m_secondPar);
    return m_policy;
}

void
TcpComposite::SetPolicy(std::string policy)
{
    NS_LOG_DEBUG("Setting policy to " << policy);
    m_policy = policy;
}

void
TcpComposite::SetFirstPar(double firstPar)
{
    NS_LOG_DEBUG("Setting first parameter to " << firstPar);
    m_firstPar = firstPar;
}

void
TcpComposite::SetSecondPar(double secondPar)
{
    NS_LOG_DEBUG("Setting second parameter to " << secondPar);
    m_secondPar = secondPar;
}

uint32_t
TcpComposite::GetSsThresh(Ptr<const TcpSocketState> state, uint32_t bytesInFlight)
{
    NS_LOG_FUNCTION(this << state << bytesInFlight);
    return std::max(2 * state->m_segmentSize, bytesInFlight / uint32_t(m_secondPar));
}

Ptr<TcpCongestionOps>
TcpComposite::Fork()
{
    return CopyObject<TcpComposite>(this);
}

} // namespace ns3