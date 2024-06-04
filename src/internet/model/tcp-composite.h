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

  protected:
    virtual uint32_t SlowStart(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked);
    virtual void CongestionAvoidance(Ptr<TcpSocketState> tcb, uint32_t segmentsAcked);

  private:
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
};

} // namespace ns3

#endif // TCP_COMPOSITE_H