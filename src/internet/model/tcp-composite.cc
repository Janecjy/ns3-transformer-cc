#include "tcp-composite.h"

#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/string.h"

NS_LOG_COMPONENT_DEFINE("TcpComposite");

namespace ns3
{

NS_OBJECT_ENSURE_REGISTERED(TcpComposite);

TypeId
TcpComposite::GetTypeId()
{
    static TypeId tid =
        TypeId("ns3::TcpComposite")
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
                          MakeDoubleChecker<double>())
            .AddAttribute("SecondCwndDiff",
                          "Difference between the cwnd of the two policies",
                          IntegerValue(0),
                          MakeIntegerAccessor(&TcpComposite::m_secondCwndDiff),
                          MakeIntegerChecker<int>())
            .AddAttribute("FastConvergence",
                          "Enable (true) or disable (false) fast convergence",
                          BooleanValue(true),
                          MakeBooleanAccessor(&TcpComposite::m_fastConvergence),
                          MakeBooleanChecker())
            .AddAttribute("TcpFriendliness",
                          "Enable (true) or disable (false) TCP friendliness",
                          BooleanValue(true),
                          MakeBooleanAccessor(&TcpComposite::m_tcpFriendliness),
                          MakeBooleanChecker())
            .AddAttribute("HyStart",
                          "Enable (true) or disable (false) hybrid slow start algorithm",
                          BooleanValue(true),
                          MakeBooleanAccessor(&TcpComposite::m_hystart),
                          MakeBooleanChecker())
            .AddAttribute("HyStartLowWindow",
                          "Lower bound cWnd for hybrid slow start (segments)",
                          UintegerValue(16),
                          MakeUintegerAccessor(&TcpComposite::m_hystartLowWindow),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("HyStartDetect",
                          "Hybrid Slow Start detection mechanisms:"
                          "packet train, delay, both",
                          EnumValue(HybridSSDetectionMode::BOTH),
                          MakeEnumAccessor<HybridSSDetectionMode>(&TcpComposite::m_hystartDetect),
                          MakeEnumChecker(HybridSSDetectionMode::PACKET_TRAIN,
                                          "PACKET_TRAIN",
                                          HybridSSDetectionMode::DELAY,
                                          "DELAY",
                                          HybridSSDetectionMode::BOTH,
                                          "BOTH"))
            .AddAttribute("HyStartMinSamples",
                          "Number of delay samples for detecting the increase of delay",
                          UintegerValue(8),
                          MakeUintegerAccessor(&TcpComposite::m_hystartMinSamples),
                          MakeUintegerChecker<uint8_t>())
            .AddAttribute("HyStartAckDelta",
                          "Spacing between ack's indicating train",
                          TimeValue(MilliSeconds(2)),
                          MakeTimeAccessor(&TcpComposite::m_hystartAckDelta),
                          MakeTimeChecker())
            .AddAttribute("HyStartDelayMin",
                          "Minimum time for hystart algorithm",
                          TimeValue(MilliSeconds(4)),
                          MakeTimeAccessor(&TcpComposite::m_hystartDelayMin),
                          MakeTimeChecker())
            .AddAttribute("HyStartDelayMax",
                          "Maximum time for hystart algorithm",
                          TimeValue(MilliSeconds(1000)),
                          MakeTimeAccessor(&TcpComposite::m_hystartDelayMax),
                          MakeTimeChecker())
            .AddAttribute("CubicDelta",
                          "Delta Time to wait after fast recovery before adjusting param",
                          TimeValue(MilliSeconds(10)),
                          MakeTimeAccessor(&TcpComposite::m_cubicDelta),
                          MakeTimeChecker())
            .AddAttribute("CntClamp",
                          "Counter value when no losses are detected (counter is used"
                          " when incrementing cWnd in congestion avoidance, to avoid"
                          " floating point arithmetic). It is the modulo of the (avoided)"
                          " division",
                          UintegerValue(20),
                          MakeUintegerAccessor(&TcpComposite::m_cntClamp),
                          MakeUintegerChecker<uint8_t>());
    return tid;
}

TcpComposite::TcpComposite()
    : TcpCongestionOps(),
      m_cWndCnt(0),
      m_lastMaxCwnd(0),
      m_bicOriginPoint(0),
      m_bicK(0.0),
      m_delayMin(Time::Min()),
      m_epochStart(Time::Min()),
      m_found(false),
      m_roundStart(Time::Min()),
      m_endSeq(0),
      m_lastAck(Time::Min()),
      m_cubicDelta(Time::Min()),
      m_currRtt(Time::Min()),
      m_sampleCnt(0)
{
    NS_LOG_FUNCTION(this);
}

TcpComposite::TcpComposite(const TcpComposite& sock)
    : TcpCongestionOps(sock),
      m_fastConvergence(sock.m_fastConvergence),
      m_hystart(sock.m_hystart),
      m_hystartDetect(sock.m_hystartDetect),
      m_hystartLowWindow(sock.m_hystartLowWindow),
      m_hystartAckDelta(sock.m_hystartAckDelta),
      m_hystartDelayMin(sock.m_hystartDelayMin),
      m_hystartDelayMax(sock.m_hystartDelayMax),
      m_hystartMinSamples(sock.m_hystartMinSamples),
      m_initialCwnd(sock.m_initialCwnd),
      m_cntClamp(sock.m_cntClamp),
      m_cWndCnt(sock.m_cWndCnt),
      m_lastMaxCwnd(sock.m_lastMaxCwnd),
      m_bicOriginPoint(sock.m_bicOriginPoint),
      m_bicK(sock.m_bicK),
      m_delayMin(sock.m_delayMin),
      m_epochStart(sock.m_epochStart),
      m_found(sock.m_found),
      m_roundStart(sock.m_roundStart),
      m_endSeq(sock.m_endSeq),
      m_lastAck(sock.m_lastAck),
      m_cubicDelta(sock.m_cubicDelta),
      m_currRtt(sock.m_currRtt),
      m_sampleCnt(sock.m_sampleCnt)
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
        NS_LOG_INFO(Simulator::Now() << ": in NewReno SlowStart, updated to cwnd " << tcb->m_cWnd << " ssthresh "
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
        NS_LOG_INFO(Simulator::Now() << ": in NewReno CongAvoid, updated to cwnd " << tcb->m_cWnd << " ssthresh "
                                                     << tcb->m_ssThresh);
    }
}

void
TcpComposite::IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    NS_LOG_FUNCTION(this << tcb << segmentsAcked);

    if (tcb->m_cWnd < tcb->m_ssThresh)
    {
        if (m_hystart && tcb->m_lastAckedSeq > m_endSeq)
        {
            HystartReset(tcb);
        }
    }

    if (m_policy == "TcpNewReno")
    {
        if (tcb->m_cWnd < tcb->m_ssThresh)
        {
            segmentsAcked = SlowStart(tcb, segmentsAcked);
        }

        if (tcb->m_cWnd >= tcb->m_ssThresh)
        {
            CongestionAvoidance(tcb, segmentsAcked);
        }
    }
    if (m_policy == "TcpCubic")
    {
        if (tcb->m_cWnd < tcb->m_ssThresh)
        {

            // In Linux, the QUICKACK socket option enables the receiver to send
            // immediate acks initially (during slow start) and then transition
            // to delayed acks.  ns-3 does not implement QUICKACK, and if ack
            // counting instead of byte counting is used during slow start window
            // growth, when TcpSocket::DelAckCount==2, then the slow start will
            // not reach as large of an initial window as in Linux.  Therefore,
            // we can approximate the effect of QUICKACK by making this slow
            // start phase perform Appropriate Byte Counting (RFC 3465)
            tcb->m_cWnd += segmentsAcked * tcb->m_segmentSize;
            segmentsAcked = 0;

            NS_LOG_INFO(Simulator::Now() << ": in Cubic SlowStart, updated to cwnd " << tcb->m_cWnd << " ssthresh "
                                                         << tcb->m_ssThresh);
        }

        if (tcb->m_cWnd >= tcb->m_ssThresh && segmentsAcked > 0)
        {
            m_cWndCnt += segmentsAcked;
            uint32_t cnt = Update(tcb, segmentsAcked);

            /* According to RFC 6356 even once the new cwnd is
             * calculated you must compare this to the number of ACKs received since
             * the last cwnd update. If not enough ACKs have been received then cwnd
             * cannot be updated.
             */
            if (m_cWndCnt >= cnt)
            {
                tcb->m_cWnd += tcb->m_segmentSize;
                m_cWndCnt -= cnt;
                NS_LOG_INFO(Simulator::Now() << ": in Cubic CongAvoid, updated to cwnd " << tcb->m_cWnd);
            }
            else
            {
                NS_LOG_INFO(Simulator::Now() << ": Cubic Not enough segments have been ACKed to increment cwnd."
                            "Until now "
                            << m_cWndCnt << " cnd " << cnt);
            }
        }
    }
}

void
TcpComposite::Init(Ptr<TcpSocketState> tcb)
{
    NS_LOG_FUNCTION(this << tcb);
    SetPolicy(m_policyFirst);
    SetFirstPar(m_firstParFirst);
    SetSecondPar(m_secondParFirst);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::SetPolicy, this, m_policySecond);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::SetFirstPar, this, m_firstParSecond);
    Simulator::Schedule(Seconds(m_switchTime),
                        &TcpComposite::SetSecondPar,
                        this,
                        m_secondParSecond);
    Simulator::Schedule(Seconds(m_switchTime), &TcpComposite::ChangeCwnd, this, tcb, m_secondCwndDiff);
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

void TcpComposite::ChangeCwnd(Ptr<TcpSocketState> tcb, int diff){
    NS_LOG_FUNCTION(this << tcb << diff);
    NS_LOG_DEBUG("Changing cwnd from " << tcb->m_cWnd);
    tcb->m_cWnd += diff * tcb->m_segmentSize;
    NS_LOG_DEBUG("Changing cwnd to " << tcb->m_cWnd);
}

void
TcpComposite::HystartReset(Ptr<const TcpSocketState> tcb)
{
    NS_LOG_FUNCTION(this);

    m_roundStart = m_lastAck = Simulator::Now();
    m_endSeq = tcb->m_highTxMark;
    m_currRtt = Time::Min();
    m_sampleCnt = 0;
}

uint32_t
TcpComposite::Update(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked)
{
    NS_LOG_FUNCTION(this);
    Time t;
    uint32_t delta;
    uint32_t bicTarget;
    uint32_t cnt = 0;
    uint32_t maxCnt;
    double offs;
    uint32_t segCwnd = tcb->GetCwndInSegments();

    m_ackCnt += segmentsAcked;

    if (m_epochStart == Time::Min())
    {
        m_epochStart = Simulator::Now(); // record the beginning of an epoch
        m_ackCnt = segmentsAcked;
        m_tcpCwnd = segCwnd;

        if (m_lastMaxCwnd <= segCwnd)
        {
            NS_LOG_DEBUG("lastMaxCwnd <= m_cWnd. K=0 and origin=" << segCwnd);
            m_bicK = 0.0;
            m_bicOriginPoint = segCwnd;
        }
        else
        {
            m_bicK = std::pow((m_lastMaxCwnd - segCwnd) / m_secondPar, 1 / 3.);
            m_bicOriginPoint = m_lastMaxCwnd;
            NS_LOG_DEBUG("lastMaxCwnd > m_cWnd. K=" << m_bicK << " and origin=" << m_lastMaxCwnd);
        }
    }

    t = Simulator::Now() + m_delayMin - m_epochStart;

    if (t.GetSeconds() < m_bicK) /* t - K */
    {
        offs = m_bicK - t.GetSeconds();
        NS_LOG_DEBUG("t=" << t.GetSeconds() << " <k: offs=" << offs);
    }
    else
    {
        offs = t.GetSeconds() - m_bicK;
        NS_LOG_DEBUG("t=" << t.GetSeconds() << " >= k: offs=" << offs);
    }

    /* Constant value taken from Experimental Evaluation of Cubic Tcp, available at
     * eprints.nuim.ie/1716/1/Hamiltonpfldnet2007_cubic_final.pdf */
    delta = m_secondPar * std::pow(offs, 3);

    NS_LOG_DEBUG("delta: " << delta);

    if (t.GetSeconds() < m_bicK)
    {
        // below origin
        bicTarget = m_bicOriginPoint - delta;
        NS_LOG_DEBUG("t < k: Bic Target: " << bicTarget);
    }
    else
    {
        // above origin
        bicTarget = m_bicOriginPoint + delta;
        NS_LOG_DEBUG("t >= k: Bic Target: " << bicTarget);
    }

    // Next the window target is converted into a cnt or count value. CUBIC will
    // wait until enough new ACKs have arrived that a counter meets or exceeds
    // this cnt value. This is how the CUBIC implementation simulates growing
    // cwnd by values other than 1 segment size.
    if (bicTarget > segCwnd)
    {
        cnt = segCwnd / (bicTarget - segCwnd);
        NS_LOG_DEBUG("target>cwnd. cnt=" << cnt);
    }
    else
    {
        cnt = 100 * segCwnd;
    }

    if (m_lastMaxCwnd == 0 && cnt > m_cntClamp)
    {
        cnt = m_cntClamp;
    }

    if (m_tcpFriendliness)
    {
        auto scale =
            static_cast<uint32_t>(8 * (1024 + m_firstPar * 1024) / 3 / (1024 - m_firstPar * 1024));
        delta = (segCwnd * scale) >> 3;
        while (m_ackCnt > delta)
        {
            m_ackCnt -= delta;
            m_tcpCwnd++;
        }
        if (m_tcpCwnd > segCwnd)
        {
            delta = m_tcpCwnd - segCwnd;
            maxCnt = segCwnd / delta;
            if (cnt > maxCnt)
            {
                cnt = maxCnt;
            }
        }
    }

    // The maximum rate of cwnd increase CUBIC allows is 1 packet per
    // 2 packets ACKed, meaning cwnd grows at 1.5x per RTT.
    return std::max(cnt, 2U);
}

void
TcpComposite::PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt)
{
    NS_LOG_FUNCTION(this << tcb << segmentsAcked << rtt);

    /* Discard delay samples right after fast recovery */
    if (m_epochStart != Time::Min() && (Simulator::Now() - m_epochStart) < m_cubicDelta)
    {
        return;
    }

    /* first time call or link delay decreases */
    if (m_delayMin == Time::Min() || m_delayMin > rtt)
    {
        m_delayMin = rtt;
    }

    /* hystart triggers when cwnd is larger than some threshold */
    if (m_hystart && tcb->m_cWnd <= tcb->m_ssThresh &&
        tcb->m_cWnd >= m_hystartLowWindow * tcb->m_segmentSize)
    {
        HystartUpdate(tcb, rtt);
    }
}

void
TcpComposite::HystartUpdate(Ptr<TcpSocketState> tcb, const Time& delay)
{
    NS_LOG_FUNCTION(this << delay);

    if (!m_found)
    {
        Time now = Simulator::Now();

        /* first detection parameter - ack-train detection */
        if ((now - m_lastAck) <= m_hystartAckDelta)
        {
            m_lastAck = now;

            if ((now - m_roundStart) > m_delayMin)
            {
                if (m_hystartDetect == HybridSSDetectionMode::PACKET_TRAIN ||
                    m_hystartDetect == HybridSSDetectionMode::BOTH)
                {
                    m_found = true;
                }
            }
        }

        /* obtain the minimum delay of more than sampling packets */
        if (m_sampleCnt < m_hystartMinSamples)
        {
            if (m_currRtt == Time::Min() || m_currRtt > delay)
            {
                m_currRtt = delay;
            }

            ++m_sampleCnt;
        }
        else if (m_currRtt > m_delayMin + HystartDelayThresh(m_delayMin))
        {
            if (m_hystartDetect == HybridSSDetectionMode::DELAY ||
                m_hystartDetect == HybridSSDetectionMode::BOTH)
            {
                m_found = true;
            }
        }

        /*
         * Either one of two conditions are met,
         * we exit from slow start immediately.
         */
        if (m_found)
        {
            NS_LOG_DEBUG("Exit from SS, immediately :-)");
            if (m_policy == "TcpCubic")
                tcb->m_ssThresh = tcb->m_cWnd;
        }
    }
}

Time
TcpComposite::HystartDelayThresh(const Time& t) const
{
    NS_LOG_FUNCTION(this << t);

    Time ret = t;
    if (t > m_hystartDelayMax)
    {
        ret = m_hystartDelayMax;
    }
    else if (t < m_hystartDelayMin)
    {
        ret = m_hystartDelayMin;
    }

    return ret;
}

uint32_t
TcpComposite::GetSsThresh(Ptr<const TcpSocketState> tcb, uint32_t bytesInFlight)
{
    NS_LOG_FUNCTION(this << tcb << bytesInFlight);

    // Cubic update m_lastMaxCwnd and reset m_epochStart

    uint32_t segCwnd = tcb->GetCwndInSegments();
    NS_LOG_DEBUG("Loss at cWnd=" << segCwnd
                                 << " segments in flight=" << bytesInFlight / tcb->m_segmentSize);

    /* Wmax and fast convergence */
    if (segCwnd < m_lastMaxCwnd && m_fastConvergence)
    {
        m_lastMaxCwnd = (segCwnd * (1 + m_firstPar)) / 2; // Section 4.6 in RFC 8312
    }
    else
    {
        m_lastMaxCwnd = segCwnd;
    }

    m_epochStart = Time::Min(); // end of epoch

    if (m_policy == "TcpNewReno")
    {
        return std::max(2 * tcb->m_segmentSize, bytesInFlight / uint32_t(m_secondPar));
    }
    if (m_policy == "TcpCubic")
    {
        /* Formula taken from the Linux kernel */
        uint32_t ssThresh =
            std::max(static_cast<uint32_t>(segCwnd * m_firstPar), 2U) * tcb->m_segmentSize;

        NS_LOG_DEBUG("SsThresh = " << ssThresh);

        return ssThresh;
    }
    else
    {
        NS_LOG_ERROR("Unknown policy " << m_policy);
        return -1;
    }
}

void
TcpComposite::CongestionStateSet(Ptr<TcpSocketState> tcb,
                                 const TcpSocketState::TcpCongState_t newState)
{
    NS_LOG_FUNCTION(this << tcb << newState);

    if (newState == TcpSocketState::CA_LOSS)
    {
        CubicReset(tcb);
        HystartReset(tcb);
    }
}

void
TcpComposite::CubicReset(Ptr<const TcpSocketState> tcb)
{
    NS_LOG_FUNCTION(this << tcb);

    m_lastMaxCwnd = 0;
    m_bicOriginPoint = 0;
    m_bicK = 0;
    m_ackCnt = 0;
    m_tcpCwnd = 0;
    m_delayMin = Time::Min();
    m_found = false;
}

Ptr<TcpCongestionOps>
TcpComposite::Fork()
{
    return CopyObject<TcpComposite>(this);
}

} // namespace ns3