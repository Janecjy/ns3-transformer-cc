#ifndef TCP_COMPOSITE_H
#define TCP_COMPOSITE_H

#include "tcp-congestion-ops.h"
#include "tcp-socket-base.h"

namespace ns3
{
class TcpComposite : public TcpCongestionOps
{
  public:
    /**
     * \brief Values to detect the Slow Start mode of HyStart
     */
    enum HybridSSDetectionMode
    {
        PACKET_TRAIN = 1, //!< Detection by trains of packet
        DELAY = 2,        //!< Detection by delay value
        BOTH = 3,         //!< Detection by both
    };

    /**
     * \brief Get the type ID.
     * \return the object TypeId
     */
    static TypeId GetTypeId();

    TcpComposite();

    /**
     * \brief Copy constructor.
     * \param sock object to copy.
     */
    TcpComposite(const TcpComposite& sock);

    ~TcpComposite() override;

    std::string GetName() const override;
    void Init(Ptr<TcpSocketState> tcb) override;
    void SetPolicy(std::string policy);
    void SetFirstPar(double firstPar);
    void SetSecondPar(double secondPar);

    void IncreaseWindow(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked) override;
    uint32_t GetSsThresh(Ptr<const TcpSocketState> tcb, uint32_t bytesInFlight) override;
    Ptr<TcpCongestionOps> Fork() override;

    // Cubic-Related Functions
    void PktsAcked(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked, const Time& rtt) override;
    void CongestionStateSet(Ptr<TcpSocketState> tcb,
                            const TcpSocketState::TcpCongState_t newState) override;

  protected:
    virtual uint32_t SlowStart(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked);
    virtual void CongestionAvoidance(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked);

  private:
    // Composite-related Parameters
    std::string m_policyFirst;
    double m_firstParFirst;
    double m_secondParFirst;
    std::string m_policySecond;
    double m_firstParSecond;
    double m_secondParSecond;
    uint32_t m_switchTime;
    std::string m_policy;
    double m_firstPar;
    double m_secondPar;

    // Cubic-related Parameters

    bool m_fastConvergence; //!< Enable or disable fast convergence algorithm
    bool m_tcpFriendliness; //!< Enable or disable TCP-friendliness heuristic

    bool m_hystart;                        //!< Enable or disable HyStart algorithm
    HybridSSDetectionMode m_hystartDetect; //!< Detect way for HyStart algorithm
    uint32_t m_hystartLowWindow;           //!< Lower bound cWnd for hybrid slow start (segments)
    Time m_hystartAckDelta;                //!< Spacing between ack's indicating train
    Time m_hystartDelayMin;                //!< Minimum time for hystart algorithm
    Time m_hystartDelayMax;                //!< Maximum time for hystart algorithm
    uint8_t m_hystartMinSamples; //!< Number of delay samples for detecting the increase of delay

    uint32_t m_initialCwnd; //!< Initial cWnd
    uint8_t m_cntClamp;     //!< Modulo of the (avoided) float division for cWnd

    // Cubic parameters
    uint32_t m_cWndCnt;        //!<  cWnd integer-to-float counter
    uint32_t m_lastMaxCwnd;    //!<  Last maximum cWnd
    uint32_t m_bicOriginPoint; //!<  Origin point of bic function
    double m_bicK;             //!<  Time to origin point from the beginning
                               //    of the current epoch (in s)
    Time m_delayMin;           //!<  Min delay
    Time m_epochStart;         //!<  Beginning of an epoch
    bool m_found;              //!<  The exit point is found?
    Time m_roundStart;         //!<  Beginning of each round
    SequenceNumber32 m_endSeq; //!<  End sequence of the round
    Time m_lastAck;            //!<  Last time when the ACK spacing is close
    Time m_cubicDelta;         //!<  Time to wait after recovery before update
    Time m_currRtt;            //!<  Current Rtt
    uint32_t m_sampleCnt;      //!<  Count of samples for HyStart
    uint32_t m_ackCnt;         //!<  Count the number of ACKed packets
    uint32_t m_tcpCwnd;        //!<  Estimated tcp cwnd (for Reno-friendliness)

    /**
     * \brief Reset HyStart parameters
     * \param tcb Transmission Control Block of the connection
     */
    void HystartReset(Ptr<const TcpSocketState> tcb);

    /**
     * \brief Reset Cubic parameters
     * \param tcb Transmission Control Block of the connection
     */
    void CubicReset(Ptr<const TcpSocketState> tcb);

    /**
     * \brief Cubic window update after a new ack received
     * \param tcb Transmission Control Block of the connection
     * \param segmentsAcked Segments acked
     * \returns the congestion window update counter
     */
    uint32_t Update(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked);

    /**
     * \brief Update HyStart parameters
     *
     * \param tcb Transmission Control Block of the connection
     * \param delay Delay for HyStart algorithm
     */
    void HystartUpdate(Ptr<TcpSocketState> tcb, const Time& delay);

    /**
     * \brief Clamp time value in a range
     *
     * The returned value is t, clamped in a range specified
     * by attributes (HystartDelayMin < t < HystartDelayMax)
     *
     * \param t Time value to clamp
     * \return t itself if it is in range, otherwise the min or max
     * value
     */
    Time HystartDelayThresh(const Time& t) const;
};

} // namespace ns3

#endif // TCP_COMPOSITE_H